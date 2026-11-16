"""Safe verification and instantiation of built workspace starter packages."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional

from workspace_paths import SourcePaths, WorkspacePaths, normalized_file_sha256, validate_framework_manifest, validate_workspace_structure  # type: ignore

MAX_ARCHIVE_FILES = 2_000
MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_RATIO = 250
MAX_WINDOWS_PATH = 240
TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".txt",
    ".csv", ".xml", ".svg", ".html", ".htm", ".css", ".js", ".ts",
    ".sh", ".ps1", ".bat", ".cmd", ".ini", ".cfg", ".conf", ".properties",
}
ALLOWED_TOP_LEVEL = {"README.md", "AGENTS.md", "bp.py", "LICENSE", "PBF-LICENSE-SCOPE.md", ".gitignore", ".gitattributes", "docs", "_framework", "_control"}
RESERVED_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@dataclass(frozen=True)
class PackageInspection:
    path: Path
    version: str
    file_count: int
    total_size: int
    names: tuple[str, ...]
    hashes: dict[str, str]
    archive_sha256: str


def _is_text_name(name: str) -> bool:
    path = PurePosixPath(name)
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitattributes", ".gitignore", "AGENTS.md", "bp.py"} or path.name.endswith(".json.template") or path.name.endswith(".md.template")


def _normalized_hash(data: bytes, is_text: bool) -> str:
    if is_text:
        text = data.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError("Managed text contains a UTF-8 BOM")
        data = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def normalize_project_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Project name must be text")
    value = unicodedata.normalize("NFC", name).strip()
    if not value:
        raise ValueError("Project name must not be empty")
    if value != name.strip():
        # NFC normalization is expected; trimming outer whitespace is allowed.
        pass
    for char in value:
        category = unicodedata.category(char)
        if category.startswith("C") or char in '<>:"/\\|?*':
            raise ValueError(f"Project name contains a filesystem-unsafe or invisible character: U+{ord(char):04X} {char!r}")
    if value.endswith((".", " ")):
        raise ValueError("Project name must not end with a dot or space")
    stem = value.split(".", 1)[0].upper()
    if stem in RESERVED_WINDOWS:
        raise ValueError(f"Project name is reserved on Windows: {value!r}")
    return value


def project_slug(name: str) -> str:
    value = unicodedata.normalize("NFC", normalize_project_name(name))
    output: list[str] = []
    in_space = False
    for char in value:
        if char.isspace():
            if output and not in_space:
                output.append("-")
            in_space = True
            continue
        in_space = False
        category = unicodedata.category(char)
        if category[0] in {"L", "N", "M"} or char in "-_":
            output.append(char)
        else:
            # Benign punctuation is separated in the slug while remaining in
            # the display name; filesystem-unsafe characters were rejected.
            if output and output[-1] != "-":
                output.append("-")
    slug = "".join(output).strip("-_")
    if not slug or slug in {".", ".."}:
        raise ValueError("Project name does not produce a usable destination slug")
    return slug


def _validate_member_name(name: str) -> str:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"Unsafe archive member name: {name!r}")
    if name.startswith("/") or name.endswith("/"):
        raise ValueError(f"Archive directory entries and absolute paths are not permitted: {name!r}")
    pure = PurePosixPath(name)
    windows = PureWindowsPath(name)
    pieces = name.split("/")
    if pure.is_absolute() or windows.is_absolute() or windows.drive or any(part in {"", ".", ".."} for part in pieces):
        raise ValueError(f"Unsafe archive member path: {name!r}")
    if pieces[0] not in ALLOWED_TOP_LEVEL:
        raise ValueError(f"Unexpected top-level archive path: {name!r}")
    for piece in pieces:
        if piece.endswith((".", " ")) or any(c in piece for c in '<>:"\\|?*') or any(unicodedata.category(c).startswith("C") for c in piece):
            raise ValueError(f"Archive member is not portable to Windows: {name!r}")
        stem = piece.split(".", 1)[0].upper()
        if stem in RESERVED_WINDOWS:
            raise ValueError(f"Archive member uses a reserved Windows name: {name!r}")
    return name


def inspect_package(path: Path | str, expected_version: Optional[str] = None) -> PackageInspection:
    """Validate ZIP metadata, member paths, layout and managed hashes pre-extraction."""
    package = Path(path).expanduser().resolve()
    if not package.is_file():
        raise ValueError(f"Workspace starter package does not exist: {package}")
    try:
        with package.open("rb") as stream:
            payload = stream.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES or stream.read(1):
                raise ValueError(f"Workspace starter ZIP exceeds the compressed-size limit ({MAX_ARCHIVE_BYTES} bytes)")
    except OSError as exc:
        raise ValueError(f"Cannot read workspace starter ZIP: {exc}") from exc
    archive_digest = hashlib.sha256(payload).hexdigest()
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Cannot open workspace starter ZIP: {exc}") from exc
    with zf:
        infos = zf.infolist()
        if not infos:
            raise ValueError("Workspace starter ZIP is empty")
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError(f"Workspace starter ZIP contains too many members ({len(infos)})")
        names: list[str] = []
        seen_exact: set[str] = set()
        seen_folded: dict[str, str] = {}
        total_size = 0
        for info in infos:
            if info.is_dir():
                raise ValueError(f"Unexpected directory entry in workspace ZIP: {info.filename}")
            name = _validate_member_name(info.filename)
            if name in seen_exact:
                raise ValueError(f"Duplicate archive member: {name}")
            folded = unicodedata.normalize("NFKC", name).casefold()
            if folded in seen_folded and seen_folded[folded] != name:
                raise ValueError(f"Case/Unicode-normalization collision: {seen_folded[folded]!r} and {name!r}")
            seen_exact.add(name)
            seen_folded[folded] = name
            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(mode)
            if file_type not in (0, stat.S_IFREG):
                raise ValueError(f"Non-regular or symlink ZIP member is not permitted: {name}")
            if info.flag_bits & 0x1:
                raise ValueError(f"Encrypted ZIP member is not permitted: {name}")
            if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                raise ValueError(f"ZIP member exceeds the size limit: {name}")
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError("Workspace starter ZIP exceeds the total uncompressed size limit")
            if info.file_size and info.compress_size == 0:
                raise ValueError(f"Invalid compressed size metadata: {name}")
            if info.compress_size and info.file_size / info.compress_size > MAX_ARCHIVE_RATIO:
                raise ValueError(f"ZIP member compression ratio exceeds the safety limit: {name}")
            names.append(name)

        if names != sorted(names):
            raise ValueError("Workspace starter ZIP members must be sorted by root-relative path")

        # A member may not also be the directory prefix of another member.
        name_set = set(names)
        for name in names:
            parts = name.split("/")
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index])
                if parent in name_set:
                    raise ValueError(f"Archive file/directory path conflict: {parent!r} and {name!r}")

        required = {
            "README.md", "AGENTS.md", "bp.py", "LICENSE", "PBF-LICENSE-SCOPE.md", ".gitignore", ".gitattributes",
            "docs/README.md", "docs/04-architecture/adr/README.md",
            "docs/99-appendix/research/README.md", "_control/WORKSPACE.json.template",
            "_control/PHASES.md", "_control/STATE.md", "_control/PROJECT-RULES.md",
            "_control/registry/MANIFEST.md", "_control/registry/INDEX.md",
            "_control/registry/APPROVALS.md", "_control/registry/DECISIONS.md",
            "_control/registry/ASSUMPTIONS.md", "_control/registry/QUESTIONS.md",
            "_control/registry/RISKS.md", "_control/registry/GLOSSARY.md",
            "_control/registry/CHANGELOG.md", "_control/logs/status-transitions.jsonl",
            "_framework/FRAMEWORK-MANIFEST.json", "_framework/tools/blueprint.py",
            "_framework/tools/workspace_paths.py", "_framework/defaults/workspace-defaults.json",
        }
        missing = sorted(required - name_set)
        if missing:
            raise ValueError("Workspace starter ZIP is missing required file(s): " + ", ".join(missing))
        if "_control/WORKSPACE.json" in name_set:
            raise ValueError("Starter package must contain WORKSPACE.json.template, not a live WORKSPACE.json")
        forbidden_prefixes = ("framework-dev/", "src/", "dist/", ".git/")
        forbidden_exact = {"VERSION", "framework-dev/SOURCE-MANIFEST.json", "AGENT.md"}
        for name in names:
            if name in forbidden_exact or name.startswith(forbidden_prefixes):
                raise ValueError(f"Source-only or legacy file leaked into workspace package: {name}")

        # Read only package metadata and managed files after validating all
        # archive names/metadata. ZIP CRC is checked as each member is consumed.
        try:
            manifest = json.loads(zf.read("_framework/FRAMEWORK-MANIFEST.json").decode("utf-8"))
        except (KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            raise ValueError(f"Workspace package has an invalid framework manifest: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Workspace package framework manifest must be a JSON object")
        schema_version = manifest.get("manifest_schema_version")
        if (isinstance(schema_version, bool) or schema_version != 1
                or manifest.get("hash_algorithm") != "sha256"
                or manifest.get("text_hash_policy") != "utf8-lf-normalized-v1"):
            raise ValueError("Workspace package declares an unsupported framework manifest format")
        version = manifest.get("framework_version")
        if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version):
            raise ValueError(f"Workspace package has an invalid framework version: {version!r}")
        if expected_version is not None and version != expected_version:
            raise ValueError(f"Workspace package version {version} does not match source VERSION {expected_version}")
        schema_versions = manifest.get("workspace_schema_versions_supported")
        layout_versions = manifest.get("layout_versions_supported")
        if (schema_versions != [1] or layout_versions != [1]
                or any(isinstance(value, bool) for value in (schema_versions or []) + (layout_versions or []) if isinstance(value, int))):
            raise ValueError("Workspace package does not declare the supported integer workspace schema/layout versions")
        hashes = manifest.get("files")
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError("Framework manifest 'files' must be a non-empty object")
        if not all(isinstance(key, str) for key in hashes):
            raise ValueError("Framework manifest file paths must all be strings")
        if list(hashes) != sorted(hashes):
            raise ValueError("Framework manifest file entries must be sorted")
        package_managed = {name for name in names if name.startswith("_framework/") and name != "_framework/FRAMEWORK-MANIFEST.json"} | {"AGENTS.md", "bp.py"}
        if set(hashes) != package_managed:
            missing_hashes = sorted(package_managed - set(hashes))
            extra_hashes = sorted(set(hashes) - package_managed)
            raise ValueError(f"Framework manifest coverage mismatch; untracked={missing_hashes}, invalid_entries={extra_hashes}")
        for name, expected_hash in hashes.items():
            _validate_member_name(name)
            if name not in package_managed or not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise ValueError(f"Invalid framework-manifest entry: {name!r}")
            try:
                actual = _normalized_hash(zf.read(name), _is_text_name(name))
            except (KeyError, UnicodeError, zipfile.BadZipFile) as exc:
                raise ValueError(f"Cannot verify managed package file {name}: {exc}") from exc
            if actual != expected_hash:
                raise ValueError(f"Framework package hash mismatch for {name}: expected {expected_hash}, actual {actual}")

        # The package seed is intentionally non-live but must be valid config.
        try:
            config = json.loads(zf.read("_control/WORKSPACE.json.template").decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError, KeyError) as exc:
            raise ValueError(f"Starter workspace configuration seed is invalid: {exc}") from exc
        if not isinstance(config, dict) or not isinstance(config.get("project"), dict):
            raise ValueError("Starter workspace configuration seed must be an object with a project object")
        workspace_schema = config.get("workspace_schema_version")
        layout_version = config.get("layout_version")
        if (isinstance(workspace_schema, bool) or workspace_schema != 1
                or isinstance(layout_version, bool) or layout_version != 1
                or config.get("project", {}).get("name") != "{{PROJECT_NAME}}"):
            raise ValueError("Starter workspace configuration seed does not match integer schema/layout 1 or project-name template")
        if config.get("profile") not in {"lite", "standard", "exhaustive"}:
            raise ValueError("Starter workspace configuration has an unsupported profile")
        # Every packaged text file—not only hash-managed framework files—must
        # already satisfy the deterministic UTF-8/LF contract before extraction.
        for name in names:
            if _is_text_name(name):
                try:
                    text = zf.read(name).decode("utf-8")
                except (UnicodeError, zipfile.BadZipFile) as exc:
                    raise ValueError(f"Packaged text file is not valid UTF-8: {name}: {exc}") from exc
                if text.startswith("\ufeff") or "\r" in text:
                    raise ValueError(f"Packaged text file must be UTF-8 without BOM and use LF: {name}")
        agents = zf.read("AGENTS.md")
        try:
            agents_text = agents.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"AGENTS.md is not UTF-8: {exc}") from exc
        if agents_text.startswith("\ufeff") or "\r" in agents_text or len(agents_text) > 14_000:
            raise ValueError("AGENTS.md violates the UTF-8/LF/14,000-character package contract")
        readme = zf.read("README.md").decode("utf-8")
        if "{{PROJECT_NAME}}" not in readme:
            raise ValueError("README.md must retain the project-name token for new workspace creation")
        expected_control = {
            "_control/WORKSPACE.json.template", "_control/PHASES.md", "_control/STATE.md",
            "_control/PROJECT-RULES.md", "_control/logs/status-transitions.jsonl",
            "_control/logs/interviews/README.md", "_control/logs/phase-reports/README.md",
            "_control/logs/sessions/README.md",
            "_control/registry/MANIFEST.md", "_control/registry/INDEX.md",
            "_control/registry/APPROVALS.md", "_control/registry/DECISIONS.md",
            "_control/registry/ASSUMPTIONS.md", "_control/registry/QUESTIONS.md",
            "_control/registry/RISKS.md", "_control/registry/GLOSSARY.md",
            "_control/registry/CHANGELOG.md",
        }
        expected_docs = {"docs/README.md", "docs/04-architecture/adr/README.md", "docs/99-appendix/research/README.md"}
        expected_root = {"README.md", "AGENTS.md", "bp.py", "LICENSE", "PBF-LICENSE-SCOPE.md", ".gitignore", ".gitattributes"}
        expected_names = expected_root | expected_control | expected_docs | package_managed | {"_framework/FRAMEWORK-MANIFEST.json"}
        if name_set != expected_names:
            raise ValueError(
                "Workspace package inventory differs from the canonical starter; "
                f"missing={sorted(expected_names - name_set)}, unexpected={sorted(name_set - expected_names)}"
            )
        return PackageInspection(package, version, len(names), total_size, tuple(sorted(names)), dict(hashes), archive_digest)


def safe_extract_package(inspection: PackageInspection, destination: Path) -> None:
    """Extract the exact inspected archive without zipfile.extract/extractall.

    The compressed archive is read into a bounded immutable byte buffer and
    checked against the digest captured by inspect_package. This closes the
    inspect/extract path-replacement window: extraction never reopens an
    unchecked replacement at the original filesystem path.
    """
    try:
        with inspection.path.open("rb") as stream:
            payload = stream.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES or stream.read(1):
                raise ValueError("Workspace starter ZIP exceeds the compressed-size limit during extraction")
    except OSError as exc:
        raise ValueError(f"Cannot reread inspected workspace starter ZIP: {exc}") from exc
    actual_digest = hashlib.sha256(payload).hexdigest()
    if actual_digest != inspection.archive_sha256:
        raise ValueError("Workspace starter ZIP changed after inspection; refusing extraction")
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Inspected workspace starter ZIP is no longer readable: {exc}") from exc
    destination.mkdir(parents=True, exist_ok=False)
    with zf:
        current_names = tuple(sorted(info.filename for info in zf.infolist()))
        if current_names != inspection.names:
            raise ValueError("Workspace starter ZIP member inventory changed after inspection")
        for name in inspection.names:
            relative = PurePosixPath(name)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Staging starts empty. Still reject any symlink path component if
            # the environment races or a prior extraction unexpectedly exists.
            current = destination
            for part in relative.parts[:-1]:
                current = current / part
                if current.is_symlink() or not current.is_dir():
                    raise ValueError(f"Unsafe extraction parent: {current}")
            if target.exists() or target.is_symlink():
                raise ValueError(f"Extraction target already exists: {target}")
            with zf.open(name, "r") as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def _cloud_sync_warning(path: Path) -> Optional[str]:
    markers = {"onedrive", "dropbox", "icloud drive", "icloud", "google drive", "my drive", "googledrive"}
    for part in path.parts:
        folded = part.casefold()
        if any(marker in folded for marker in markers):
            return "WARNING: destination appears to be under a common cloud-synchronized folder; this is a heuristic. Prefer a local non-synchronized path for agent-assisted setup and frequent workspace file operations."
    return None


def _validate_destination(paths: SourcePaths, destination: Path, name: str, max_relative_length: int) -> Path:
    parent = destination.parent.resolve(strict=False)
    final = parent / destination.name
    if final.is_symlink() or final.exists():
        raise FileExistsError(f"Destination already exists (empty directories and symlinks are also refused): {final}")
    if not final.name or final.name in {".", ".."} or final.name.endswith((".", " ")) or any(c in final.name for c in '<>:"\\|?*') or any(unicodedata.category(c).startswith("C") for c in final.name):
        raise ValueError(f"Destination directory name is not portable to Windows: {final.name!r}")
    if final.name.split(".", 1)[0].upper() in RESERVED_WINDOWS:
        raise ValueError(f"Destination directory name is reserved on Windows: {final.name!r}")
    resolved = final.resolve(strict=False)
    source_root = paths.root.resolve()
    if resolved == source_root or source_root in resolved.parents:
        raise ValueError("Destination must be outside the framework source repository and all of its subdirectories")
    # Conservative cross-platform limit with room for the longest package path.
    if len(str(resolved)) + 1 + max_relative_length > MAX_WINDOWS_PATH:
        raise ValueError(f"Destination path is too long for the cross-platform workspace budget ({MAX_WINDOWS_PATH} characters)")
    # Case-fold/Unicode collisions are observable on case-sensitive hosts too.
    if parent.is_dir():
        candidate_key = unicodedata.normalize("NFKC", resolved.name).casefold()
        for sibling in parent.iterdir():
            if unicodedata.normalize("NFKC", sibling.name).casefold() == candidate_key:
                raise FileExistsError(f"Destination collides with an existing path under case/Unicode normalization: {sibling}")
    return resolved


def _remove_owned_empty_parents(created: list[Path]) -> None:
    for path in reversed(created):
        try:
            path.rmdir()
        except OSError:
            pass


def _create_workspace_tree(staging: Path, name: str) -> None:
    from .source_cli import validate_agents_instructions

    template = staging / "_control" / "WORKSPACE.json.template"
    config = json.loads(template.read_text(encoding="utf-8"))
    config["project"]["name"] = name
    readme_template = staging / "README.md"
    readme = readme_template.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", name)
    if "{{PROJECT_NAME}}" in readme:
        raise ValueError("README template contains an unresolved project-name placeholder")
    readme_template.write_text(readme, encoding="utf-8", newline="\n")
    live_marker = template.with_name("WORKSPACE.json")
    live_marker.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    template.unlink()
    if validate_agents_instructions(staging / "AGENTS.md"):
        raise ValueError("Packaged AGENTS.md failed instruction-hygiene checks")


def _normalize_workspace_text(root: Path) -> None:
    for item in root.rglob("*"):
        if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        if _is_text_name(item.relative_to(root).as_posix()):
            content = item.read_bytes().decode("utf-8")
            if content.startswith("\ufeff"):
                raise ValueError(f"Generated text contains a UTF-8 BOM: {item.relative_to(root).as_posix()}")
            item.write_bytes(content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def _validate_materialized_workspace(root: Path, expected_name: str) -> None:
    # Create the initial derived views before their freshness checks. This does
    # not create a session or infer any project decisions/approvals.
    import subprocess
    import sys
    for command in ((sys.executable, str(root / "bp.py"), "status", "--write"),
                    (sys.executable, str(root / "bp.py"), "index")):
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=__import__("sys").stderr)
        if result.returncode != 0:
            raise ValueError(f"Initial workspace generation failed: {' '.join(command[2:])} (exit {result.returncode})")
    _normalize_workspace_text(root)
    paths = WorkspacePaths.from_root(root)
    if paths.project_name != expected_name:
        raise ValueError("Materialized WORKSPACE.json does not contain the requested project name")
    defaults = json.loads(paths.defaults.read_text(encoding="utf-8"))
    structural = validate_workspace_structure(paths, defaults)
    drift = validate_framework_manifest(paths)
    failures = [f"{severity}: {message}" for severity, message in structural + drift if severity != "warning"]
    if failures:
        raise ValueError("Materialized workspace failed required structure/manifest validation:\n- " + "\n- ".join(failures))
    warning_messages = [message for severity, message in drift if severity == "warning"]
    if warning_messages:
        raise ValueError("Materialized workspace has unexpected managed-file drift:\n- " + "\n- ".join(warning_messages))

    for command in ((str(root / "bp.py"), "check", "--strict"), (str(root / "bp.py"), "index", "--check")):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, *command], cwd=root, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=__import__("sys").stderr)
        if result.returncode != 0:
            raise ValueError(f"New workspace validation failed: {' '.join(command[1:])} (exit {result.returncode})")

    for item in root.rglob("*"):
        if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        if _is_text_name(item.relative_to(root).as_posix()):
            raw = item.read_bytes()
            raw.decode("utf-8")
            if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
                raise ValueError(f"Generated file violates UTF-8 without BOM/LF policy: {item.relative_to(root).as_posix()}")

    allowed_docs = {"README.md", "04-architecture/adr/README.md", "99-appendix/research/README.md"}
    actual_docs = {item.relative_to(paths.docs).as_posix() for item in paths.docs.rglob("*") if item.is_file()}
    if actual_docs - allowed_docs:
        raise ValueError("Fresh workspace unexpectedly contains scaffolded project documents: " + ", ".join(sorted(actual_docs - allowed_docs)))
    # Runtime imports may create bytecode caches; they are never part of a
    # generated workspace and must not survive promotion.
    for cache in root.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache)
    for pyc in root.rglob("*.pyc"):
        pyc.unlink()


def create_workspace(paths: SourcePaths, name: str, destination: Optional[str] = None, package: Optional[str] = None) -> int:
    """Instantiate a project workspace via sibling staging and final rename."""
    created_parents: list[Path] = []
    staging: Optional[Path] = None
    try:
        from .source_cli import validate_agents_instructions
        display_name = normalize_project_name(name)
        slug = project_slug(display_name)
        version = paths.version.read_text(encoding="utf-8").strip()
        package_path = Path(package).expanduser() if package else paths.dist / f"project-blueprint-workspace-{version}.zip"
        if not package_path.is_absolute():
            package_path = (Path.cwd() / package_path).resolve()
        inspection = inspect_package(package_path, expected_version=version)

        if destination is None:
            destination_path = paths.root.parent / f"{slug}-Blueprint"
        else:
            destination_path = Path(destination).expanduser()
            if not destination_path.is_absolute():
                destination_path = Path.cwd() / destination_path
        # Resolve the parent before making it; record only directories this
        # invocation actually creates so failure cleanup cannot remove user data.
        destination_path = Path(os.path.abspath(str(destination_path)))
        parent = destination_path.parent
        missing: list[Path] = []
        cursor = parent
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        for item in reversed(missing):
            item.mkdir()
            created_parents.append(item)
        final = _validate_destination(paths, destination_path, display_name, max(len(name) for name in inspection.names))
        warning = _cloud_sync_warning(final)
        if warning:
            print(warning)

        staging = Path(tempfile.mkdtemp(prefix=f".{slug}.bp-stage-", dir=str(final.parent)))
        # tempfile creates the staging directory; safe extraction requires a
        # non-existent destination, so remove only that owned empty directory.
        staging.rmdir()
        safe_extract_package(inspection, staging)
        _create_workspace_tree(staging, display_name)
        _validate_materialized_workspace(staging, display_name)

        # The residual concurrent-creation race after this check is documented
        # in the accepted architecture. Promotion is a same-filesystem rename.
        if final.exists() or final.is_symlink():
            raise FileExistsError(f"Destination appeared during creation; refusing promotion: {final}")
        os.rename(staging, final)
        staging = None

        print(f"Workspace created: {final}")
        print(f"Project: {display_name}")
        print("Validation: check --strict and index --check passed on the staged workspace.")
        print("Next: review README.md, AGENTS.md and _control/PROJECT-RULES.md, then start the first discovery conversation.")
        print("First-session prompt: README.md")
        print("Git was not initialized. To opt in later, run `git init` from the workspace root.")
        print("Interpreter examples: Windows `py -3.11 bp.py check --strict`; POSIX/WSL `python3.11 bp.py check --strict`.")
        return 0
    except Exception as exc:
        print(f"ERROR: workspace creation failed: {exc}")
        if staging is not None and staging.exists():
            # staging is a unique, invocation-owned sibling; never clean any
            # path other than this exact directory.
            shutil.rmtree(staging, ignore_errors=True)
        _remove_owned_empty_parents(created_parents)
        return 1
