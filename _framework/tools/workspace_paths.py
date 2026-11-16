"""Canonical, layout-versioned path discovery for Project Blueprint Framework.

The module is deliberately standard-library-only and contains no framework or
agent-harness behavior. Workspace layout v1 is fixed; WORKSPACE.json cannot
redirect framework writes through arbitrary path values.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
import re
from pathlib import Path, PureWindowsPath
import unicodedata
from typing import Iterable, Optional, Tuple, Union

WORKSPACE_MARKER = Path("_control") / "WORKSPACE.json"
SOURCE_MARKER = Path("framework-dev") / "SOURCE-MANIFEST.json"
SUPPORTED_WORKSPACE_SCHEMA = {1}
SUPPORTED_LAYOUTS = {1}


class WorkspaceDiscoveryError(RuntimeError):
    """Raised when no unambiguous valid framework context can be discovered."""


def _contained(root: Path, candidate: Path, label: str) -> Path:
    """Resolve a fixed path and reject symlink/path escapes from root."""
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError(f"Configured {label} resolves outside the workspace root: {candidate}")
    return candidate_resolved


def _read_json(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkspaceDiscoveryError(f"Cannot read {label} at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkspaceDiscoveryError(f"{label} must contain a JSON object: {path}")
    return data



TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".txt",
    ".csv", ".xml", ".svg", ".html", ".htm", ".css", ".js", ".ts",
    ".sh", ".ps1", ".bat", ".cmd", ".ini", ".cfg", ".conf", ".properties",
}
FRAMEWORK_MANIFEST_SCHEMA = 1
SOURCE_SCHEMA_VERSION = 1
SOURCE_LAYOUT_VERSION = 1

def normalized_file_sha256(path: Path) -> str:
    """Hash managed text as UTF-8/LF; hash binary files byte-for-byte."""
    raw = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"AGENTS.md", "bp.py", ".gitattributes", ".gitignore"}:
        # Strict UTF-8 decode prevents arbitrary binary data being silently normalized.
        text = raw.decode("utf-8")
        canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        raw = canonical
    return hashlib.sha256(raw).hexdigest()

def validate_framework_manifest(paths: "WorkspacePaths") -> list[tuple[str, str]]:
    """Return (severity, message) pairs for installed framework-manifest drift."""
    issues: list[tuple[str, str]] = []
    manifest_path = paths.framework_manifest
    try:
        manifest = _read_json(manifest_path, "framework integrity manifest")
    except WorkspaceDiscoveryError as exc:
        return [("error", str(exc))]

    if manifest.get("manifest_schema_version") != FRAMEWORK_MANIFEST_SCHEMA:
        return [("error", f"Unsupported framework manifest schema: {manifest.get('manifest_schema_version')!r}")]
    version = manifest.get("framework_version")
    if not isinstance(version, str) or not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version
    ):
        issues.append(("error", f"Framework manifest contains an invalid framework_version: {version!r}"))
    if manifest.get("hash_algorithm") != "sha256":
        issues.append(("error", f"Unsupported framework manifest hash_algorithm: {manifest.get('hash_algorithm')!r}"))
    if manifest.get("text_hash_policy") != "utf8-lf-normalized-v1":
        issues.append(("error", f"Unsupported framework manifest text_hash_policy: {manifest.get('text_hash_policy')!r}"))
    schema_versions = manifest.get("workspace_schema_versions_supported")
    layout_versions = manifest.get("layout_versions_supported")
    if not isinstance(schema_versions, list) or paths.workspace_schema_version not in schema_versions:
        issues.append(("error", "Framework manifest does not declare support for this workspace schema version"))
    if not isinstance(layout_versions, list) or paths.layout_version not in layout_versions:
        issues.append(("error", "Framework manifest does not declare support for this workspace layout version"))

    listed = manifest.get("files")
    if not isinstance(listed, dict):
        issues.append(("error", "Framework manifest 'files' must be an object mapping relative paths to SHA-256 digests"))
        return issues

    actual_paths: set[str] = set()
    for root in (paths.framework,):
        if root.exists():
            for item in root.rglob("*"):
                if not item.is_file() or item == manifest_path or "__pycache__" in item.parts or item.suffix == ".pyc":
                    continue
                try:
                    actual_paths.add(paths.relative(item))
                except ValueError:
                    issues.append(("error", f"Framework file escapes workspace root: {item}"))
    for item in (paths.agent_instructions, paths.launcher):
        if item.is_file():
            actual_paths.add(paths.relative(item))

    listed_paths = set(listed)
    if list(listed.keys()) != sorted(listed.keys()):
        issues.append(("error", "Framework manifest file entries must be sorted by relative path"))
    if paths.relative(manifest_path) in listed_paths:
        issues.append(("error", "Framework manifest must not include itself in its managed-file hashes"))
    for relative in sorted(listed_paths):
        if not isinstance(relative, str) or not relative or "\\" in relative:
            issues.append(("error", f"Invalid framework manifest path: {relative!r}"))
            continue
        pure = Path(relative)
        windows = PureWindowsPath(relative)
        if pure.is_absolute() or windows.is_absolute() or windows.drive or any(part in ("", ".", "..") for part in pure.parts):
            issues.append(("error", f"Unsafe framework manifest path: {relative!r}"))
            continue
        if relative not in {"AGENTS.md", "bp.py"} and not relative.startswith("_framework/"):
            issues.append(("error", f"Manifest path is not framework-managed: {relative!r}"))
            continue
        candidate = (paths.root / pure).resolve(strict=False)
        if candidate != paths.root and paths.root not in candidate.parents:
            issues.append(("error", f"Framework manifest path escapes workspace: {relative!r}"))
            continue
        if relative not in actual_paths or not candidate.is_file():
            issues.append(("warning", f"Framework-managed file is missing: {relative}"))
            continue
        expected = listed[relative]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            issues.append(("error", f"Invalid SHA-256 digest for framework-managed file: {relative}"))
            continue
        try:
            actual = normalized_file_sha256(candidate)
        except (OSError, UnicodeError) as exc:
            issues.append(("warning", f"Cannot hash framework-managed file {relative}: {exc}"))
            continue
        if actual != expected:
            issues.append(("warning", f"Framework-managed file drift: {relative} (expected {expected}, actual {actual})"))
    for relative in sorted(actual_paths - listed_paths):
        issues.append(("warning", f"Untracked file in framework-managed area: {relative}"))
    return issues


def validate_gitattributes(paths: "WorkspacePaths") -> list[tuple[str, str]]:
    """Check the project's required LF and binary Git attributes; warnings only."""
    issues: list[tuple[str, str]] = []
    file = paths.gitattributes
    if not file.is_file():
        return [("warning", ".gitattributes is missing; required UTF-8/LF rules cannot be verified")]
    lines = []
    try:
        lines = [line.strip() for line in file.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()]
    except (OSError, UnicodeError) as exc:
        return [("warning", f"Cannot read .gitattributes: {exc}")]
    active = [line for line in lines if line and not line.startswith("#")]
    required_lf = ("*.md", "*.template", "*.py", "*.json", "*.jsonl", "*.toml", "*.yaml", "*.yml", "*.txt", "*.csv", "*.xml", "*.svg")
    for pattern in required_lf:
        if not any(line.split()[0] == pattern and "text" in line.split()[1:] and "eol=lf" in line.split()[1:] for line in active if len(line.split()) >= 3):
            issues.append(("warning", f".gitattributes is missing required LF rule: {pattern} text eol=lf"))
    required_binary = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.pdf", "*.zip")
    for pattern in required_binary:
        if not any(line.split()[0] == pattern and "binary" in line.split()[1:] for line in active if len(line.split()) >= 2):
            issues.append(("warning", f".gitattributes is missing binary rule: {pattern} binary"))
    return issues


