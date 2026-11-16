"""Create disposable layout-v1 workspaces for architecture/runtime tests."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    raw = path.read_bytes()
    if path.suffix.lower() in {".md", ".py", ".json", ".jsonl", ".txt", ".yaml", ".yml"}:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def create_workspace(source_root: Path, destination: Path, project_name: str = "Test Project", *, preserve_onboarding: bool = False) -> Path:
    """Create a test workspace by applying starter seeds to the canonical runtime."""
    source_root = source_root.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("test destination must be empty")

    shutil.copytree(source_root / "starter", destination, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(source_root / "_framework", destination / "_framework", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(source_root / "bp.py", destination / "bp.py")
    for name in (".gitignore", ".gitattributes"):
        shutil.copy2(source_root / name, destination / name)

    marker_template = destination / "_control" / "WORKSPACE.json.template"
    config = json.loads(marker_template.read_text(encoding="utf-8"))
    config["project"]["name"] = project_name
    marker = marker_template.with_name("WORKSPACE.json")
    marker.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    marker_template.unlink()

    readme_template = destination / "README.md.template"
    if readme_template.exists():
        readme_template.rename(destination / "README.md")
    if preserve_onboarding:
        readme = (destination / "README.md").read_text(encoding="utf-8")
        (destination / "README.md").write_text(
            readme.replace("{{PROJECT_NAME}}", project_name),
            encoding="utf-8", newline="\n")
    else:
        # Compact fixture onboarding keeps the general path/runtime tests small.
        (destination / "README.md").write_text(
            f"# {project_name}\n\nDocumentation workspace for {project_name}.\n",
            encoding="utf-8", newline="\n")
        (destination / "AGENTS.md").write_text(
            "# Project Blueprint Agent Instructions\n\nFollow the framework operating contract.\n",
            encoding="utf-8", newline="\n")

    files = {}
    for path in sorted((destination / "_framework").rglob("*")):
        if path.is_file() and path.name != "FRAMEWORK-MANIFEST.json":
            files[path.relative_to(destination).as_posix()] = _sha256(path)
    for path in (destination / "bp.py", destination / "AGENTS.md"):
        files[path.relative_to(destination).as_posix()] = _sha256(path)
    files = dict(sorted(files.items()))
    version = (source_root / "VERSION").read_text(encoding="utf-8").strip()
    framework_manifest = {
        "manifest_schema_version": 1,
        "framework_version": version,
        "workspace_schema_versions_supported": [1],
        "layout_versions_supported": [1],
        "hash_algorithm": "sha256",
        "text_hash_policy": "utf8-lf-normalized-v1",
        "files": files,
    }
    (destination / "_framework" / "FRAMEWORK-MANIFEST.json").write_text(
        json.dumps(framework_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return destination
