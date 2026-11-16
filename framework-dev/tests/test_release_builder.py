from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools/release/build_release.py"
SPEC = importlib.util.spec_from_file_location("pbf_build_release", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load release builder test target")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ReleaseBuilderTests(unittest.TestCase):
    def test_deterministic_zip_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "b.txt").write_text("second\n", encoding="utf-8")
            (source / "a.txt").write_text("first\n", encoding="utf-8")
            first, second = root / "first.zip", root / "second.zip"
            BUILDER.write_deterministic_zip(source, first)
            BUILDER.write_deterministic_zip(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_checksum_inventory_covers_exact_payload_and_verifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.txt").write_text("one\n", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested/two.txt").write_text("two\n", encoding="utf-8")
            generated = BUILDER.write_checksum_inventory(root)
            self.assertEqual(set(generated), {"one.txt", "nested/two.txt"})
            self.assertEqual(BUILDER.verify_checksum_inventory(root), generated)

    def test_checksum_inventory_rejects_unlisted_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.txt").write_text("one\n", encoding="utf-8")
            BUILDER.write_checksum_inventory(root)
            (root / "extra.txt").write_text("extra\n", encoding="utf-8")
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.verify_checksum_inventory(root)

    def test_archive_component_case_collision_is_rejected(self):
        with self.assertRaises(BUILDER.ReleaseBuildError):
            BUILDER._check_member_collisions(["A/one.txt", "a/two.txt"])

    def test_archive_file_directory_conflict_is_rejected(self):
        with self.assertRaises(BUILDER.ReleaseBuildError):
            BUILDER._check_member_collisions(["a", "a/b.txt"])

    def test_version_and_architecture_are_read_from_authoritative_files(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual(BUILDER.read_version(root), (root / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(BUILDER.read_architecture_revision(root), "1.3.4")

    def test_release_version_rendering_and_nested_manifest_path_scope(self):
        self.assertEqual(
            BUILDER.render_release_text("PBF {{PBF_VERSION}}\n", "3.7.2"),
            "PBF 3.7.2\n",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_file = root / "PACKAGE-MANIFEST.json"
            license_file = root / "LICENSE"
            runtime_file = root / "archives/runtime.zip"
            workspace_file = root / "archives/workspace.zip"
            runtime_file.parent.mkdir(parents=True)
            manifest_file.write_text("{}\n", encoding="utf-8")
            license_file.write_text("Apache License Version 2.0, January 2004\n", encoding="utf-8")
            runtime_file.write_bytes(b"runtime")
            workspace_file.write_bytes(b"workspace")
            members = {
                "PACKAGE-MANIFEST.json": BUILDER.sha256_file(manifest_file),
                "archives/runtime.zip": BUILDER.sha256_file(runtime_file),
                "archives/workspace.zip": BUILDER.sha256_file(workspace_file),
            }
            outer_manifest = {
                "license": "Apache-2.0",
                "license_file": "LICENSE",
                "nested_agent_package": "agent-package/PBF-Agent-Package.zip",
                "nested_agent_package_sha256": "a" * 64,
                "nested_package_contents": {
                    "package_manifest": "PACKAGE-MANIFEST.json",
                    "bootstrap_runtime": {"path": "archives/runtime.zip", "sha256": BUILDER.sha256_file(runtime_file)},
                    "workspace_starter": {"path": "archives/workspace.zip", "sha256": BUILDER.sha256_file(workspace_file)},
                },
            }
            BUILDER.validate_outer_manifest_references(outer_manifest, members)
            bad_path = json.loads(json.dumps(outer_manifest))
            bad_path["nested_package_contents"]["bootstrap_runtime"]["path"] = "archives/missing.zip"
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.validate_outer_manifest_references(bad_path, members)
            bad_hash = json.loads(json.dumps(outer_manifest))
            bad_hash["nested_package_contents"]["bootstrap_runtime"]["sha256"] = "0" * 64
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.validate_outer_manifest_references(bad_hash, members)
            bad_manifest_path = json.loads(json.dumps(outer_manifest))
            bad_manifest_path["nested_package_contents"]["package_manifest"] = "nested/PACKAGE-MANIFEST.json"
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.validate_outer_manifest_references(bad_manifest_path, members)

    def test_safe_relative_name_rejects_windows_reserved_and_invalid_components(self):
        for value in ("folder/CON.txt", "folder/name:stream", "folder/trailing.", "folder/trailing ", "folder/bad?.txt", "folder/LPT9.log"):
            with self.subTest(value=value), self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER._safe_relative_name(value)

    def test_source_symlinks_are_rejected_before_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            try:
                (source / "linked.txt").symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Symlinks unavailable on this host: {exc}")
            with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "Symlink"):
                BUILDER.write_deterministic_zip(source, root / "source.zip")

    def test_unicode_normalization_collision_is_rejected(self):
        with self.assertRaises(BUILDER.ReleaseBuildError):
            BUILDER._check_member_collisions(["caf\u00e9.txt", "cafe\u0301.txt"])

    def test_extract_validated_zip_rejects_duplicate_members_and_cleans_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive, "w") as zf:
                    zf.writestr("same.txt", "one")
                    zf.writestr("same.txt", "two")
            destination = root / "out"
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.extract_validated_zip(archive, destination)
            self.assertFalse(destination.exists())

    def test_extract_validated_zip_rejects_symlink_and_cleans_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "symlink.zip"
            info = zipfile.ZipInfo("linked")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(info, "target.txt")
            destination = root / "out"
            with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "Link/encrypted"):
                BUILDER.extract_validated_zip(archive, destination)
            self.assertFalse(destination.exists())

    def test_extract_validated_zip_enforces_compression_ratio_and_cleans_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "ratio.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                zf.writestr("high-ratio.txt", "A" * 2_000_000)
            destination = root / "out"
            with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "compression ratio"):
                BUILDER.extract_validated_zip(archive, destination)
            self.assertFalse(destination.exists())

    def _minimal_release_assets(self, root: Path) -> None:
        (root / "VERSION").write_text("3.0.0\n", encoding="utf-8")
        (root / "LICENSE").write_text("Apache License Version 2.0, January 2004\n", encoding="utf-8")
        (root / "starter").mkdir(parents=True)
        (root / "starter/LICENSE").write_bytes((root / "LICENSE").read_bytes())
        (root / "starter/PBF-LICENSE-SCOPE.md").write_text(
            "The PBF license does **not** automatically apply to owner-authored project-specific content.\n",
            encoding="utf-8",
        )
        (root / "tools/agent-bootstrap").mkdir(parents=True)
        (root / "tools/agent-bootstrap/bootstrap.py").write_text("# bootstrap\n", encoding="utf-8")
        required = [
            "README-RELEASE.md", "QUICKSTART.md",
            "agent/AGENT-OPERATING-INSTRUCTIONS.md", "agent/AGENT-STARTUP-PROMPT.md",
            "docs/README.md", "docs/PBF-Architecture-and-Technical-Reference.md",
            "docs/PBF-Maintainer-Handbook.md", "docs/PBF-Project-Overview-and-Method.md",
            "docs/PBF-Quality-Assurance-and-Review-Policy.md", "docs/PBF-Release-Notes-and-Verification.md",
            "docs/PBF-User-Guide.md",
        ]
        for relative in required:
            target = root / "release-assets" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Release asset content\n", encoding="utf-8")
        index = root / "release-assets/docs/README.md"
        index.write_text("\n".join(Path(item).name for item in required if item.startswith("docs/") and item != "docs/README.md"), encoding="utf-8")

    def test_validate_release_assets_rejects_hard_coded_current_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._minimal_release_assets(root)
            target = root / "release-assets/docs/PBF-User-Guide.md"
            target.write_text("PBF 3.0.0 release guide\n", encoding="utf-8")
            with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "hard-codes the current version"):
                BUILDER.validate_release_assets(root)

    def test_run_logged_enforces_timeout_and_preserves_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "timeout.log"
            with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "timed out"):
                BUILDER.run_logged(
                    [__import__("sys").executable, "-B", "-c", "import time; time.sleep(2)"],
                    root, log, "Timeout fixture", timeout=0.1,
                )
            self.assertTrue(log.is_file())

    def _prepare_build_root(self, root: Path) -> Path:
        (root / "VERSION").write_text("3.0.0\n", encoding="utf-8")
        return root / "dist/PBF-v3.0.0-Agent-First-Release.zip"

    def _build_with_fake_package(self, root: Path, fake_builder, *, force: bool):
        with patch.object(BUILDER, "read_architecture_revision", return_value="1.3.4"), \
             patch.object(BUILDER, "validate_release_assets", return_value=None), \
             patch.object(BUILDER, "build_package", side_effect=fake_builder):
            return BUILDER.build_release(force=force, root=root)

    def test_build_release_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = self._prepare_build_root(root)
            output.parent.mkdir(parents=True)
            output.write_bytes(b"previous release")
            with patch.object(BUILDER, "read_architecture_revision", return_value="1.3.4"), \
                 patch.object(BUILDER, "validate_release_assets", return_value=None), \
                 patch.object(BUILDER, "build_package") as package_builder:
                with self.assertRaisesRegex(BUILDER.ReleaseBuildError, "refusing to overwrite"):
                    BUILDER.build_release(force=False, root=root)
                package_builder.assert_not_called()
            self.assertEqual(output.read_bytes(), b"previous release")

    def test_force_build_failure_preserves_previous_release_and_cleans_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = self._prepare_build_root(root)
            output.parent.mkdir(parents=True)
            output.write_bytes(b"previous release")

            def broken_builder(source_root, work_root, version, architecture, logs_dir):
                candidate = work_root / "broken.zip"
                candidate.write_bytes(b"not a zip archive")
                return candidate, {}

            with self.assertRaises(zipfile.BadZipFile):
                self._build_with_fake_package(root, broken_builder, force=True)
            self.assertEqual(output.read_bytes(), b"previous release")
            self.assertFalse(output.with_name(output.name + ".candidate").exists())
            self.assertFalse(output.with_name(output.name + ".tmp").exists())

    def test_force_build_success_replaces_previous_release_after_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = self._prepare_build_root(root)
            output.parent.mkdir(parents=True)
            output.write_bytes(b"previous release")

            def successful_builder(source_root, work_root, version, architecture, logs_dir):
                candidate = work_root / "candidate.zip"
                with zipfile.ZipFile(candidate, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("payload.txt", "verified candidate")
                return candidate, {"test_count": 0}

            self._build_with_fake_package(root, successful_builder, force=True)
            with zipfile.ZipFile(output, "r") as zf:
                self.assertEqual(zf.read("payload.txt"), b"verified candidate")
            self.assertFalse(output.with_name(output.name + ".candidate").exists())

    def test_final_bootstrap_evidence_is_appended_from_observed_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "BUILD-VERIFICATION.md"
            evidence.write_text("# Build Verification\n\nChecks run before final integration.\n", encoding="utf-8")
            result = {
                "status": "verified",
                "temporary_runtime_removed": True,
                "checks": [
                    "bootstrap runtime verification passed",
                    "workspace creation completed",
                    "workspace check --strict passed",
                    "workspace index --check passed",
                    "workspace audit-state --strict passed",
                ],
            }
            BUILDER.append_final_bootstrap_evidence(evidence, result, provenance_audit_passed=True)
            rendered = evidence.read_text(encoding="utf-8")
            self.assertIn("## Final nested-package bootstrap", rendered)
            self.assertIn("Temporary runtime cleanup: confirmed", rendered)
            self.assertNotIn("pending", rendered.lower())
            with self.assertRaises(BUILDER.ReleaseBuildError):
                BUILDER.append_final_bootstrap_evidence(evidence, result, provenance_audit_passed=True)


if __name__ == "__main__":
    unittest.main()
