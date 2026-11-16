"""Standard-library tests for the PBF agent bootstrap helper."""
from __future__ import annotations

import contextlib
import hashlib
import io
import importlib.util
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("pbf_bootstrap", SCRIPT)
bootstrap = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(bootstrap)


class BootstrapPathTests(unittest.TestCase):
    def test_accepts_nested_relative_path(self):
        self.assertEqual(bootstrap.safe_relative_path("archives/source.zip").as_posix(), "archives/source.zip")

    def test_rejects_parent_traversal(self):
        for value in ("../outside", "a/../../outside", "a/../b"):
            with self.subTest(value=value), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.safe_relative_path(value)

    def test_rejects_absolute_and_drive_paths(self):
        for value in ("/rooted", "C:/Windows/file", "C:file"):
            with self.subTest(value=value), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.safe_relative_path(value)

    def test_rejects_backslash_and_ambiguous_components(self):
        for value in (r"a\\b", "a//b", "a/./b", ""):
            with self.subTest(value=value), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.safe_relative_path(value)

    def test_rejects_windows_reserved_and_invalid_names(self):
        for value in ("folder/CON.txt", "folder/name:stream", "folder/trailing.", "folder/trailing ", "folder/bad?.txt"):
            with self.subTest(value=value), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.safe_relative_path(value)


