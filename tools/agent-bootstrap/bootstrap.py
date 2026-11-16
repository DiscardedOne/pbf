#!/usr/bin/env python3
"""Safely materialize a PBF v3.0.0 workspace from the agent package.

This helper performs mechanical setup only. The calling agent must obtain the
owner's explicit approval for the exact destination before invoking it.
"""
from __future__ import annotations

import argparse
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
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_PACKAGE = "PBF-Agent-Package"
MAX_ARCHIVE_MEMBERS = 10_000
MAX_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024
MAX_MEMBER_SIZE = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 500


class BootstrapError(RuntimeError):
    """Expected, user-actionable bootstrap failure with observed setup state."""

    def __init__(self, message: str, *, destination_created: bool = False):
        super().__init__(message)
        self.destination_created = destination_created


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(raw: str) -> Path:
    """Validate a package/checksum path before filesystem use."""
    if not raw or "\x00" in raw or "\\" in raw:
        raise BootstrapError(f"Unsafe package path: {raw!r}")
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise BootstrapError(f"Unsafe package path: {raw!r}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise BootstrapError(f"Unsafe package path: {raw!r}")
    if pure.parts and re.match(r"^[A-Za-z]:", pure.parts[0]):
        raise BootstrapError(f"Drive-qualified package path is not allowed: {raw!r}")
    invalid_windows = set('<>:"|?*')
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in pure.parts:
        stem = part.split(".", 1)[0].upper()
        if any(ord(char) < 32 or char in invalid_windows for char in part):
            raise BootstrapError(f"Path component is not portable to Windows: {raw!r}")
        if part.endswith((".", " ")) or stem in reserved:
            raise BootstrapError(f"Reserved or ambiguous Windows path component: {raw!r}")
    return Path(*pure.parts)


def load_and_verify_package(package_root: Path) -> dict[str, Any]:
    """Validate the exact agent package, its checksum inventory and manifest claims."""
    package_root = package_root.resolve(strict=True)
    manifest_path = package_root / "PACKAGE-MANIFEST.json"
    sums_path = package_root / "SHA256SUMS.txt"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise BootstrapError("Package root must contain PACKAGE-MANIFEST.json and SHA256SUMS.txt.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"Cannot read package manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BootstrapError("Package manifest must be a JSON object.")
    if manifest.get("package_id") != EXPECTED_PACKAGE:
        raise BootstrapError("Unexpected package identity; refusing to continue.")
    if isinstance(manifest.get("package_schema_version"), bool) or manifest.get("package_schema_version") != 1:
        raise BootstrapError("Unsupported package_schema_version; expected integer 1.")
    if manifest.get("license") != "Apache-2.0" or manifest.get("license_file") != "LICENSE":
        raise BootstrapError("Package manifest must declare Apache-2.0 and the root LICENSE file.")

    version = manifest.get("framework_version")
    if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version):
        raise BootstrapError("Package manifest contains an invalid framework_version.")
    architecture = manifest.get("workspace_architecture")
    if not isinstance(architecture, str) or not re.fullmatch(r"\d+\.\d+\.\d+", architecture):
        raise BootstrapError("Package manifest contains an invalid workspace_architecture.")

    runtime_name = f"archives/project-blueprint-framework-{version}-bootstrap-runtime.zip"
    workspace_name = f"archives/project-blueprint-workspace-{version}.zip"
    expected_names = {
        "LICENSE", "AGENT-OPERATING-INSTRUCTIONS.md", "AGENT-STARTUP-PROMPT.md",
        "PACKAGE-MANIFEST.json", runtime_name, workspace_name, "tools/bootstrap.py",
    }
    if manifest.get("bootstrap_runtime_archive") != runtime_name:
        raise BootstrapError("Unexpected bootstrap runtime archive path in manifest.")
    if manifest.get("workspace_archive") != workspace_name:
        raise BootstrapError("Unexpected workspace archive path in manifest.")

    checksums: dict[str, str] = {}
    try:
        lines = sums_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise BootstrapError(f"Cannot read package checksums: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise BootstrapError(f"Malformed checksum line {number}.")
        digest, raw_path = match.groups()
        safe_relative_path(raw_path)
        if raw_path in checksums:
            raise BootstrapError(f"Duplicate checksum entry: {raw_path}")
        checksums[raw_path] = digest

    actual_files: set[str] = set()
    for path in package_root.rglob("*"):
        if path.is_symlink():
            raise BootstrapError(f"Symbolic links are not allowed in the package: {path}")
        if path.is_file() and path != sums_path:
            actual_files.add(path.relative_to(package_root).as_posix())
    if actual_files != set(checksums):
        missing = sorted(actual_files - set(checksums))
        extra = sorted(set(checksums) - actual_files)
        raise BootstrapError(f"Checksum inventory mismatch. Unlisted files: {missing}; missing files: {extra}.")
    if actual_files != expected_names:
        missing = sorted(expected_names - actual_files)
        unexpected = sorted(actual_files - expected_names)
        raise BootstrapError(f"Unexpected agent package file inventory. Missing: {missing}; unexpected: {unexpected}.")

    for relative, expected_digest in checksums.items():
        candidate = package_root / safe_relative_path(relative)
        if not candidate.is_file() or candidate.is_symlink():
            raise BootstrapError(f"Checksum target is not a regular file: {relative}")
        actual_digest = sha256_file(candidate)
        if actual_digest != expected_digest:
            raise BootstrapError(f"SHA-256 mismatch for {relative}.")

    # The manifest's archive claims must agree with the checksum inventory,
    # not merely be covered by the checksum of the manifest file itself.
    license_path = package_root / "LICENSE"
    try:
        license_prefix = license_path.read_bytes()[:512]
    except OSError as exc:
        raise BootstrapError(f"Cannot read package LICENSE: {exc}") from exc
    if b"Apache License" not in license_prefix or b"Version 2.0, January 2004" not in license_prefix:
        raise BootstrapError("Agent package LICENSE is not the expected Apache-2.0 text.")

    for field, archive_name in (("bootstrap_runtime_sha256", runtime_name), ("workspace_archive_sha256", workspace_name)):
        declared = manifest.get(field)
        if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
            raise BootstrapError(f"Package manifest has an invalid {field}.")
        if declared != checksums.get(archive_name):
            raise BootstrapError(f"Package manifest {field} does not match SHA256SUMS.txt for {archive_name}.")
    return manifest


def inspect_zip(archive_path: Path) -> list[zipfile.ZipInfo]:
    """Reject traversal, links, ambiguous path components, encryption and ZIP bombs."""
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_MEMBERS:
                raise BootstrapError(f"Unexpected member count in {archive_path.name}.")
            seen_members: set[tuple[str, ...]] = set()
            component_spellings: dict[tuple[tuple[str, ...], str], str] = {}
            node_types: dict[tuple[str, ...], str] = {}
            explicit_directories: set[tuple[str, ...]] = set()
            total_size = 0
            for info in infos:
                raw = info.filename
                is_dir = info.is_dir()
                normalized = raw[:-1] if is_dir and raw.endswith("/") else raw
                relative = safe_relative_path(normalized)
                parts = relative.parts
                folded_parts = tuple(unicodedata.normalize("NFKC", part).casefold() for part in parts)
                if folded_parts in seen_members:
                    raise BootstrapError(f"Duplicate or case/Unicode-colliding ZIP member: {raw}")
                seen_members.add(folded_parts)

                # Check every path component in its parent scope. This catches
                # A/x and a/y, which full-path comparisons alone miss.
                for index, part in enumerate(parts):
                    parent_key = folded_parts[:index]
                    component_key = (parent_key, folded_parts[index])
                    previous = component_spellings.get(component_key)
                    if previous is not None and previous != part:
                        raise BootstrapError(
                            f"Case/Unicode-normalization collision in ZIP path component: {previous!r} and {part!r}"
                        )
                    component_spellings[component_key] = part

                    prefix = folded_parts[:index + 1]
                    if index < len(parts) - 1:
                        if node_types.get(prefix) == "file":
                            raise BootstrapError(f"ZIP path descends through a file member: {raw}")
                        node_types.setdefault(prefix, "dir")

                full_key = folded_parts
                current_type = "dir" if is_dir else "file"
                previous_type = node_types.get(full_key)
                if previous_type is not None and previous_type != current_type:
                    raise BootstrapError(f"ZIP file/directory path conflict: {raw}")
                if is_dir:
                    if full_key in explicit_directories:
                        raise BootstrapError(f"Duplicate ZIP directory member: {raw}")
                    explicit_directories.add(full_key)
                elif previous_type == "dir":
                    raise BootstrapError(f"ZIP file conflicts with an existing directory path: {raw}")
                node_types[full_key] = current_type

                if info.flag_bits & 0x1:
                    raise BootstrapError(f"Encrypted ZIP members are not supported: {raw}")
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise BootstrapError(f"Symbolic link ZIP member is not allowed: {raw}")
                if not is_dir:
                    if info.file_size > MAX_MEMBER_SIZE:
                        raise BootstrapError(f"ZIP member exceeds size limit: {raw}")
                    total_size += info.file_size
                    if total_size > MAX_TOTAL_UNCOMPRESSED:
                        raise BootstrapError("ZIP archive exceeds the total uncompressed-size limit.")
                    if info.file_size and info.compress_size == 0:
                        raise BootstrapError(f"Invalid compressed size for ZIP member: {raw}")
                    if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                        raise BootstrapError(f"Suspicious compression ratio for ZIP member: {raw}")
            return infos
    except zipfile.BadZipFile as exc:
        raise BootstrapError(f"Invalid ZIP archive: {archive_path.name}") from exc


def safe_extract(archive_path: Path, destination: Path) -> None:
    infos = inspect_zip(archive_path)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in infos:
                raw = info.filename
                is_dir = info.is_dir()
                normalized = raw[:-1] if is_dir and raw.endswith("/") else raw
                relative = safe_relative_path(normalized)
                target = destination.joinpath(*relative.parts)
                resolved_parent = target.parent.resolve(strict=False)
                if destination.resolve() not in (resolved_parent, *resolved_parent.parents):
                    raise BootstrapError(f"ZIP member escapes extraction directory: {raw}")
                if is_dir:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
    except Exception:
        # This destination was just created with exist_ok=False, so its
        # contents are owned by this extraction attempt.
        shutil.rmtree(destination, ignore_errors=True)
        raise


def run_command(args: list[str], cwd: Path, label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    print("$ " + " ".join(args), flush=True)
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n", flush=True)
    if completed.returncode != 0:
        raise BootstrapError(f"{label} failed with exit code {completed.returncode}.")


def bootstrap(package_root: Path, project_name: str, destination: Path, approved_destination: Path) -> dict[str, Any]:
    package_root = package_root.resolve(strict=True)
    if not project_name.strip():
        raise BootstrapError("Project name must not be empty.")

    destination_requested = destination.expanduser().absolute()
    approved_requested = approved_destination.expanduser().absolute()
    if os.path.normcase(os.path.normpath(str(destination_requested))) != os.path.normcase(os.path.normpath(str(approved_requested))):
        raise BootstrapError("The approved destination does not exactly match --destination. No files were created.")

    parent = destination_requested.parent
    if not parent.exists() or not parent.is_dir():
        raise BootstrapError("The destination's parent directory must already exist. No parent directories were created.")
    destination_resolved = destination_requested.resolve(strict=False)
    if destination_requested.exists() or destination_requested.is_symlink():
        raise BootstrapError("Destination already exists; refusing to overwrite or merge it.")
    if package_root == destination_resolved or package_root in destination_resolved.parents:
        raise BootstrapError("Destination cannot be inside the extracted agent package.")
    if not os.access(parent, os.W_OK):
        raise BootstrapError("The destination's parent directory is not writable by this process.")

    manifest = load_and_verify_package(package_root)
    runtime_zip = package_root / manifest["bootstrap_runtime_archive"]
    workspace_zip = package_root / manifest["workspace_archive"]
    inspect_zip(runtime_zip)
    inspect_zip(workspace_zip)

    checks: list[str] = []
    destination_created = False
    temporary_root = None
    source_root = None
    try:
        with tempfile.TemporaryDirectory(prefix="pbf-bootstrap-") as temporary:
            temporary_root = Path(temporary)
            source_root = temporary_root / "runtime"
            safe_extract(runtime_zip, source_root)
            if not (source_root / "bp.py").is_file() or not (source_root / "src/blueprint_framework/source_cli.py").is_file():
                raise BootstrapError("The bootstrap runtime archive does not have the expected PBF runtime layout.")
            if not (source_root / "_framework/tools/workspace_paths.py").is_file():
                raise BootstrapError("The bootstrap runtime archive is missing the workspace runtime.")
            checks.append("bootstrap runtime safely extracted to a temporary directory")

            run_command([sys.executable, "-B", "bp.py", "verify", "--scope", "bootstrap"], source_root, "Bootstrap runtime verification")
            runtime_version = (source_root / "VERSION").read_text(encoding="utf-8").strip()
            if runtime_version != manifest["framework_version"]:
                raise BootstrapError("Bootstrap runtime VERSION does not match PACKAGE-MANIFEST.json.")
            checks.append("bootstrap runtime verification passed")

            run_command(
                [sys.executable, "-B", "bp.py", "new", "--name", project_name,
                 "--destination", str(destination_requested), "--package", str(workspace_zip)],
                source_root,
                "Workspace creation",
            )
            destination_created = destination_requested.is_dir()
            if not destination_created:
                raise BootstrapError("The source CLI returned success but the destination directory is absent.")
            checks.append("workspace creation completed")

            run_command([sys.executable, "-B", "bp.py", "check", "--strict"], destination_requested, "Workspace strict validation")
            checks.append("workspace check --strict passed")
            run_command([sys.executable, "-B", "bp.py", "index", "--check"], destination_requested, "Workspace index validation")
            checks.append("workspace index --check passed")
            run_command([sys.executable, "-B", "bp.py", "audit-state", "--strict"], destination_requested, "Workspace state audit")
            checks.append("workspace audit-state --strict passed")
    except Exception as exc:
        # The destination was confirmed absent before this operation. Its current
        # presence after a failure is therefore the observable partial-setup state.
        created_now = destination_requested.is_dir()
        try:
            setattr(exc, "destination_created", created_now)
        except Exception:
            pass
        raise

    temporary_runtime_removed = (
        temporary_root is not None
        and source_root is not None
        and not temporary_root.exists()
        and not source_root.exists()
    )
    if not temporary_runtime_removed:
        raise BootstrapError(
            "Temporary runtime extraction still exists after cleanup.",
            destination_created=destination_requested.is_dir(),
        )

    result = {
        "status": "verified",
        "framework_version": manifest["framework_version"],
        "workspace_architecture": manifest["workspace_architecture"],
        "project_name": project_name,
        "destination": str(destination_requested),
        "checks": checks,
        "temporary_runtime_removed": temporary_runtime_removed,
        "git_initialized": False,
    }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and verify a Project Blueprint Framework workspace.")
    parser.add_argument("--package-root", required=True, type=Path, help="Extracted root of PBF-Agent-Package")
    parser.add_argument("--name", required=True, help="Project display name")
    parser.add_argument("--destination", required=True, type=Path, help="Exact new workspace destination")
    parser.add_argument(
        "--approved-destination", required=True, type=Path,
        help="Repeat the exact destination confirmed by the owner; acts as an invocation guard, not proof of consent",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = None
    try:
        args = parse_args(argv)
        result = bootstrap(args.package_root, args.name, args.destination, args.approved_destination)
        print("\nPBF_BOOTSTRAP_RESULT=" + json.dumps(result, sort_keys=True), flush=True)
        print("\nPBF workspace setup completed and verified. Temporary runtime files were removed.", flush=True)
        return 0
    except BootstrapError as exc:
        print(f"PBF bootstrap blocked/failed: {exc}", file=sys.stderr, flush=True)
        print("No pre-existing destination was overwritten.", file=sys.stderr, flush=True)
        if getattr(exc, "destination_created", False) and args is not None and args.destination.is_dir():
            print(f"A workspace was created before a later setup/verification failure and was preserved at: {args.destination}", file=sys.stderr, flush=True)
        else:
            print("No workspace destination was created by this attempt.", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # defensive boundary: never print a false success
        print(f"PBF bootstrap failed unexpectedly: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        if args is not None and getattr(exc, "destination_created", False) and args.destination.is_dir():
            print(f"A workspace was created before the unexpected failure and was preserved at: {args.destination}", file=sys.stderr, flush=True)
        else:
            print("No workspace destination was created by this attempt.", file=sys.stderr, flush=True)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