def validate_workspace_structure(paths: "WorkspacePaths", defaults: dict) -> list[tuple[str, str]]:
    """Validate required files/directories from hash-tracked framework defaults."""
    issues: list[tuple[str, str]] = []
    structure = defaults.get("workspace_structure")
    if not isinstance(structure, dict):
        return [("error", "Framework defaults require a workspace_structure object")]
    for key, expected_type in (("required_files", list), ("required_directories", list), ("optional_directories", list)):
        if not isinstance(structure.get(key), expected_type):
            issues.append(("error", f"Framework defaults workspace_structure.{key} must be a list"))
    if issues:
        return issues
    root = paths.root.resolve()
    for category, expected in (("required file", "file"), ("required directory", "directory")):
        key = "required_files" if expected == "file" else "required_directories"
        for relative in structure[key]:
            if not isinstance(relative, str) or not relative or "\\" in relative:
                issues.append(("error", f"Invalid {category} path in framework defaults: {relative!r}"))
                continue
            pure = Path(relative)
            windows = PureWindowsPath(relative)
            if pure.is_absolute() or windows.is_absolute() or windows.drive or any(part in ("", ".", "..") for part in pure.parts):
                issues.append(("error", f"Unsafe {category} path in framework defaults: {relative!r}"))
                continue
            candidate = (root / pure).resolve(strict=False)
            if candidate != root and root not in candidate.parents:
                issues.append(("error", f"{category.title()} path escapes workspace through a symlink: {relative}"))
                continue
            ok = candidate.is_file() if expected == "file" else candidate.is_dir()
            if not ok:
                issues.append(("error", f"Required workspace {expected} is missing: {relative}"))
    for relative in structure["optional_directories"]:
        if not isinstance(relative, str) or not relative or "\\" in relative:
            issues.append(("error", f"Invalid optional directory path in framework defaults: {relative!r}"))
            continue
        pure = Path(relative)
        windows = PureWindowsPath(relative)
        if pure.is_absolute() or windows.is_absolute() or windows.drive or any(part in ("", ".", "..") for part in pure.parts):
            issues.append(("error", f"Unsafe optional directory path in framework defaults: {relative!r}"))
            continue
        candidate = (root / pure).resolve(strict=False)
        if candidate != root and root not in candidate.parents:
            issues.append(("error", f"Optional directory path escapes workspace through a symlink: {relative}"))
        elif candidate.exists() and not candidate.is_dir():
            issues.append(("error", f"Optional workspace directory path is not a directory: {relative}"))
    return issues


