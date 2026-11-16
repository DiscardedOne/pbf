"""Workspace path and layout regression tests for the v3 architecture."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
TOOLS = SOURCE_ROOT / "_framework" / "tools"
TESTS = SOURCE_ROOT / "framework-dev" / "tests"
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from workspace_paths import (  # noqa: E402
    SourcePaths, WorkspaceDiscoveryError, WorkspacePaths, discover_context,
    python_version_supported,
)
from workspace_fixture import create_workspace  # noqa: E402


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="blueprint-v3-phase1-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = create_workspace(SOURCE_ROOT, self.base / "Path Safety Example Blueprint")
        self.paths = WorkspacePaths.from_root(self.root)

    def test_v23_3_golden_fingerprint_is_unchanged(self):
        fixture = SOURCE_ROOT / "framework-dev/tests/fixtures/v2.3.2-fingerprint-golden.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("blueprint_v3_runtime", self.root / "_framework/tools/blueprint.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        actual = module.approval_fingerprint(data["document_text"], data["manifest_document"])
        self.assertEqual(data["expected_sha256"], actual)

    def test_fixed_layout_paths(self):
        p = self.paths
        self.assertEqual(p.docs, self.root / "docs")
        self.assertEqual(p.framework, self.root / "_framework")
        self.assertEqual(p.control, self.root / "_control")
        self.assertEqual(p.registry, self.root / "_control/registry")
        self.assertEqual(p.status_transitions, self.root / "_control/logs/status-transitions.jsonl")
        self.assertEqual(p.adr, self.root / "docs/04-architecture/adr")
        self.assertEqual(p.specs, self.root / "docs/_assets/specs")
        self.assertEqual(p.gitattributes, self.root / ".gitattributes")
        self.assertEqual(p.gitignore, self.root / ".gitignore")
        self.assertFalse((self.root / "docs/03-architecture/adr").exists())

    def test_discover_from_root_and_nested_directory(self):
        (self.root / "docs/04-architecture").mkdir(parents=True, exist_ok=True)
        mode, context = discover_context(start=self.root, launcher_path=self.root / "bp.py")
        self.assertEqual(mode, "workspace")
        self.assertEqual(context.root, self.root)
        mode, nested = discover_context(start=self.root / "docs/04-architecture")
        self.assertEqual(mode, "workspace")
        self.assertEqual(nested.root, self.root)

    def test_source_discovery_and_starter_template_marker_do_not_collide(self):
        mode, context = discover_context(start=SOURCE_ROOT / "starter", launcher_path=SOURCE_ROOT / "bp.py")
        self.assertEqual(mode, "source")
        self.assertIsInstance(context, SourcePaths)
        self.assertFalse((SOURCE_ROOT / "starter/_control/WORKSPACE.json").exists())
        self.assertTrue((SOURCE_ROOT / "starter/_control/WORKSPACE.json.template").is_file())

    def test_workspace_configuration_rejects_arbitrary_paths_and_duplicate_version(self):
        config_path = self.paths.workspace_config
        original = json.loads(config_path.read_text(encoding="utf-8"))
        for key, value in (("paths", {"docs": "../../escape"}), ("framework_version", "3.0.0"),
                           ("profile_ranks", {"lite": 99, "standard": 100, "exhaustive": 101})):
            mutated = dict(original)
            mutated[key] = value
            config_path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaises(WorkspaceDiscoveryError):
                WorkspacePaths.from_root(self.root)
        config_path.write_text(json.dumps(original), encoding="utf-8")

    def test_invalid_schema_and_layout_are_rejected(self):
        path = self.paths.workspace_config
        original = json.loads(path.read_text(encoding="utf-8"))
        for key, value in (("workspace_schema_version", 999), ("layout_version", 999),
                           ("workspace_schema_version", True), ("layout_version", True)):
            mutated = dict(original)
            mutated[key] = value
            path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaises(WorkspaceDiscoveryError):
                WorkspacePaths.from_root(self.root)
        path.write_text(json.dumps(original), encoding="utf-8")

    def test_document_resolution_rejects_path_escape(self):
        for value in ("../../outside.md", "/tmp/outside.md", "C:\\outside.md", "04-architecture\\x.md"):
            self.assertIsNone(self.paths.resolve_document(value), value)
        good = self.paths.resolve_document("04-architecture/context.md")
        self.assertEqual(good, self.root / "docs/04-architecture/context.md")

    def test_symlink_escape_is_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "docs/escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        self.assertIsNone(self.paths.resolve_document("escape/file.md"))

    def test_case_and_unicode_normalization_collisions_detected(self):
        (self.root / "docs/Foo").mkdir(parents=True)
        (self.root / "docs/foo").mkdir(parents=True)
        (self.root / "docs/Foo/a.md").write_text("a", encoding="utf-8")
        (self.root / "docs/foo/b.md").write_text("b", encoding="utf-8")
        composed = self.root / "docs/é"
        decomposed = self.root / "docs/e\u0301"
        try:
            composed.mkdir()
            decomposed.mkdir()
        except FileExistsError:
            self.skipTest("filesystem normalizes Unicode names before collision scan")
        collisions = self.paths.case_collisions()
        self.assertTrue(any(a.casefold() == "docs/foo" and b.casefold() == "docs/foo" and a != b for a, b in collisions), collisions)
        self.assertTrue(any(a != b and {a, b} == {"docs/é", "docs/e\u0301"} for a, b in collisions), collisions)

    def test_framework_manifest_drift_warns_normally_and_errors_in_strict_mode(self):
        refresh = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "status", "--write"],
                                 cwd=self.root, text=True, capture_output=True)
        self.assertEqual(refresh.returncode, 0, refresh.stdout + refresh.stderr)
        clean = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "check", "--strict"],
                               cwd=self.root, text=True, capture_output=True)
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        managed = self.root / "_framework" / "WORKSPACE-CONFIG.md"
        managed.write_text(managed.read_text(encoding="utf-8") + "\nLocal accidental edit.\n", encoding="utf-8")
        normal = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "check"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
        self.assertIn("WARN  FRAMEWORK: Framework-managed file drift", normal.stdout)
        strict = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "check", "--strict"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("ERROR FRAMEWORK: Framework-managed file drift", strict.stdout)

    def test_manifest_rejects_unsafe_or_missing_entries(self):
        manifest = self.paths.framework_manifest
        original = json.loads(manifest.read_text(encoding="utf-8"))
        invalid = dict(original)
        invalid["files"] = dict(original["files"])
        invalid["files"]["../../outside.md"] = "0" * 64
        manifest.write_text(json.dumps(invalid), encoding="utf-8")
        from workspace_paths import validate_framework_manifest
        issues = validate_framework_manifest(self.paths)
        self.assertTrue(any("Unsafe framework manifest path" in message for _, message in issues), issues)
        missing = dict(original)
        missing["files"] = dict(original["files"])
        missing["files"]["_framework/not-here.md"] = "0" * 64
        manifest.write_text(json.dumps(missing), encoding="utf-8")
        issues = validate_framework_manifest(self.paths)
        self.assertTrue(any("Framework-managed file is missing" in message for _, message in issues), issues)
        manifest.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

    def test_gitattributes_lf_and_binary_policy_is_present(self):
        from workspace_paths import validate_gitattributes
        self.assertEqual(validate_gitattributes(self.paths), [])
        path = self.paths.gitattributes
        original = path.read_text(encoding="utf-8")
        path.write_text("*.md text\n", encoding="utf-8")
        issues = validate_gitattributes(self.paths)
        self.assertTrue(any("*.md text eol=lf" in message for _, message in issues), issues)
        self.assertTrue(any("*.template text eol=lf" in message for _, message in issues), issues)
        self.assertTrue(any("*.png binary" in message for _, message in issues), issues)
        path.write_text(original, encoding="utf-8")

    def test_workspace_fixed_root_symlink_escape_is_rejected(self):
        docs = self.root / "docs"
        original_docs = self.root / "docs-original"
        outside = self.base / "outside-docs"
        outside.mkdir()
        docs.rename(original_docs)
        try:
            docs.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            original_docs.rename(docs)
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaises(ValueError):
            WorkspacePaths.from_root(self.root)
        docs.unlink()
        original_docs.rename(docs)

    def test_workspace_marker_symlink_escape_is_rejected(self):
        marker = self.paths.workspace_config
        outside = self.base / "outside-workspace.json"
        outside.write_text(marker.read_text(encoding="utf-8"), encoding="utf-8")
        backup = self.root / "_control" / "WORKSPACE.backup.json"
        marker.rename(backup)
        try:
            marker.symlink_to(outside)
        except (OSError, NotImplementedError):
            backup.rename(marker)
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaises(ValueError):
            WorkspacePaths.from_root(self.root)
        marker.unlink()
        backup.rename(marker)

    def test_workspace_relative_path_rejects_external_path(self):
        with self.assertRaises(ValueError):
            self.paths.relative(self.base / "outside.txt")

    def test_index_document_links_are_relative_from_control_registry(self):
        scaffold = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "scaffold", "--only", "D0.01"],
                                  cwd=self.root, text=True, capture_output=True)
        self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)
        index = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "index"],
                               cwd=self.root, text=True, capture_output=True)
        self.assertEqual(index.returncode, 0, index.stdout + index.stderr)
        text = self.paths.index.read_text(encoding="utf-8")
        self.assertIn("../../docs/00-overview/vision-capture.md", text)


    def test_source_manifest_identity_and_versions_are_validated(self):
        with tempfile.TemporaryDirectory(prefix="bp-source-marker-") as td:
            root = Path(td)
            marker = root / "framework-dev" / "SOURCE-MANIFEST.json"
            marker.parent.mkdir(parents=True)
            valid = {
                "source_schema_version": 1,
                "source_identity": "project-blueprint-framework",
                "source_layout_version": 1,
            }
            marker.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(SourcePaths.from_root(root).root, root.resolve())
            for key, value in (("source_schema_version", True), ("source_schema_version", 9),
                               ("source_identity", "another-tool"), ("source_layout_version", 9)):
                mutated = dict(valid)
                mutated[key] = value
                marker.write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaises(WorkspaceDiscoveryError):
                    SourcePaths.from_root(root)

    def test_starter_seed_is_not_a_workspace_marker_without_launcher(self):
        mode, context = discover_context(start=SOURCE_ROOT / "starter")
        self.assertEqual(mode, "source")
        self.assertIsInstance(context, SourcePaths)

    def test_text_hash_is_line_ending_normalized(self):
        from workspace_paths import normalized_file_sha256
        path = self.root / "_framework" / "WORKSPACE-CONFIG.md"
        original = path.read_bytes()
        lf_hash = normalized_file_sha256(path)
        path.write_bytes(original.replace(b"\n", b"\r\n"))
        self.assertEqual(lf_hash, normalized_file_sha256(path))
        path.write_bytes(original)

    def test_unlisted_framework_file_is_reported_as_drift(self):
        from workspace_paths import validate_framework_manifest
        extra = self.root / "_framework" / "untracked-runtime-note.md"
        extra.write_text("extra\n", encoding="utf-8")
        issues = validate_framework_manifest(self.paths)
        self.assertTrue(any("Untracked file in framework-managed area" in message for _, message in issues), issues)

    def test_workspace_structure_defaults_reject_path_escape(self):
        from workspace_paths import validate_workspace_structure
        defaults = json.loads(self.paths.defaults.read_text(encoding="utf-8"))
        defaults["workspace_structure"]["required_files"].append("../../outside.txt")
        issues = validate_workspace_structure(self.paths, defaults)
        self.assertTrue(any("Unsafe required file path" in message for _, message in issues), issues)

    def test_runtime_has_no_legacy_root_path_resolver(self):
        import ast
        runtime = SOURCE_ROOT / "_framework/tools/blueprint.py"
        text = runtime.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertTrue({"ROOT", "DOCS", "REG", "FW", "LOGS", "STATE_EVENT_LOG"}.isdisjoint(names))
        functions = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertNotIn("workspace_path", functions)
        # Match obsolete root-relative paths, not the legitimate new
        # ``_control/registry/...`` paths that contain the same suffix.
        self.assertNotRegex(text, r'(?<!_control/)registry/(?:WORKSPACE\.json|MANIFEST\.md|PHASES\.md|INDEX\.md)')
        for legacy in ('"docs/03-architecture/adr"', '"../docs/"', '"python tools/blueprint.py"'):
            self.assertNotIn(legacy, text, f"legacy runtime reference remains: {legacy}")


    def test_v23_2_profile_and_dependency_snapshot_is_preserved(self):
        fixture = SOURCE_ROOT / "framework-dev/tests/fixtures/v2.3.2-profile-snapshot.json"
        expected = json.loads(fixture.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("blueprint_v3_profile_snapshot", self.root / "_framework/tools/blueprint.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        module.set_workspace_paths(self.paths)
        actual_docs = module.load_manifest()
        actual = {
            item["id"]: {
                "profile_tier": item["profile_tier"],
                "depends_on": ", ".join(item.get("depends", [])) or "-",
            }
            for item in actual_docs
        }
        self.assertEqual(expected["manifest_docs"], actual)
        defaults = json.loads(self.paths.defaults.read_text(encoding="utf-8"))
        expected_config = expected["workspace_config"]
        self.assertEqual(defaults["vision_document_id"], expected_config["vision_document_id"])
        self.assertEqual(defaults["architecture_document_id"], expected_config["architecture_document_id"])
        self.assertEqual(defaults["bootstrap_doc_ids"], expected_config["bootstrap_doc_ids"])
        self.assertEqual(defaults["id_index_document_ids"], expected_config["id_index_document_ids"])
        self.assertEqual(defaults["profile_ranks"], expected_config["profile_ranks"])
        self.assertEqual(defaults["profile_policy"], expected_config["profile_policy"])
        workspace_config = json.loads(self.paths.workspace_config.read_text(encoding="utf-8"))
        self.assertEqual(workspace_config["profile"], expected_config["profile"])

    def test_source_launcher_selects_source_mode_from_starter_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(SOURCE_ROOT / "bp.py"), "--help"],
            cwd=SOURCE_ROOT / "starter", text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("verify", result.stdout)
        self.assertIn("build", result.stdout)
        self.assertIn("new", result.stdout)
        self.assertNotIn("No Project Blueprint source or workspace marker", result.stdout)
        self.assertFalse((SOURCE_ROOT / "starter" / "_control" / "WORKSPACE.json").exists())

    def test_python_guard(self):
        self.assertFalse(python_version_supported((3, 10, 99)))
        self.assertTrue(python_version_supported((3, 11, 0)))
        self.assertTrue(python_version_supported((3, 15, 0)))


    def test_root_launcher_refuses_python_below_311(self):
        import contextlib
        import io
        spec = importlib.util.spec_from_file_location("blueprint_root_launcher", SOURCE_ROOT / "bp.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = module._python_guard((3, 10, 99))
        self.assertEqual(result, 3)
        self.assertIn("requires Python 3.11 or newer", output.getvalue())
        self.assertIn("py -3.11", output.getvalue())
        self.assertIn("python3.11", output.getvalue())

    def test_prerelease_version_parser_accepts_alpha_one(self):
        spec = importlib.util.spec_from_file_location("blueprint_v3_runtime_parser", self.root / "_framework/tools/blueprint.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertTrue(module.parse_framework_version("3.0.0-alpha.1"))
        self.assertTrue(module.parse_framework_version("3.0.0"))
        self.assertFalse(module.parse_framework_version("3.0-alpha.1"))

    def test_launcher_reports_workspace_version_and_runs_from_nested_directory(self):
        result = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "--version"], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected_version = (SOURCE_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertIn(expected_version, result.stdout)
        nested = self.root / "docs/01-discovery"
        nested.mkdir(parents=True)
        result = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "--version"], cwd=nested,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