class BootstrapArchiveTests(unittest.TestCase):
    def test_inspects_and_extracts_valid_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "valid.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("folder/file.txt", "hello")
            infos = bootstrap.inspect_zip(archive_path)
            self.assertEqual(len(infos), 1)
            destination = root / "extracted"
            bootstrap.safe_extract(archive_path, destination)
            self.assertEqual((destination / "folder/file.txt").read_text(), "hello")

    def test_rejects_zip_slip(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", "no")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.inspect_zip(archive_path)

    def test_rejects_case_colliding_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "collision.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("Docs/Readme.md", "one")
                archive.writestr("docs/readme.md", "two")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.inspect_zip(archive_path)

    def test_rejects_unicode_normalization_collisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unicode-collision.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("caf\u00e9.md", "one")
                archive.writestr("cafe\u0301.md", "two")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.inspect_zip(archive_path)

    def test_rejects_symlink_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "symlink.zip"
            info = zipfile.ZipInfo("linked")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(info, "target")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.inspect_zip(archive_path)


class BootstrapPackageTests(unittest.TestCase):
    def _create_package(self, root: Path) -> None:
        (root / "archives").mkdir()
        (root / "tools").mkdir(parents=True)
        license_text = "Apache License\nVersion 2.0, January 2004\n" + ("Canonical license test fixture.\n" * 32)
        files = {
            "LICENSE": license_text,
            "AGENT-OPERATING-INSTRUCTIONS.md": "instructions",
            "AGENT-STARTUP-PROMPT.md": "prompt",
            "archives/project-blueprint-framework-3.0.0-bootstrap-runtime.zip": "runtimezip-placeholder",
            "archives/project-blueprint-workspace-3.0.0.zip": "workspacezip-placeholder",
            "tools/bootstrap.py": SCRIPT.read_text(encoding="utf-8"),
        }
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        manifest = {
            "package_id": "PBF-Agent-Package",
            "package_schema_version": 1,
            "license": "Apache-2.0",
            "license_file": "LICENSE",
            "framework_version": "3.0.0",
            "workspace_architecture": "1.3.4",
            "bootstrap_runtime_archive": "archives/project-blueprint-framework-3.0.0-bootstrap-runtime.zip",
            "workspace_archive": "archives/project-blueprint-workspace-3.0.0.zip",
            "bootstrap_runtime_sha256": hashlib.sha256((root / "archives/project-blueprint-framework-3.0.0-bootstrap-runtime.zip").read_bytes()).hexdigest(),
            "workspace_archive_sha256": hashlib.sha256((root / "archives/project-blueprint-workspace-3.0.0.zip").read_bytes()).hexdigest(),
        }
        (root / "PACKAGE-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        checksummed = sorted([*files, "PACKAGE-MANIFEST.json"])
        lines = [f"{hashlib.sha256((root / relative).read_bytes()).hexdigest()}  {relative}" for relative in checksummed]
        (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_validates_manifest_and_checksums(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._create_package(root)
            manifest = bootstrap.load_and_verify_package(root)
            self.assertEqual(manifest["framework_version"], "3.0.0")

    def test_detects_tampered_package_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._create_package(root)
            (root / "AGENT-STARTUP-PROMPT.md").write_text("tampered", encoding="utf-8")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.load_and_verify_package(root)

    def test_bootstrap_requires_matching_approved_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            package.mkdir()
            parent = root / "destinations"
            parent.mkdir()
            destination = parent / "Project"
            other = parent / "Different"
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.bootstrap(package, "Project", destination, other)
            self.assertFalse(destination.exists())

    def test_manifest_archive_digest_must_match_checksum_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._create_package(root)
            manifest_path = root / "PACKAGE-MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["bootstrap_runtime_sha256"] = "f" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            sums_path = root / "SHA256SUMS.txt"
            lines = sums_path.read_text(encoding="utf-8").splitlines()
            updated = []
            for line in lines:
                digest, path = line.split("  ", 1)
                if path == "PACKAGE-MANIFEST.json":
                    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                updated.append(f"{digest}  {path}")
            sums_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "does not match SHA256SUMS"):
                bootstrap.load_and_verify_package(root)

    def test_rejects_parent_component_case_collisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "parent-collision.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("A/file-one.txt", "one")
                archive.writestr("a/file-two.txt", "two")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "path component"):
                bootstrap.inspect_zip(archive_path)

    def test_rejects_file_directory_ancestor_conflicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "ancestor-conflict.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("node", "file")
                archive.writestr("node/child.txt", "child")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "descends through a file"):
                bootstrap.inspect_zip(archive_path)


class BootstrapReportingTests(unittest.TestCase):
    def _arguments(self, root: Path, destination: Path) -> list[str]:
        package = root / "package"
        package.mkdir(exist_ok=True)
        return [
            "--package-root", str(package),
            "--name", "Example Project",
            "--destination", str(destination),
            "--approved-destination", str(destination),
        ]

    def test_main_reports_no_workspace_when_failure_precedes_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "destinations"
            parent.mkdir()
            destination = parent / "Project"
            stderr = io.StringIO()
            failure = bootstrap.BootstrapError("fixture failure before destination creation")
            with patch.object(bootstrap, "bootstrap", side_effect=failure), contextlib.redirect_stderr(stderr):
                code = bootstrap.main(self._arguments(root, destination))
            self.assertEqual(2, code)
            self.assertIn("No workspace destination was created by this attempt.", stderr.getvalue())
            self.assertNotIn("preserved at:", stderr.getvalue())
            self.assertFalse(destination.exists())

    def test_main_reports_created_workspace_only_after_observed_partial_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "destinations"
            parent.mkdir()
            destination = parent / "Project"
            destination.mkdir()
            stderr = io.StringIO()
            failure = bootstrap.BootstrapError("fixture failure after creation", destination_created=True)
            with patch.object(bootstrap, "bootstrap", side_effect=failure), contextlib.redirect_stderr(stderr):
                code = bootstrap.main(self._arguments(root, destination))
            self.assertEqual(2, code)
            self.assertIn(f"A workspace was created before a later setup/verification failure and was preserved at: {destination}", stderr.getvalue())
            self.assertTrue(destination.is_dir())

    def test_bootstrap_reports_temporary_runtime_cleanup_from_observed_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            package.mkdir()
            self._create_valid_runtime_package(package)
            parent = root / "destinations"
            parent.mkdir()
            destination = parent / "Project"
            created_temp_roots: list[Path] = []
            real_temp_directory = bootstrap.tempfile.TemporaryDirectory

            def track_temp_directory(*args, **kwargs):
                temporary_directory = real_temp_directory(*args, **kwargs)
                created_temp_roots.append(Path(temporary_directory.name))
                return temporary_directory

            def fake_run_command(args, cwd, label):
                if label == "Workspace creation":
                    Path(args[args.index("--destination") + 1]).mkdir()

            with patch.object(bootstrap, "run_command", side_effect=fake_run_command), \
                 patch.object(bootstrap.tempfile, "TemporaryDirectory", side_effect=track_temp_directory):
                result = bootstrap.bootstrap(package, "Example Project", destination, destination)

            self.assertTrue(result["temporary_runtime_removed"])
            self.assertTrue(created_temp_roots)
            self.assertTrue(all(not path.exists() for path in created_temp_roots))
            self.assertTrue(destination.is_dir())

    def _create_valid_runtime_package(self, root: Path) -> None:
        BootstrapPackageTests()._create_package(root)
        runtime = root / "archives/project-blueprint-framework-3.0.0-bootstrap-runtime.zip"
        workspace = root / "archives/project-blueprint-workspace-3.0.0.zip"
        with zipfile.ZipFile(runtime, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("VERSION", "3.0.0\n")
            zf.writestr("bp.py", "# runtime launcher\n")
            zf.writestr("src/blueprint_framework/source_cli.py", "# source cli\n")
            zf.writestr("_framework/tools/workspace_paths.py", "# workspace paths\n")
        with zipfile.ZipFile(workspace, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.md", "Workspace starter\n")

        manifest_path = root / "PACKAGE-MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["bootstrap_runtime_sha256"] = hashlib.sha256(runtime.read_bytes()).hexdigest()
        manifest["workspace_archive_sha256"] = hashlib.sha256(workspace.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        payload = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS.txt"
        )
        lines = [f"{hashlib.sha256((root / relative).read_bytes()).hexdigest()}  {relative}" for relative in payload]
        (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