@dataclass(frozen=True)
class WorkspacePaths:
    """Immutable fixed-path map for one v1 project workspace."""
    root: Path
    launcher: Path
    readme: Path
    agent_instructions: Path
    gitignore: Path
    gitattributes: Path
    docs: Path
    docs_readme: Path
    framework: Path
    framework_manifest: Path
    framework_tools: Path
    catalog: Path
    templates: Path
    defaults: Path
    defaults_policy: Path
    workspace_config: Path
    control: Path
    phases: Path
    state: Path
    project_rules: Path
    registry: Path
    manifest: Path
    index: Path
    approvals: Path
    decisions: Path
    assumptions: Path
    questions: Path
    risks: Path
    glossary: Path
    registry_changelog: Path
    logs: Path
    sessions: Path
    interviews: Path
    phase_reports: Path
    overrides: Path
    status_transitions: Path
    assets: Path
    images: Path
    diagrams: Path
    attachments: Path
    specs: Path
    adr: Path
    workspace_schema_version: int
    layout_version: int
    project_name: str

    @classmethod
    def from_root(cls, root: Union[str, Path]) -> "WorkspacePaths":
        root = Path(root).resolve()
        marker = root / WORKSPACE_MARKER
        if not marker.is_file():
            raise WorkspaceDiscoveryError(f"Live workspace marker not found: {marker}")
        marker = _contained(root, marker, "workspace marker")
        config = _read_json(marker, "workspace configuration")
        if "paths" in config:
            raise WorkspaceDiscoveryError(
                "WORKSPACE.json must not define arbitrary paths; layout v1 paths are fixed by the framework"
            )
        if "framework_version" in config:
            raise WorkspaceDiscoveryError(
                "WORKSPACE.json must not duplicate framework_version; _framework/FRAMEWORK-MANIFEST.json owns it"
            )
        allowed_keys = {"workspace_schema_version", "layout_version", "project", "profile"}
        unknown_keys = sorted(set(config) - allowed_keys)
        if unknown_keys:
            raise WorkspaceDiscoveryError(
                "WORKSPACE.json contains unsupported or framework-owned setting(s): " + ", ".join(unknown_keys)
            )
        schema_version = config.get("workspace_schema_version")
        layout_version = config.get("layout_version")
        if isinstance(schema_version, bool) or schema_version not in SUPPORTED_WORKSPACE_SCHEMA:
            raise WorkspaceDiscoveryError(f"Unsupported workspace_schema_version: {schema_version!r}")
        if isinstance(layout_version, bool) or layout_version not in SUPPORTED_LAYOUTS:
            raise WorkspaceDiscoveryError(f"Unsupported layout_version: {layout_version!r}")
        project = config.get("project")
        if not isinstance(project, dict) or not isinstance(project.get("name"), str) or not project["name"].strip():
            raise WorkspaceDiscoveryError("WORKSPACE.json requires a non-empty project.name")

        # Fixed layout-v1 path map. Every value is rooted and containment-checked.
        rel = {
            "launcher": "bp.py",
            "readme": "README.md",
            "agent_instructions": "AGENTS.md",
            "gitignore": ".gitignore",
            "gitattributes": ".gitattributes",
            "docs": "docs",
            "docs_readme": "docs/README.md",
            "framework": "_framework",
            "framework_manifest": "_framework/FRAMEWORK-MANIFEST.json",
            "framework_tools": "_framework/tools",
            "catalog": "_framework/DOC-CATALOG.md",
            "templates": "_framework/templates",
            "defaults": "_framework/defaults/workspace-defaults.json",
            "defaults_policy": "_framework/defaults/workspace-policy-defaults.md",
            "workspace_config": "_control/WORKSPACE.json",
            "control": "_control",
            "phases": "_control/PHASES.md",
            "state": "_control/STATE.md",
            "project_rules": "_control/PROJECT-RULES.md",
            "registry": "_control/registry",
            "manifest": "_control/registry/MANIFEST.md",
            "index": "_control/registry/INDEX.md",
            "approvals": "_control/registry/APPROVALS.md",
            "decisions": "_control/registry/DECISIONS.md",
            "assumptions": "_control/registry/ASSUMPTIONS.md",
            "questions": "_control/registry/QUESTIONS.md",
            "risks": "_control/registry/RISKS.md",
            "glossary": "_control/registry/GLOSSARY.md",
            "registry_changelog": "_control/registry/CHANGELOG.md",
            "logs": "_control/logs",
            "sessions": "_control/logs/sessions",
            "interviews": "_control/logs/interviews",
            "phase_reports": "_control/logs/phase-reports",
            "overrides": "_control/logs/overrides",
            "status_transitions": "_control/logs/status-transitions.jsonl",
            "assets": "docs/_assets",
            "images": "docs/_assets/images",
            "diagrams": "docs/_assets/diagrams",
            "attachments": "docs/_assets/attachments",
            "specs": "docs/_assets/specs",
            "adr": "docs/04-architecture/adr",
        }
        resolved = {name: _contained(root, root / value, name) for name, value in rel.items()}
        return cls(
            root=root,
            workspace_schema_version=int(schema_version),
            layout_version=int(layout_version),
            project_name=project["name"].strip(),
            **resolved,
        )

    def relative(self, path: Union[str, Path]) -> str:
        """Return a stable workspace-relative POSIX path for diagnostics and links."""
        candidate = Path(path).resolve(strict=False)
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"Path is outside the workspace: {path}")
        return candidate.relative_to(self.root).as_posix()

    def resolve_document(self, relative_posix: str) -> Optional[Path]:
        """Resolve a catalog document path safely inside docs/."""
        if not isinstance(relative_posix, str) or not relative_posix or "\\" in relative_posix:
            return None
        pure = Path(relative_posix)
        windows = PureWindowsPath(relative_posix)
        if pure.is_absolute() or windows.is_absolute() or windows.drive or any(part in ("", ".", "..") for part in pure.parts):
            return None
        candidate = (self.docs / pure).resolve(strict=False)
        docs_root = self.docs.resolve()
        if candidate != docs_root and docs_root not in candidate.parents:
            return None
        return candidate

    def case_collisions(self, skip_dirs: Iterable[str] = (".git", ".venv", "venv", "__pycache__", ".pytest_cache")) -> list[tuple[str, str]]:
        """Return file or directory path pairs colliding under Windows-like normalization.

        Every path prefix is checked, not only complete paths, so Foo/a.md and
        foo/b.md correctly collide on the parent directory component.
        """
        skip = set(skip_dirs)
        seen: dict[str, str] = {}
        collisions: list[tuple[str, str]] = []
        if not self.root.exists():
            return collisions
        for path in self.root.rglob("*"):
            try:
                relative = path.relative_to(self.root)
            except ValueError:
                continue
            if any(part in skip for part in relative.parts):
                continue
            if path.is_symlink() and path.is_dir():
                continue
            parts = relative.parts
            for index in range(1, len(parts) + 1):
                original = Path(*parts[:index]).as_posix()
                key = unicodedata.normalize("NFKC", original).casefold()
                previous = seen.get(key)
                if previous is not None and previous != original:
                    pair = (previous, original)
                    if pair not in collisions and (original, previous) not in collisions:
                        collisions.append(pair)
                else:
                    seen[key] = original
        return collisions


