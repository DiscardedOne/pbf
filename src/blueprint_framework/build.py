"""Deterministic workspace starter assembly and release packaging."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from workspace_paths import SourcePaths, WorkspacePaths, normalized_file_sha256, validate_framework_manifest, validate_workspace_structure  # type: ignore
from .source_cli import validate_agents_instructions, verify_source

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".txt",
    ".csv", ".xml", ".svg", ".html", ".htm", ".css", ".js", ".ts",
    ".sh", ".ps1", ".bat", ".cmd", ".ini", ".cfg", ".conf", ".properties",
}


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitattributes", ".gitignore", "AGENTS.md", "bp.py", "LICENSE"} or path.name.endswith(".json.template") or path.name.endswith(".md.template")


def _canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if _is_text(path):
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError(f"UTF-8 BOM is not allowed in packaged text: {path}")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return raw


def _copy_tree_files(source: Path, target: Path, *, prefix: str = "") -> None:
    for item in sorted(source.rglob("*"), key=lambda p: p.as_posix()):
        if item.is_symlink():
            raise ValueError(f"Symlink cannot be included in workspace package: {item}")
        if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        relative = item.relative_to(source).as_posix()
        destination = target / prefix / relative if prefix else target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_canonical_bytes(item))


def _write_manifest(workspace_root: Path, version: str) -> Path:
    managed: dict[str, str] = {}
    framework_root = workspace_root / "_framework"
    for item in sorted(framework_root.rglob("*"), key=lambda p: p.as_posix()):
        if not item.is_file() or item.name == "FRAMEWORK-MANIFEST.json" or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        rel = item.relative_to(workspace_root).as_posix()
        managed[rel] = normalized_file_sha256(item)
    for rel in ("AGENTS.md", "bp.py"):
        managed[rel] = normalized_file_sha256(workspace_root / rel)
    manifest = {
        "manifest_schema_version": 1,
        "framework_version": version,
        "hash_algorithm": "sha256",
        "text_hash_policy": "utf8-lf-normalized-v1",
        "workspace_schema_versions_supported": [1],
        "layout_versions_supported": [1],
        "files": {key: managed[key] for key in sorted(managed)},
    }
    path = framework_root / "FRAMEWORK-MANIFEST.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _assemble(paths: SourcePaths, target: Path, version: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    # One canonical root launcher; starter/ must never carry its own copy.
    for name in (".gitignore", ".gitattributes"):
        (target / name).write_bytes(_canonical_bytes(paths.starter / name))
    (target / "LICENSE").write_bytes(_canonical_bytes(paths.starter / "LICENSE"))
    (target / "PBF-LICENSE-SCOPE.md").write_bytes(_canonical_bytes(paths.starter / "PBF-LICENSE-SCOPE.md"))
    (target / "bp.py").write_bytes(paths.launcher.read_bytes())
    (target / "AGENTS.md").write_bytes((paths.starter / "AGENTS.md").read_bytes())

    _copy_tree_files(paths.root / "_framework", target / "_framework")

    readme_template = paths.starter / "README.md.template"
    readme = _canonical_bytes(readme_template)
    (target / "README.md").write_bytes(readme)
    # Everything below starter/ is project-owned seed content. Preserve the
    # non-live workspace marker name so only `new` materializes a live marker.
    _copy_tree_files(paths.starter / "docs", target / "docs")
    _copy_tree_files(paths.starter / "_control", target / "_control")
    if (target / "_control" / "WORKSPACE.json").exists():
        raise ValueError("Starter assembly unexpectedly produced a live WORKSPACE.json")
    _write_manifest(target, version)


def _materialize_validation_copy(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination)
    template_path = destination / "_control" / "WORKSPACE.json.template"
    config = json.loads(template_path.read_text(encoding="utf-8"))
    config.setdefault("project", {})["name"] = "Build Validation Project"
    live = destination / "_control" / "WORKSPACE.json"
    live.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    template_path.unlink()
    readme_path = destination / "README.md"
    content = readme_path.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", "Build Validation Project")
    if "{{PROJECT_NAME}}" in content:
        raise ValueError("README template contains an unresolved project-name token")
    readme_path.write_text(content, encoding="utf-8", newline="\n")


def _normalize_workspace_text(root: Path) -> None:
    text_suffixes = TEXT_SUFFIXES | {".md", ".py", ".json", ".jsonl"}
    for item in root.rglob("*"):
        if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        if item.suffix.lower() in text_suffixes or item.name in {".gitattributes", ".gitignore", "LICENSE"}:
            raw = item.read_bytes()
            content = raw.decode("utf-8")
            if content.startswith("\ufeff"):
                raise ValueError(f"Generated text contains a UTF-8 BOM: {item.relative_to(root).as_posix()}")
            item.write_bytes(content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def _check_generated_workspace(root: Path) -> None:
    # Generate project-owned dashboard/navigation from the actual materialized
    # workspace before validating freshness. These commands do not fabricate
    # decisions, approvals or session history.
    for command in ((sys.executable, str(root / "bp.py"), "status", "--write"),
                    (sys.executable, str(root / "bp.py"), "index")):
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            raise ValueError(f"Initial workspace generation failed ({' '.join(command[2:])}, exit {result.returncode})")
    _normalize_workspace_text(root)
    paths = WorkspacePaths.from_root(root)
    defaults = json.loads(paths.defaults.read_text(encoding="utf-8"))
    structural = validate_workspace_structure(paths, defaults)
    drift = validate_framework_manifest(paths)
    errors = [message for severity, message in structural + drift if severity == "error"]
    if errors:
        raise ValueError("Generated workspace failed path/default/manifest validation:\n- " + "\n- ".join(errors))
    agent_issues = validate_agents_instructions(paths.agent_instructions)
    if agent_issues:
        raise ValueError("Generated AGENTS.md failed hygiene checks:\n- " + "\n- ".join(agent_issues))

    # The same public workspace CLI that a user receives must validate this
    # assembled workspace. This avoids a separate, weaker build-only checker.
    for command in ((sys.executable, str(paths.launcher), "check", "--strict"),
                    (sys.executable, str(paths.launcher), "index", "--check")):
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            raise ValueError(f"Generated workspace command failed ({' '.join(command[2:])}, exit {result.returncode})")

    # Validate all generated text bytes independently of the runtime parser.
    for item in root.rglob("*"):
        if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        if _is_text(item):
            raw = item.read_bytes()
            raw.decode("utf-8")
            if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
                raise ValueError(f"Generated text is not UTF-8 without BOM/LF: {item.relative_to(root).as_posix()}")

    # No real project documents are created by a fresh workspace.
    expected_docs = {"README.md", "04-architecture/adr/README.md", "99-appendix/research/README.md"}
    actual_docs = {p.relative_to(paths.docs).as_posix() for p in paths.docs.rglob("*") if p.is_file()}
    extras = sorted(actual_docs - expected_docs)
    if extras:
        raise ValueError("Workspace creation unexpectedly scaffolded project documents: " + ", ".join(extras))


def _zip_tree(source: Path, archive: Path) -> None:
    files = [p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    members = sorted((p.relative_to(source).as_posix(), p) for p in files)
    temp_archive = archive.with_suffix(archive.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temp_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as zf:
            for name, path in members:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.flag_bits |= 0x800
                zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temp_archive, archive)
    finally:
        if temp_archive.exists():
            temp_archive.unlink()


def build_workspace(paths: SourcePaths, run_tests: bool = True) -> int:
    version = paths.version.read_text(encoding="utf-8").strip()
    print(f"Building Project Blueprint workspace package {version}")
    ok, issues = verify_source(paths, run_tests=run_tests)
    if not ok:
        for issue in issues:
            print(f"ERROR: {issue}")
        print("Build stopped: source verification failed.")
        return 1

    dist = paths.dist
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / f"project-blueprint-workspace-{version}.zip"
    try:
        with tempfile.TemporaryDirectory(prefix=".bp-build-", dir=str(dist)) as temp:
            temp_root = Path(temp)
            assembled = temp_root / "package"
            _assemble(paths, assembled, version)
            with tempfile.TemporaryDirectory(prefix=".bp-build-verify-") as verify_temp:
                validation_root = Path(verify_temp) / "workspace"
                _materialize_validation_copy(assembled, validation_root)
                _check_generated_workspace(validation_root)
            candidate_archive = temp_root / archive.name
            _zip_tree(assembled, candidate_archive)
            # Independently verify and extract the exact candidate ZIP that
            # will be consumed by `new`, then run workspace checks again.
            # Do not touch an older valid dist artifact until this succeeds.
            from .package import inspect_package, safe_extract_package
            inspection = inspect_package(candidate_archive, expected_version=version)
            with tempfile.TemporaryDirectory(prefix=".bp-build-extract-") as extract_temp:
                extracted = Path(extract_temp) / "package"
                safe_extract_package(inspection, extracted)
                with tempfile.TemporaryDirectory(prefix=".bp-build-verify-zip-") as verify_temp:
                    validation_root = Path(verify_temp) / "workspace"
                    _materialize_validation_copy(extracted, validation_root)
                    _check_generated_workspace(validation_root)
            digest = hashlib.sha256(candidate_archive.read_bytes()).hexdigest()
            sums = dist / "SHA256SUMS"
            candidate_sums = temp_root / "SHA256SUMS"
            candidate_sums.write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")

            # Publishing two related files cannot be one portable filesystem
            # transaction. Back up existing outputs and roll them back if the
            # checksum replacement fails after the verified archive is moved.
            previous_archive = temp_root / "previous-workspace.zip"
            previous_sums = temp_root / "previous-SHA256SUMS"
            had_archive = archive.is_file()
            had_sums = sums.is_file()
            if had_archive:
                shutil.copy2(archive, previous_archive)
            if had_sums:
                shutil.copy2(sums, previous_sums)

            os.replace(candidate_archive, archive)
            try:
                os.replace(candidate_sums, sums)
            except Exception:
                rollback_errors = []
                try:
                    if had_archive:
                        os.replace(previous_archive, archive)
                    elif archive.exists():
                        archive.unlink()
                except OSError as rollback_exc:
                    rollback_errors.append(f"workspace archive rollback failed: {rollback_exc}")
                try:
                    if had_sums:
                        os.replace(previous_sums, sums)
                    elif sums.exists():
                        sums.unlink()
                except OSError as rollback_exc:
                    rollback_errors.append(f"checksum rollback failed: {rollback_exc}")
                if rollback_errors:
                    raise RuntimeError("checksum publication failed and output rollback was incomplete: " + "; ".join(rollback_errors))
                raise

        print(f"Workspace package built and freshly verified: {archive}")
        print(f"Files: {inspection.file_count} | Uncompressed bytes: {inspection.total_size}")
        print(f"SHA-256: {digest}")
        print(f"Checksum file: {sums}")
        return 0
    except Exception as exc:
        print(f"ERROR: workspace build failed: {exc}")
        # The published archive is never deleted on a failed candidate build;
        # replacement occurs only after full fresh-extraction verification.
        return 1
