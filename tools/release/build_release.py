#!/usr/bin/env python3
"""Build the single PBF Agent-First Release ZIP deterministically.

The developer repository is the source of truth. This compiler builds the
Agent-First product artifact and does not mutate source inputs.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "release-assets"
MINIMUM_PYTHON = (3, 11)
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_TOTAL_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_RATIO = 500


class ReleaseBuildError(RuntimeError):
    """A release build failed a required precondition or verification."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version(root: Path = ROOT) -> str:
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ReleaseBuildError(f"Cannot read VERSION: {exc}") from exc
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version):
        raise ReleaseBuildError(f"VERSION is not a supported semantic version: {version!r}")
    return version


def read_architecture_revision(root: Path = ROOT) -> str:
    path = root / "framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReleaseBuildError(f"Cannot read accepted workspace architecture: {exc}") from exc
    match = re.search(r"^version:\s*['\"]?(\d+\.\d+\.\d+)['\"]?\s*$", content, re.MULTILINE)
    if not match:
        raise ReleaseBuildError("Accepted architecture specification does not declare a numeric version field.")
    return match.group(1)


def _safe_relative_name(value: str) -> PurePosixPath:
    """Validate archive paths for POSIX extraction and Windows portability."""
    if not value or "\\" in value or "\x00" in value:
        raise ReleaseBuildError(f"Unsafe archive member name: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ReleaseBuildError(f"Unsafe archive member name: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", parts[0]):
        raise ReleaseBuildError(f"Absolute or drive-qualified archive member: {value!r}")
    invalid_windows = set('<>:\"|?*')
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in path.parts:
        stem = part.split(".", 1)[0].upper()
        if any(ord(char) < 32 or char in invalid_windows for char in part):
            raise ReleaseBuildError(f"Archive path component is not portable to Windows: {value!r}")
        if part.endswith((".", " ")) or stem in reserved:
            raise ReleaseBuildError(f"Reserved or ambiguous Windows archive path component: {value!r}")
    return path


def _check_member_collisions(names: Iterable[str]) -> None:
    """Reject full-path, component and file/directory aliases cross-platform."""
    component_spelling: dict[tuple[str, ...], tuple[str, ...]] = {}
    node_kind: dict[tuple[str, ...], str] = {}
    exact: set[str] = set()
    for name in sorted(names):
        pure = _safe_relative_name(name)
        if name in exact:
            raise ReleaseBuildError(f"Duplicate archive member: {name}")
        exact.add(name)
        parts = pure.parts
        for index, part in enumerate(parts):
            key = tuple(unicodedata.normalize("NFKC", p).casefold() for p in parts[: index + 1])
            spelling = tuple(parts[: index + 1])
            prior = component_spelling.get(key)
            if prior is not None and prior != spelling:
                raise ReleaseBuildError(f"Archive path component collision: {'/'.join(prior)!r} and {'/'.join(spelling)!r}")
            component_spelling[key] = spelling
            if index < len(parts) - 1:
                if node_kind.get(key) == "file":
                    raise ReleaseBuildError(f"Archive file/directory ancestor conflict at {'/'.join(parts[: index + 1])!r}")
                node_kind[key] = "directory"
            else:
                if node_kind.get(key) == "directory":
                    raise ReleaseBuildError(f"Archive file/directory ancestor conflict at {name!r}")
                node_kind[key] = "file"


def _iter_source_files(source: Path) -> list[tuple[str, Path]]:
    if not source.is_dir():
        raise ReleaseBuildError(f"Expected source directory does not exist: {source}")
    members: list[tuple[str, Path]] = []
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ReleaseBuildError(f"Symlink is not allowed in release inputs: {path.relative_to(source).as_posix()}")
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(source).as_posix()
        _safe_relative_name(relative)
        members.append((relative, path))
    members.sort(key=lambda item: item[0])
    _check_member_collisions(name for name, _ in members)
    return members


def write_deterministic_zip(source: Path, archive: Path) -> str:
    """Write sorted regular-file entries with normalized ZIP metadata."""
    members = _iter_source_files(source)
    if not members:
        raise ReleaseBuildError(f"Refusing to create an empty ZIP from {source}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_name(archive.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as zf:
            for name, path in members:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.flag_bits |= 0x800
                zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise ReleaseBuildError(f"Generated ZIP CRC check failed at {bad}")
        os.replace(temporary, archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    return sha256_file(archive)



def render_release_text(text: str, version: str) -> str:
    """Render the sole release-version token in an authored Markdown asset."""
    rendered = text.replace("{{PBF_VERSION}}", version)
    if "{{PBF_VERSION}}" in rendered:
        raise ReleaseBuildError("Unresolved PBF_VERSION token in release asset.")
    return rendered


def validate_outer_manifest_references(manifest: dict, nested_member_hashes: dict[str, str]) -> None:
    """Ensure outer-manifest references to inner files are scoped and hash-accurate."""
    if manifest.get("license") != "Apache-2.0" or manifest.get("license_file") != "LICENSE":
        raise ReleaseBuildError("Outer manifest must declare Apache-2.0 and the root LICENSE file.")
    nested_path = manifest.get("nested_agent_package")
    nested_sha = manifest.get("nested_agent_package_sha256")
    if not isinstance(nested_path, str):
        raise ReleaseBuildError("Outer manifest is missing its nested-agent package path.")
    _safe_relative_name(nested_path)
    if not isinstance(nested_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", nested_sha):
        raise ReleaseBuildError("Outer manifest has an invalid nested-agent package SHA-256.")
    contents = manifest.get("nested_package_contents")
    if not isinstance(contents, dict) or set(contents) != {"package_manifest", "bootstrap_runtime", "workspace_starter"}:
        raise ReleaseBuildError("Outer manifest must scope the package manifest and archives under nested_package_contents.")
    package_manifest = contents.get("package_manifest")
    if package_manifest != "PACKAGE-MANIFEST.json":
        raise ReleaseBuildError("Outer manifest package-manifest path must be exactly PACKAGE-MANIFEST.json.")
    _safe_relative_name(package_manifest)
    if package_manifest not in nested_member_hashes:
        raise ReleaseBuildError(f"Nested package manifest path does not exist inside the nested ZIP: {package_manifest}")
    for key in ("bootstrap_runtime", "workspace_starter"):
        item = contents.get(key)
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ReleaseBuildError(f"Outer manifest has an invalid nested {key} reference.")
        relative = item.get("path")
        digest = item.get("sha256")
        if not isinstance(relative, str):
            raise ReleaseBuildError(f"Outer manifest has an invalid nested {key} path.")
        _safe_relative_name(relative)
        if relative not in nested_member_hashes:
            raise ReleaseBuildError(f"Outer manifest nested {key} path does not exist: {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReleaseBuildError(f"Outer manifest has an invalid nested {key} SHA-256.")
        if nested_member_hashes[relative] != digest:
            raise ReleaseBuildError(f"Outer manifest nested {key} SHA-256 does not match its inner package file: {relative}")

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")



def append_final_bootstrap_evidence(
    evidence_path: Path,
    bootstrap_result: dict,
    *,
    provenance_audit_passed: bool,
) -> None:
    """Append observed final-package bootstrap results to the build evidence."""
    if not isinstance(bootstrap_result, dict) or bootstrap_result.get("status") != "verified":
        raise ReleaseBuildError("Cannot record final bootstrap evidence without a verified bootstrap result.")
    if bootstrap_result.get("temporary_runtime_removed") is not True:
        raise ReleaseBuildError("Cannot record final bootstrap evidence without observed temporary-runtime cleanup.")
    if provenance_audit_passed is not True:
        raise ReleaseBuildError("Cannot record final bootstrap evidence before the post-provenance state audit passes.")
    checks = bootstrap_result.get("checks")
    required_checks = {
        "bootstrap runtime verification passed",
        "workspace creation completed",
        "workspace check --strict passed",
        "workspace index --check passed",
        "workspace audit-state --strict passed",
    }
    if not isinstance(checks, list) or not required_checks.issubset(set(checks)):
        raise ReleaseBuildError("Final bootstrap result does not contain every required verification check.")
    try:
        content = evidence_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReleaseBuildError(f"Cannot read intermediate build evidence: {exc}") from exc
    heading = "## Final nested-package bootstrap"
    if heading in content:
        raise ReleaseBuildError("Final nested-package bootstrap evidence was already appended.")
    if "performed by the final release integration stage" in content or '{"pending"' in content:
        raise ReleaseBuildError("Intermediate build evidence contains an obsolete placeholder.")
    lines = [
        "",
        heading,
        "",
        "- Result: passed against the nested package extracted from the exact final outer ZIP.",
        "- Structured helper status: `verified`.",
        "- Verified operations:",
    ]
    lines.extend(f"  - {check}." for check in checks)
    lines.extend([
        "- Temporary runtime cleanup: confirmed by checking that the temporary extraction path no longer exists.",
        "- Setup provenance: written to the existing workspace STATE field; the subsequent strict state audit passed.",
        "- Git: remained uninitialized.",
        "",
    ])
    evidence_path.write_text(content.rstrip() + "\n" + "\n".join(lines), encoding="utf-8", newline="\n")
    final_content = evidence_path.read_text(encoding="utf-8")
    if heading not in final_content or "pending" in final_content.lower():
        raise ReleaseBuildError("Final build evidence did not contain a complete bootstrap result.")


def write_checksum_inventory(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for relative, path in _iter_source_files(root):
        if relative == "SHA256SUMS.txt":
            continue
        files[relative] = sha256_file(path)
    content = "".join(f"{digest}  {name}\n" for name, digest in sorted(files.items()))
    (root / "SHA256SUMS.txt").write_text(content, encoding="utf-8", newline="\n")
    return files


def verify_checksum_inventory(root: Path) -> dict[str, str]:
    sums = root / "SHA256SUMS.txt"
    if not sums.is_file():
        raise ReleaseBuildError(f"Checksum inventory is missing: {sums}")
    checksums: dict[str, str] = {}
    for number, line in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ReleaseBuildError(f"Malformed checksum inventory line {number}")
        digest, name = match.groups()
        _safe_relative_name(name)
        if name in checksums:
            raise ReleaseBuildError(f"Duplicate checksum path: {name}")
        checksums[name] = digest
    actual = {name for name, _ in _iter_source_files(root) if name != "SHA256SUMS.txt"}
    if set(checksums) != actual:
        raise ReleaseBuildError(f"Checksum inventory mismatch; missing={sorted(actual-set(checksums))}; extra={sorted(set(checksums)-actual)}")
    for name, expected in checksums.items():
        if sha256_file(root / Path(*PurePosixPath(name).parts)) != expected:
            raise ReleaseBuildError(f"SHA-256 mismatch: {name}")
    return checksums


def extract_validated_zip(archive: Path, destination: Path) -> list[str]:
    if destination.exists():
        raise ReleaseBuildError(f"Extraction destination already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            infos = zf.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ReleaseBuildError(f"Unexpected archive member count in {archive.name}")
            names: list[str] = []
            total = 0
            for info in infos:
                pure = _safe_relative_name(info.filename)
                names.append(info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode) or info.flag_bits & 1:
                    raise ReleaseBuildError(f"Link/encrypted archive member is not allowed: {info.filename}")
                if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise ReleaseBuildError(f"Archive member exceeds size limit: {info.filename}")
                total += info.file_size
                if total > MAX_ARCHIVE_TOTAL_BYTES:
                    raise ReleaseBuildError("Archive exceeds total uncompressed-size limit")
                if info.file_size and (not info.compress_size or info.file_size / info.compress_size > MAX_ARCHIVE_RATIO):
                    raise ReleaseBuildError(f"Suspicious compression ratio: {info.filename}")
            _check_member_collisions(names)
            for info in infos:
                if info.is_dir():
                    continue
                relative = _safe_relative_name(info.filename)
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
        return names
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def copy_runtime_inputs(source_root: Path, target: Path) -> None:
    """Copy only the source/runtime inputs needed for workspace creation."""
    required = (
        "VERSION", "LICENSE", "bp.py", "framework-dev/SOURCE-MANIFEST.json",
    )
    for relative in required:
        src = source_root / relative
        if not src.is_file() or src.is_symlink():
            raise ReleaseBuildError(f"Required runtime input missing or unsafe: {relative}")
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    for relative in ("_framework", "starter", "src/blueprint_framework"):
        src = source_root / relative
        dest = target / relative
        if not src.is_dir() or src.is_symlink():
            raise ReleaseBuildError(f"Required runtime directory missing or unsafe: {relative}")
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _iter_source_files(target)


def count_tests(source_root: Path) -> tuple[int, list[tuple[str, int]]]:
    files = sorted((source_root / "framework-dev/tests").glob("test_*.py"), key=lambda p: p.name)
    bootstrap = source_root / "tools/agent-bootstrap/tests/test_bootstrap.py"
    if bootstrap.is_file():
        files.append(bootstrap)
    inventory: list[tuple[str, int]] = []
    total = 0
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"))
        inventory.append((path.relative_to(source_root).as_posix(), count))
        total += count
    return total, inventory


def run_logged(command: list[str], cwd: Path, log_path: Path, label: str, timeout: int = 600) -> str:
    """Run a command, tee output to a local log and enforce a wall-clock limit."""
    from queue import Queue, Empty
    from threading import Thread
    from time import monotonic

    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
    except OSError as exc:
        raise ReleaseBuildError(f"Could not start {label}: {exc}") from exc
    if process.stdout is None:
        process.kill()
        raise ReleaseBuildError(f"Could not capture output for {label}.")
    output_queue: Queue[str | None] = Queue()

    def read_output() -> None:
        try:
            for line in process.stdout:
                output_queue.put(line)
        finally:
            output_queue.put(None)

    reader = Thread(target=read_output, name="pbf-release-log-reader", daemon=True)
    reader.start()
    chunks: list[str] = []
    deadline = monotonic() + timeout
    finished_reading = False
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        while not finished_reading:
            remaining = deadline - monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                reader.join(timeout=2)
                if process.stdout is not None and not process.stdout.closed:
                    process.stdout.close()
                tail = "".join(chunks[-35:])
                raise ReleaseBuildError(f"{label} timed out after {timeout} seconds; see {log_path}\n{tail}")
            try:
                line = output_queue.get(timeout=min(0.5, remaining))
            except Empty:
                if process.poll() is not None and not reader.is_alive():
                    break
                continue
            if line is None:
                finished_reading = True
                continue
            chunks.append(line)
            log.write(line)
            log.flush()
            sys.stdout.write(line)
            sys.stdout.flush()
    return_code = process.wait()
    reader.join(timeout=2)
    if process.stdout is not None and not process.stdout.closed:
        process.stdout.close()
    output = "".join(chunks)
    if return_code != 0:
        tail = "\n".join(output.splitlines()[-35:])
        raise ReleaseBuildError(f"{label} failed with exit code {return_code}. Log: {log_path}\n{tail}")
    return output


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise ReleaseBuildError(f"Release asset is missing or not a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _copy_versioned_text(source: Path, destination: Path, version: str) -> None:
    if not source.is_file() or source.is_symlink():
        raise ReleaseBuildError(f"Release asset is missing or not a regular file: {source}")
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReleaseBuildError(f"Cannot read versioned release asset {source}: {exc}") from exc
    rendered = render_release_text(text, version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8", newline="\n")


def validate_release_assets(root: Path = ROOT) -> None:
    required = [
        "LICENSE", "starter/LICENSE", "starter/PBF-LICENSE-SCOPE.md",
        "release-assets/README-RELEASE.md", "release-assets/QUICKSTART.md",
        "release-assets/agent/AGENT-OPERATING-INSTRUCTIONS.md", "release-assets/agent/AGENT-STARTUP-PROMPT.md",
        "tools/agent-bootstrap/bootstrap.py",
    ]
    required.extend(f"release-assets/docs/{name}" for name in (
        "README.md", "PBF-Architecture-and-Technical-Reference.md", "PBF-Maintainer-Handbook.md",
        "PBF-Project-Overview-and-Method.md", "PBF-Quality-Assurance-and-Review-Policy.md",
        "PBF-Release-Notes-and-Verification.md", "PBF-User-Guide.md",
    ))
    for relative in required:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ReleaseBuildError(f"Required release asset is missing or unsafe: {relative}")
    if (root / "LICENSE").read_bytes() != (root / "starter/LICENSE").read_bytes():
        raise ReleaseBuildError("LICENSE and starter/LICENSE must be byte-identical.")
    scope_notice = (root / "starter/PBF-LICENSE-SCOPE.md").read_text(encoding="utf-8").lower()
    if "does **not** automatically apply" not in scope_notice or "owner-authored" not in scope_notice:
        raise ReleaseBuildError("The workspace PBF license-scope notice is missing or incomplete.")
    license_text = (root / "LICENSE").read_bytes()[:512]
    if b"Apache License" not in license_text or b"Version 2.0, January 2004" not in license_text:
        raise ReleaseBuildError("The root LICENSE must contain the canonical Apache License 2.0 text.")
    current_version = read_version(root)
    for asset in sorted((root / "release-assets").rglob("*.md")):
        try:
            text = asset.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ReleaseBuildError(f"Cannot read release text asset {asset}: {exc}") from exc
        if current_version in text:
            raise ReleaseBuildError(f"Release asset hard-codes the current version; use {{PBF_VERSION}} template token: {asset.relative_to(root).as_posix()}")
    docs_index = (root / "release-assets/docs/README.md").read_text(encoding="utf-8")
    for filename in (
        "PBF-Architecture-and-Technical-Reference.md", "PBF-Maintainer-Handbook.md",
        "PBF-Project-Overview-and-Method.md", "PBF-Quality-Assurance-and-Review-Policy.md",
        "PBF-Release-Notes-and-Verification.md", "PBF-User-Guide.md",
    ):
        if filename not in docs_index:
            raise ReleaseBuildError(f"Documentation index does not list {filename}")


def _copy_runtime_doc_assets(asset_root: Path, stage: Path, version: str) -> list[str]:
    (stage / "docs").mkdir(parents=True, exist_ok=True)
    names = [
        "README.md", "PBF-Architecture-and-Technical-Reference.md", "PBF-Maintainer-Handbook.md",
        "PBF-Project-Overview-and-Method.md", "PBF-Quality-Assurance-and-Review-Policy.md",
        "PBF-Release-Notes-and-Verification.md", "PBF-User-Guide.md",
    ]
    for name in names:
        _copy_versioned_text(asset_root / "docs" / name, stage / "docs" / name, version)
    return [f"docs/{name}" for name in names]


def build_package(source_root: Path, work_root: Path, version: str, architecture: str, logs_dir: Path) -> tuple[Path, dict]:
    validate_release_assets(source_root)
    build_checkout = work_root / "developer-checkout"
    shutil.copytree(
        source_root, build_checkout,
        ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc", ".venv", ".pytest_cache", ".mypy_cache"),
    )
    # Execute the existing framework build in an isolated checkout. This keeps
    # the developer tree and any pre-existing dist files untouched.
    print("[release] Stage 1/5: maintainer verification, full maintained tests and workspace starter build", flush=True)
    build_log = logs_dir / "workspace-build.log"
    run_logged([sys.executable, "-B", "bp.py", "build"], build_checkout, build_log, "Maintainer verification and workspace build")

    test_count, test_inventory = count_tests(build_checkout)
    workspace_archive = build_checkout / "dist" / f"project-blueprint-workspace-{version}.zip"
    if not workspace_archive.is_file():
        raise ReleaseBuildError("Existing bp.py build did not produce the expected workspace starter archive.")
    workspace_sha = sha256_file(workspace_archive)
    workspace_extract = work_root / "workspace-starter-extracted"
    workspace_names = extract_validated_zip(workspace_archive, workspace_extract)

    # Independently verify the curated runtime after extracting its exact ZIP.
    print("[release] Stage 2/5: curated bootstrap runtime assembly and verification", flush=True)
    runtime_stage = work_root / "bootstrap-runtime"
    runtime_stage.mkdir()
    copy_runtime_inputs(build_checkout, runtime_stage)
    runtime_archive = work_root / f"project-blueprint-framework-{version}-bootstrap-runtime.zip"
    runtime_sha = write_deterministic_zip(runtime_stage, runtime_archive)
    runtime_extract = work_root / "bootstrap-runtime-extracted"
    extract_validated_zip(runtime_archive, runtime_extract)
    runtime_log = logs_dir / "bootstrap-runtime-verify.log"
    run_logged([sys.executable, "-B", "bp.py", "verify", "--scope", "bootstrap"], runtime_extract, runtime_log, "Bootstrap runtime verification")

    # Assemble and checksum the exact nested package.
    print("[release] Stage 3/5: nested agent package assembly and integrity verification", flush=True)
    package_stage = work_root / "agent-package"
    package_stage.mkdir()
    _copy_file(source_root / "LICENSE", package_stage / "LICENSE")
    _copy_versioned_text(source_root / "release-assets/agent/AGENT-OPERATING-INSTRUCTIONS.md", package_stage / "AGENT-OPERATING-INSTRUCTIONS.md", version)
    _copy_versioned_text(source_root / "release-assets/agent/AGENT-STARTUP-PROMPT.md", package_stage / "AGENT-STARTUP-PROMPT.md", version)
    _copy_file(source_root / "tools/agent-bootstrap/bootstrap.py", package_stage / "tools/bootstrap.py")
    runtime_relative = f"archives/project-blueprint-framework-{version}-bootstrap-runtime.zip"
    workspace_relative = f"archives/project-blueprint-workspace-{version}.zip"
    _copy_file(runtime_archive, package_stage / runtime_relative)
    _copy_file(workspace_archive, package_stage / workspace_relative)
    package_manifest = {
        "package_id": "PBF-Agent-Package",
        "package_name": "Project Blueprint Framework Agent Package",
        "package_schema_version": 1,
        "license": "Apache-2.0",
        "license_file": "LICENSE",
        "framework_version": version,
        "workspace_architecture": architecture,
        "minimum_python": "3.11",
        "setup_method": "agent-assisted-recommended",
        "manual_setup_supported": True,
        "bootstrap_runtime_archive": runtime_relative,
        "workspace_archive": workspace_relative,
        "bootstrap_runtime_sha256": runtime_sha,
        "workspace_archive_sha256": workspace_sha,
        "bootstrap_helper": "tools/bootstrap.py",
        "notes": [
            "The package carries a curated, verified bootstrap runtime, not the full maintainer source repository.",
            "The helper delegates workspace creation to the existing bp.py new command.",
            "The helper requires separate owner approval for the exact destination before invocation.",
            "The helper does not initialize Git, install software or make network requests.",
        ],
    }
    write_json(package_stage / "PACKAGE-MANIFEST.json", package_manifest)
    package_files = write_checksum_inventory(package_stage)
    verify_checksum_inventory(package_stage)
    # Import from the exact developer helper and validate the package contract.
    sys.path.insert(0, str(source_root / "tools/agent-bootstrap"))
    try:
        from bootstrap import load_and_verify_package, inspect_zip  # type: ignore
        loaded = load_and_verify_package(package_stage)
        if loaded != package_manifest:
            raise ReleaseBuildError("Nested package manifest changed unexpectedly during validation.")
        inspect_zip(package_stage / runtime_relative)
        inspect_zip(package_stage / workspace_relative)
    finally:
        if sys.path and sys.path[0] == str(source_root / "tools/agent-bootstrap"):
            sys.path.pop(0)
        sys.modules.pop("bootstrap", None)
    package_zip = work_root / f"PBF-Agent-Package-v{version}.zip"
    package_sha = write_deterministic_zip(package_stage, package_zip)

    # Build evidence is authored from the commands and hashes observed above.
    framework_version = version
    test_rows = "\n".join(f"| `{path}` | {count} |" for path, count in test_inventory)
    workspace_file_count = len([name for name in workspace_names if not name.endswith("/")])
    runtime_member_count = len([name for name in _iter_source_files(runtime_stage)])
    evidence = f"""# PBF {framework_version} — Build Verification\n\n\
This report is generated from this exact release build. It records commands that completed successfully; it is not a publisher signature.\n\n\
## Build identity\n\n\
- Framework version: `{framework_version}` (read from root `VERSION`)\n- Workspace architecture revision: `{architecture}`\n- Minimum declared Python: `3.11`\n- Build interpreter: met the declared Python 3.11+ minimum; host-specific version and platform identifiers are intentionally not published.\n\n\
## Maintained test suite\n\n\
The existing `bp.py build` command completed successfully. It ran the maintained test modules before creating and validating the workspace starter. Test inventory was counted from the source AST after the successful command.\n\n\
| Module | Test methods |\n|---|---:|\n{test_rows}\n| **Total** | **{test_count}** |\n\n\
## Generated artifacts\n\n\
| Artifact | Members/files | SHA-256 |\n|---|---:|---|\n| Workspace starter ZIP | {workspace_file_count} | `{workspace_sha}` |\n| Curated bootstrap runtime ZIP | {runtime_member_count} | `{runtime_sha}` |\n| Nested agent package ZIP | {len(package_files)} payload files | `{package_sha}` |\n\n\
## Verification performed\n\n\
- Maintainer source verification and maintained tests: passed through the existing `bp.py build` default workflow.\n- Workspace starter: produced by the existing `bp.py build`, then CRC-checked and extracted into a fresh temporary directory.\n- Bootstrap runtime: built from the explicitly required runtime inputs, then checksum/CRC-checked, extracted and passed `bp.py verify --scope bootstrap`.\n- Nested agent package: exact inventory and SHA-256 file list generated and independently verified; package manifest archive hashes cross-checked; both embedded archives passed ZIP inspection.\n- Final nested-package bootstrap results are appended after the exact final outer ZIP has been extracted and tested.\n\n\
## Compatibility and security limits\n\n\
This build was executed with an interpreter meeting the declared Python 3.11+ minimum. This report does not certify every Python minor version, native Windows, a second AI harness or universal agent compatibility. PBF instructions do not create an OS-level sandbox. For public downloads, compare the outer ZIP SHA-256 with the value in the official GitHub Release description; this relies on trust in the project GitHub account/repository and is not a detached cryptographic signature.\n"""
    evidence_path = work_root / "BUILD-VERIFICATION.md"
    evidence_path.write_text(evidence, encoding="utf-8", newline="\n")

    # Assemble the outer user-facing release. No review prompt/ZIP is accepted here.
    print("[release] Stage 4/5: outer Agent-First release assembly", flush=True)
    outer_stage = work_root / "outer-release"
    outer_stage.mkdir()
    _copy_file(source_root / "LICENSE", outer_stage / "LICENSE")
    _copy_versioned_text(source_root / "release-assets/README-RELEASE.md", outer_stage / "README.md", version)
    _copy_versioned_text(source_root / "release-assets/QUICKSTART.md", outer_stage / "QUICKSTART.md", version)
    documentation_files = _copy_runtime_doc_assets(source_root / "release-assets", outer_stage, version)
    (outer_stage / "release-evidence").mkdir(parents=True)
    _copy_file(evidence_path, outer_stage / "release-evidence/BUILD-VERIFICATION.md")
    _copy_file(package_zip, outer_stage / f"agent-package/{package_zip.name}")
    nested_relative = f"agent-package/{package_zip.name}"
    manifest = {
        "schema_version": 1,
        "product": "Project Blueprint Framework",
        "license": "Apache-2.0",
        "license_file": "LICENSE",
        "framework_version": version,
        "workspace_architecture": architecture,
        "distribution": "Agent-First Release",
        "recommended_setup": "agent-assisted",
        "manual_setup_supported": True,
        "minimum_python": "3.11",
        "primary_user_download": f"PBF-v{version}-Agent-First-Release.zip",
        "nested_agent_package": nested_relative,
        "nested_agent_package_sha256": package_sha,
        "nested_package_contents": {
            "package_manifest": "PACKAGE-MANIFEST.json",
            "bootstrap_runtime": {"path": runtime_relative, "sha256": runtime_sha},
            "workspace_starter": {"path": workspace_relative, "sha256": workspace_sha},
        },
        "documentation_files": documentation_files,
        "release_evidence_files": ["release-evidence/BUILD-VERIFICATION.md"],
        "integrity_note": "For public downloads, compare the outer ZIP SHA-256 with the digest published in the official PBF GitHub Release description. This relies on trust in the project GitHub account/repository; SHA-256 detects a mismatch but is not a detached cryptographic signature.",
    }
    write_json(outer_stage / "RELEASE-MANIFEST.json", manifest)
    outer_files = write_checksum_inventory(outer_stage)
    verify_checksum_inventory(outer_stage)
    output = work_root / f"PBF-v{version}-Agent-First-Release.zip"
    outer_sha = write_deterministic_zip(outer_stage, output)

    # Validate the exact final outer ZIP and repeat the complete nested bootstrap.
    print("[release] Stage 5/5: final-package extraction and end-to-end workspace bootstrap", flush=True)
    final_extract = work_root / "outer-extracted"
    extract_validated_zip(output, final_extract)
    verify_checksum_inventory(final_extract)
    final_manifest = json.loads((final_extract / "RELEASE-MANIFEST.json").read_text(encoding="utf-8"))
    nested_path = final_extract / final_manifest["nested_agent_package"]
    if sha256_file(nested_path) != final_manifest["nested_agent_package_sha256"]:
        raise ReleaseBuildError("Final outer manifest's nested-agent ZIP hash does not match its payload.")
    nested_extract = work_root / "nested-agent-extracted"
    extract_validated_zip(nested_path, nested_extract)
    verify_checksum_inventory(nested_extract)
    nested_member_hashes = {name: sha256_file(path) for name, path in _iter_source_files(nested_extract)}
    validate_outer_manifest_references(final_manifest, nested_member_hashes)
    sys.path.insert(0, str(source_root / "tools/agent-bootstrap"))
    try:
        from bootstrap import load_and_verify_package  # type: ignore
        load_and_verify_package(nested_extract)
    finally:
        if sys.path and sys.path[0] == str(source_root / "tools/agent-bootstrap"):
            sys.path.pop(0)
        sys.modules.pop("bootstrap", None)

    smoke_parent = work_root / "smoke-parent"
    smoke_parent.mkdir()
    smoke_destination = smoke_parent / "Release Smoke Blueprint"
    smoke_log = logs_dir / "end-to-end-bootstrap.log"
    smoke_output = run_logged(
        [sys.executable, "-B", "tools/bootstrap.py", "--package-root", str(nested_extract),
         "--name", "Release Smoke", "--destination", str(smoke_destination),
         "--approved-destination", str(smoke_destination)],
        nested_extract, smoke_log, "Final release bootstrap smoke test", timeout=300,
    )
    result_match = re.search(r"PBF_BOOTSTRAP_RESULT=(\{[^\n]+\})", smoke_output)
    if not result_match:
        raise ReleaseBuildError("Final bootstrap did not emit its structured PBF_BOOTSTRAP_RESULT.")
    bootstrap_result = json.loads(result_match.group(1))
    if bootstrap_result.get("status") != "verified" or bootstrap_result.get("temporary_runtime_removed") is not True:
        raise ReleaseBuildError("Final bootstrap result did not report verified setup and temporary runtime cleanup.")
    if not smoke_destination.is_dir() or (smoke_destination / ".git").exists():
        raise ReleaseBuildError("Final bootstrap smoke test did not create the expected non-Git workspace.")
    if not (smoke_destination / "LICENSE").is_file() or (smoke_destination / "LICENSE").read_bytes() != (source_root / "LICENSE").read_bytes():
        raise ReleaseBuildError("Generated workspace does not contain the exact Apache-2.0 LICENSE text.")
    scope_path = smoke_destination / "PBF-LICENSE-SCOPE.md"
    if not scope_path.is_file() or scope_path.read_bytes() != (source_root / "starter/PBF-LICENSE-SCOPE.md").read_bytes():
        raise ReleaseBuildError("Generated workspace does not contain the exact PBF license-scope notice.")

    # Exercise the documented post-bootstrap provenance update in the existing
    # STATE field, then rerun the final state audit. This is a synthetic smoke
    # value; real users' entries are supplied by their agent after setup.
    state_path = smoke_destination / "_control/STATE.md"
    state_text = state_path.read_text(encoding="utf-8")
    pending = "Pending — record setup date, method and verification result after creation"
    if pending not in state_text:
        raise ReleaseBuildError("Generated workspace is missing the approved setup-provenance field.")
    provenance = f"{datetime.now(timezone.utc).date().isoformat()}; agent-assisted; PBF {version}; verified"
    state_path.write_text(state_text.replace(pending, provenance, 1), encoding="utf-8", newline="\n")
    provenance_log = logs_dir / "post-provenance-state-audit.log"
    run_logged([sys.executable, "-B", "bp.py", "audit-state", "--strict"], smoke_destination, provenance_log, "Post-provenance workspace state audit")

    evidence_path = outer_stage / "release-evidence/BUILD-VERIFICATION.md"
    append_final_bootstrap_evidence(
        evidence_path,
        bootstrap_result,
        provenance_audit_passed=True,
    )
    # Evidence changed after initial checksums; regenerate the outer inventory and ZIP.
    write_json(outer_stage / "RELEASE-MANIFEST.json", manifest)
    write_checksum_inventory(outer_stage)
    verify_checksum_inventory(outer_stage)
    outer_sha = write_deterministic_zip(outer_stage, output)
    # Final CRC + inventory validation after final evidence update.
    final_check = work_root / "outer-final-check"
    extract_validated_zip(output, final_check)
    verify_checksum_inventory(final_check)
    if sha256_file(output) != outer_sha:
        raise ReleaseBuildError("Final outer ZIP hash changed unexpectedly after verification.")

    return output, {
        "framework_version": version,
        "workspace_architecture": architecture,
        "test_count": test_count,
        "test_inventory": test_inventory,
        "workspace_archive_sha256": workspace_sha,
        "bootstrap_runtime_sha256": runtime_sha,
        "nested_package_sha256": package_sha,
        "outer_release_sha256": outer_sha,
        "outer_file_count": len(outer_files),
        "workspace_file_count": workspace_file_count,
        "runtime_file_count": runtime_member_count,
        "bootstrap_result": bootstrap_result,
    }


def build_release(force: bool = False, root: Path = ROOT) -> tuple[Path, dict]:
    if sys.version_info < MINIMUM_PYTHON:
        raise ReleaseBuildError("Release builder requires Python 3.11 or newer.")
    root = root.resolve()
    version = read_version(root)
    architecture = read_architecture_revision(root)
    validate_release_assets(root)
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    output = dist / f"PBF-v{version}-Agent-First-Release.zip"
    if output.exists() and not force:
        raise ReleaseBuildError(f"Release output already exists; refusing to overwrite: {output} (use --force after reviewing it)")
    logs_dir = dist / "build-logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pbf-release-build-") as temporary:
        work_root = Path(temporary)
        candidate, result = build_package(root, work_root, version, architecture, logs_dir)
        staged_output = dist / (output.name + ".candidate")
        try:
            shutil.copyfile(candidate, staged_output)
            with zipfile.ZipFile(staged_output, "r") as zf:
                bad = zf.testzip()
                if bad is not None:
                    raise ReleaseBuildError(f"Candidate outer ZIP failed CRC validation at {bad}")
            if output.exists() and not force:
                raise ReleaseBuildError(f"Release output appeared during build; refusing to overwrite: {output}")
            os.replace(staged_output, output)
        finally:
            if staged_output.exists():
                staged_output.unlink()
    return output, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PBF Agent-First Release ZIP from the developer repository.")
    parser.add_argument("--force", action="store_true", help="replace the existing release ZIP only after a successful new build")
    args = parser.parse_args(argv)
    try:
        output, result = build_release(force=args.force)
    except (OSError, ValueError, ReleaseBuildError, zipfile.BadZipFile) as exc:
        print(f"RELEASE BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"RELEASE BUILD VERIFIED: {output}")
    print(f"Framework: {result['framework_version']} | workspace architecture: {result['workspace_architecture']}")
    print(f"Maintained test methods: {result['test_count']}")
    print(f"Outer files: {result['outer_file_count']} | workspace files: {result['workspace_file_count']} | runtime files: {result['runtime_file_count']}")
    print(f"SHA-256: {result['outer_release_sha256']}")
    print("The Agent-First Release ZIP is the only product artifact produced by this build.")
    print(f"Local build logs: {ROOT / 'dist' / 'build-logs'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