@dataclass(frozen=True)
class SourcePaths:
    """Fixed source-repository paths; source-only modules never ship to workspaces."""
    root: Path
    marker: Path
    version: Path
    launcher: Path
    source_modules: Path
    source_cli: Path
    build_module: Path
    package_module: Path
    runtime: Path
    starter: Path
    starter_workspace_seed: Path
    dist: Path
    framework_dev: Path
    tests: Path
    architecture: Path

    @classmethod
    def from_root(cls, root: Union[str, Path]) -> "SourcePaths":
        root = Path(root).resolve()
        marker = root / SOURCE_MARKER
        if not marker.is_file():
            raise WorkspaceDiscoveryError(f"Source repository marker not found: {marker}")
        marker = _contained(root, marker, "source manifest")
        source_data = _read_json(marker, "source manifest")
        source_schema = source_data.get("source_schema_version")
        source_layout = source_data.get("source_layout_version")
        if isinstance(source_schema, bool) or source_schema != SOURCE_SCHEMA_VERSION:
            raise WorkspaceDiscoveryError(f"Unsupported source_schema_version: {source_schema!r}")
        if source_data.get("source_identity") != "project-blueprint-framework":
            raise WorkspaceDiscoveryError("Source manifest has an unexpected source_identity")
        if isinstance(source_layout, bool) or source_layout != SOURCE_LAYOUT_VERSION:
            raise WorkspaceDiscoveryError(f"Unsupported source_layout_version: {source_layout!r}")
        values = {
            "version": "VERSION",
            "launcher": "bp.py",
            "source_modules": "src/blueprint_framework",
            "source_cli": "src/blueprint_framework/source_cli.py",
            "build_module": "src/blueprint_framework/build.py",
            "package_module": "src/blueprint_framework/package.py",
            "runtime": "_framework/tools/blueprint.py",
            "starter": "starter",
            "starter_workspace_seed": "starter/_control/WORKSPACE.json.template",
            "dist": "dist",
            "framework_dev": "framework-dev",
            "tests": "framework-dev/tests",
            "architecture": "framework-dev/architecture",
        }
        for name, relative in values.items():
            resolved = (root / relative).resolve(strict=False)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"Source path {relative} escapes source repository")
            values[name] = resolved
        return cls(root=root, marker=marker.resolve(), **values)


def _ancestor_candidates(start: Path) -> list[Path]:
    start = start.resolve()
    if start.is_file():
        start = start.parent
    return [start, *start.parents]


def discover_context(start: Optional[Path] = None, launcher_path: Optional[Path] = None):
    """Return ('workspace'|'source', immutable paths) using nearest valid markers.

    The launcher directory is checked first when supplied, so invoking a workspace
    launcher by absolute path cannot accidentally bind to an unrelated current cwd.
    Within each candidate, a live workspace marker is checked before a source marker.
    The starter seed name WORKSPACE.json.template is intentionally never a marker.
    """
    starts: list[Path] = []
    if launcher_path is not None:
        starts.append(Path(launcher_path).resolve().parent)
    if start is not None:
        candidate = Path(start).resolve()
        if candidate not in starts:
            starts.append(candidate)
    for base in starts:
        for directory in _ancestor_candidates(base):
            workspace_marker = directory / WORKSPACE_MARKER
            source_marker = directory / SOURCE_MARKER
            if workspace_marker.is_file():
                return "workspace", WorkspacePaths.from_root(directory)
            if source_marker.is_file():
                return "source", SourcePaths.from_root(directory)
    return None, None


def python_version_supported(version_info=None) -> bool:
    version_info = version_info or __import__("sys").version_info
    return tuple(version_info[:2]) >= (3, 11)
