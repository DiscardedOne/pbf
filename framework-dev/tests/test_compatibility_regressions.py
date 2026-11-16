"""Ported regression tests for Blueprint 2.3.3 behaviour on the v3 workspace layout (standard library only).

Run the maintained suite from the developer repository root with: python -B bp.py verify --tests
Each test uses a disposable v3 workspace fixture; no test mutates the installed framework.
"""
from __future__ import annotations

import json
import io
import importlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_REL = Path("bp.py")
sys.path.insert(0, str(SOURCE_ROOT / "framework-dev" / "tests"))
sys.path.insert(0, str(SOURCE_ROOT / "_framework" / "tools"))
from workspace_fixture import create_workspace

_FIXTURE_TEMP = None
_LEGACY_WORKSPACE_FIXTURE = None


def setUpModule():
    """Build one canonical v3 starter fixture for this test session."""
    global _FIXTURE_TEMP, _LEGACY_WORKSPACE_FIXTURE
    _FIXTURE_TEMP = tempfile.TemporaryDirectory(prefix="blueprint-v233-port-fixture-")
    _LEGACY_WORKSPACE_FIXTURE = Path(_FIXTURE_TEMP.name) / "workspace"
    create_workspace(SOURCE_ROOT, _LEGACY_WORKSPACE_FIXTURE,
                     project_name="Legacy v2.3.3 Regression Fixture", preserve_onboarding=True)
    launcher = _LEGACY_WORKSPACE_FIXTURE / "bp.py"
    for args in (("status", "--write"), ("index",), ("check", "--strict")):
        result = subprocess.run([sys.executable, "-B", str(launcher), *args],
                                cwd=_LEGACY_WORKSPACE_FIXTURE, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Could not prepare shared v3 regression fixture: {args}\n{result.stdout}")


def tearDownModule():
    global _FIXTURE_TEMP, _LEGACY_WORKSPACE_FIXTURE
    if _FIXTURE_TEMP is not None:
        _FIXTURE_TEMP.cleanup()
    _FIXTURE_TEMP = None
    _LEGACY_WORKSPACE_FIXTURE = None


class BlueprintTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="blueprint-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        shutil.copytree(_LEGACY_WORKSPACE_FIXTURE, self.root)
        self.script = self.root / SCRIPT_REL

    def run_cli(self, *args, expected=None):
        # The legacy behavioural tests exercise the workspace command handlers
        # in-process for speed. Source CLI integration tests separately exercise
        # the real root launcher, source/workspace dispatch and end-to-end `new`.
        module = importlib.import_module("blueprint")
        module.set_workspace_paths(module.WorkspacePaths.from_root(self.root))
        output = io.StringIO()
        returncode = 0
        try:
            with redirect_stdout(output), redirect_stderr(output):
                try:
                    returncode = module.main(list(map(str, args)))
                except SystemExit as exc:
                    returncode = int(exc.code or 0)
        except Exception:
            raise
        result = subprocess.CompletedProcess(
            [sys.executable, "-B", str(self.script), *map(str, args)],
            returncode, output.getvalue(), "")
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def manifest_row(self, doc_id):
        path = self.root / "_control/registry/MANIFEST.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.startswith("| " + doc_id + " |"):
                return line
        self.fail(f"Manifest row not found: {doc_id}")

    def replace_manifest_cell(self, doc_id, column, value):
        path = self.root / "_control/registry/MANIFEST.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("| Doc ID |"))
        headers = [c.strip() for c in lines[header_idx].strip("|").split("|")]
        col_idx = headers.index(column)
        for i, line in enumerate(lines):
            if line.startswith("| " + doc_id + " |"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                cells[col_idx] = value
                lines[i] = "| " + " | ".join(cells) + " |"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return
        self.fail(f"Manifest row not found: {doc_id}")

    def refresh_framework_manifest_entry(self, relative_path):
        manifest_path = self.root / "_framework/FRAMEWORK-MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = self.root / relative_path
        raw = target.read_bytes()
        if target.suffix.lower() in {".md", ".py", ".json", ".jsonl", ".txt", ".yaml", ".yml"}:
            raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        manifest["files"][relative_path] = __import__("hashlib").sha256(raw).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    def replace_catalog_cell(self, doc_id, column, value):
        path = self.root / "_framework/DOC-CATALOG.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("| Doc ID |"))
        headers = [c.strip() for c in lines[header_idx].strip("|").split("|")]
        col_idx = headers.index(column)
        for i, line in enumerate(lines):
            if line.startswith("| " + doc_id + " |"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                cells[col_idx] = value
                lines[i] = "| " + " | ".join(cells) + " |"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                self.refresh_framework_manifest_entry("_framework/DOC-CATALOG.md")
                return
        self.fail(f"Catalog row not found: {doc_id}")

    def add_custom_manifest_doc(self, doc_id, phase, path, title="Custom test document", profile="lite", depends="-"):
        manifest = self.root / "_control/registry/MANIFEST.md"
        rows = manifest.read_text(encoding="utf-8").splitlines()
        row = (f"| {doc_id} | {path} | {phase} | active | Test-specific active document. | {profile} | S | not-started | {depends} | {title} | outline | 0.1 | 2026-10-20 |")
        insert_at = max(i for i, line in enumerate(rows) if line.startswith("| D")) + 1
        rows.insert(insert_at, row)
        manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def add_custom_doc(self, doc_id="D9.01", phase=9, profile="lite", path="09-special/custom.md"):
        manifest = self.root / "_control/registry/MANIFEST.md"
        rows = manifest.read_text(encoding="utf-8").splitlines()
        row = (f"| {doc_id} | {path} | {phase} | active | Test-specific active document. | {profile} | S | not-started | - | Custom phase test document | outline | 0.1 | 2026-10-20 |")
        # Insert in the canonical document table; use the last document row, not progress summaries.
        insert_at = max(i for i, line in enumerate(rows) if line.startswith("| D")) + 1
        rows.insert(insert_at, row)
        manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

        catalog = self.root / "_framework/DOC-CATALOG.md"
        cat_rows = catalog.read_text(encoding="utf-8").splitlines()
        cat_row = f"| {doc_id} | {path} | Custom phase test document | core | S | - | document | A concise purpose and result; Test-specific checklist |"
        index = max(i for i, line in enumerate(cat_rows) if line.startswith("| D")) + 1
        cat_rows.insert(index, cat_row)
        catalog.write_text("\n".join(cat_rows) + "\n", encoding="utf-8")
        self.refresh_framework_manifest_entry("_framework/DOC-CATALOG.md")

        phase_path = self.root / "_control/PHASES.md"
        phase_path.write_text(phase_path.read_text(encoding="utf-8") + f"| {phase} | Custom phase {phase} | active | Regression test. |\n", encoding="utf-8")


class ValidationCoverageTests(BlueprintTestCase):
    def test_baseline_strict_validation_passes(self):
        result = self.run_cli("check", "--strict", expected=0)
        self.assertIn("0 error(s), 0 warning(s)", result.stdout)

    def test_checker_scans_framework_markdown_for_broken_links(self):
        target = self.root / "_framework/PROTOCOLS.md"
        with target.open("a", encoding="utf-8") as f:
            f.write("\nBroken-link regression: [missing](does-not-exist.md)\n")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertRegex(result.stdout, r"_framework/PROTOCOLS\.md:\d+: broken link")

    def test_checker_scans_root_readme_for_broken_links(self):
        target = self.root / "README.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n[bad](missing-root-file.md)\n", encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertRegex(result.stdout, r"README\.md:\d+: broken link")

    def test_checker_scans_framework_mermaid(self):
        target = self.root / "_framework/DIAGRAMS.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n```mermaid\nnotARealDiagram\n```\n", encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("unknown type 'notARealDiagram'", result.stdout)

    def test_checker_resolves_reference_style_links(self):
        target = self.root / "README.md"
        with target.open("a", encoding="utf-8") as f:
            f.write("\nBroken reference: [missing destination][bad-target].\n\n[bad-target]: nowhere-to-go.md\n")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertRegex(result.stdout, r"README\.md:\d+: broken link")
        self.assertIn("nowhere-to-go.md", result.stdout)

    def test_checker_validates_heading_anchors(self):
        target = self.root / "README.md"
        with target.open("a", encoding="utf-8") as f:
            f.write("\n[broken section](README.md#not-a-real-heading)\n")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("heading anchor '#not-a-real-heading' does not exist", result.stdout)

    def test_checker_finds_stale_document_ids_in_diagram_index(self):
        target = self.root / "_framework/DIAGRAMS.md"
        with target.open("a", encoding="utf-8") as f:
            f.write("\nStale reference D99.99 should fail validation.\n")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("document reference D99.99 is not present", result.stdout)

    def test_catalog_manifest_path_mismatch_is_error(self):
        self.replace_catalog_cell("D1.01", "Path", "01-discovery/wrong-path.md")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("CATALOG: D1.01 path '01-discovery/wrong-path.md' differs from manifest path", result.stdout)

    def test_catalog_dependency_mismatch_is_error(self):
        self.replace_catalog_cell("D1.01", "Depends on", "D0.02, D0.01")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("CATALOG: D1.01 content dependencies", result.stdout)
        self.assertIn("differ from manifest", result.stdout)

    def test_catalog_title_mismatch_is_error(self):
        self.replace_catalog_cell("D1.01", "Title", "A different title")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("CATALOG: D1.01 title 'A different title' differs from manifest title 'Vision and problem statement'", result.stdout)

    def test_empty_catalog_title_is_error(self):
        self.replace_catalog_cell("D1.01", "Title", "")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("CATALOG: D1.01 title '' differs from manifest title 'Vision and problem statement'", result.stdout)

    def test_catalog_distinguishes_file_and_folder_paths(self):
        self.replace_catalog_cell("D5.03", "Path", "05-design/components")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("CATALOG: D5.03 path '05-design/components' differs from manifest path '05-design/components/'", result.stdout)

    def test_lite_document_cannot_depend_on_deeper_profile_document(self):
        self.replace_manifest_cell("D0.01", "Profile tier", "exhaustive")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("PROFILE: D0.02 is tier 'lite' but content-depends on deeper-tier D0.01", result.stdout)

    def test_phase_gate_ignores_conditional_and_out_of_profile_documents(self):
        result = self.run_cli("check", "--gate", "1", "--profile", "lite", expected=1)
        gate_messages = [line for line in result.stdout.splitlines() if line.startswith("ERROR GATE 1:")]
        self.assertTrue(gate_messages, result.stdout)  # active Lite documents are still unapproved
        for conditional_id in ("D1.05", "D1.06", "D1.07"):
            self.assertFalse(any(conditional_id in line for line in gate_messages), result.stdout)

    def test_workspace_custom_phase_and_document_paths_are_dynamic(self):
        self.replace_manifest_cell("D1.01", "Path", "custom-discovery/problem.md")
        self.replace_catalog_cell("D1.01", "Path", "custom-discovery/problem.md")
        self.run_cli("status", "--write", expected=0)
        self.run_cli("index", expected=0)
        result = self.run_cli("check", "--strict", expected=0)
        status = self.run_cli("status", expected=0)
        self.assertIn("custom-discovery/problem.md", self.manifest_row("D1.01"))
        self.assertIn("Phase", status.stdout)

    def test_configured_traceability_index_path_follows_manifest_move(self):
        # Move the configured index identity by changing both source-of-truth tables.
        old = self.root / "docs/07-delivery/traceability-matrix.md"
        new_rel = "custom-governance/traceability.md"
        self.replace_manifest_cell("D7.04", "Path", new_rel)
        self.replace_catalog_cell("D7.04", "Path", new_rel)
        new = self.root / "docs" / new_rel
        new.parent.mkdir(parents=True, exist_ok=True)
        new.write_text("---\ndoc_id: D7.04\ntitle: Traceability matrix\nphase: 7\nstatus: not-started\nmaturity: outline\nversion: 0.1\nlast_updated: 2026-10-20\napplicability: active\napplicability_rationale: \"\"\nprofile_tier: exhaustive\ndepends_on: [D2.04, D4.03, D6.01]\nsummary: \"\"\n---\n\n| Requirement | Goal | Test |\n|---|---|---|\n| FR-777 | goal description | test description |\n", encoding="utf-8")
        self.add_custom_doc(doc_id="D9.99", phase=9, profile="lite", path="02-product/requirement-owner.md")
        source = self.root / "docs/02-product/requirement-owner.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("---\ndoc_id: D9.99\ntitle: Custom phase test document\nphase: 9\nstatus: not-started\nmaturity: outline\nversion: 0.1\nlast_updated: 2026-10-20\ndepends_on: []\nsummary: Test-specific active document.\napplicability: active\napplicability_rationale: Test-specific active document.\nprofile_tier: lite\n---\n\n# FR-777 — Test-only canonical definition\n", encoding="utf-8")
        self.run_cli("status", "--write", expected=0)
        self.run_cli("index", expected=0)
        result = self.run_cli("check", "--strict", expected=0)
        self.assertNotIn("ID FR-777 is defined in more than one file", result.stdout)

    def test_catalog_dependencies_do_not_reintroduce_structural_edges(self):
        path = self.root / "_framework/DOC-CATALOG.md"
        headers = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| Doc ID |"))
        h = [c.strip() for c in headers.strip("|").split("|")]
        dep_idx = h.index("Depends on")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| D") or line.startswith("| Doc ID |"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells[0] != "D0.02":
                self.assertNotIn("D0.02", [x.strip() for x in cells[dep_idx].split(",")])

    def test_manifest_title_mismatch_is_error(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        doc = self.root / "docs/00-overview/vision-capture.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("title: Vision capture and playback", "title: Wrong title", 1), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("front-matter title 'Wrong title' != manifest", result.stdout)

    def test_manifest_phase_mismatch_is_error(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        doc = self.root / "docs/00-overview/vision-capture.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("phase: 0", "phase: 1", 1), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("front-matter phase '1' != manifest '0'", result.stdout)

    def test_manifest_version_and_date_mismatches_are_errors(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        doc = self.root / "docs/00-overview/vision-capture.md"
        original = doc.read_text(encoding="utf-8")
        manifest_date = re.search(r"^last_updated: (\S+)", original, re.M).group(1)
        text = original.replace("version: 0.1", "version: 0.2", 1).replace(f"last_updated: {manifest_date}", "last_updated: 2000-01-01", 1)
        doc.write_text(text, encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("front-matter version '0.2' != manifest '0.1'", result.stdout)
        self.assertIn(f"front-matter last_updated '2000-01-01' != manifest '{manifest_date}'", result.stdout)

    def test_dependency_mismatch_is_error_not_warning(self):
        self.run_cli("scaffold", "--only", "D0.02", expected=0)
        doc = self.root / "docs/00-overview/documentation-scope.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("depends_on: [D0.01]", "depends_on: []", 1), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("front-matter depends_on [] differs from manifest ['D0.01']", result.stdout)

    def test_path_traversal_is_rejected(self):
        self.replace_manifest_cell("D1.01", "Path", "../../outside.md")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("unsafe path", result.stdout)

    def test_duplicate_paths_are_rejected(self):
        self.replace_manifest_cell("D1.01", "Path", "00-overview/vision-capture.md")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("duplicate document path", result.stdout)

    def test_child_document_must_stay_inside_repeatable_family_path(self):
        self.add_custom_manifest_doc("D5.03.01", 5, "05-design/not-components.md", title="Example component", depends="D4.03")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("is outside repeatable family path '05-design/components/'", result.stdout)

    def test_markdown_link_cannot_escape_workspace(self):
        target = self.root / "README.md"
        with target.open("a", encoding="utf-8") as f:
            f.write("\n[escape](../outside-workspace.md)\n")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("relative link escapes the workspace root", result.stdout)

    def test_phase_10_question_blocker_is_respected(self):
        self.add_custom_doc(doc_id="D10.01", phase=10, path="10-special/custom.md")
        qfile = self.root / "_control/registry/QUESTIONS.md"
        qlines = qfile.read_text(encoding="utf-8").splitlines()
        insertion = next(i for i, line in enumerate(qlines) if line.startswith("| ID | Question")) + 2
        qlines.insert(insertion, "| Q-777 | Multi-digit gate question | Gate 10 must respect P10 blockers. | P10 | Framework test | open | — | — |")
        qfile.write_text("\n".join(qlines) + "\n", encoding="utf-8")
        result = self.run_cli("check", "--gate", "10", "--profile", "lite", expected=1)
        self.assertIn("GATE 10: open question Q-777 blocks this phase", result.stdout)

    def test_excluded_existing_file_still_gets_metadata_checked(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        self.run_cli("applicability", "D0.01", "excluded", "--reason", "Test-only excluded item", expected=0)
        doc = self.root / "docs/00-overview/vision-capture.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("title: Vision capture and playback", "title: Mismatched title", 1), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("front-matter title 'Mismatched title' != manifest", result.stdout)

    def test_profile_rank_order_must_be_valid(self):
        p = self.root / "_framework/defaults/workspace-defaults.json"
        defaults = json.loads(p.read_text(encoding="utf-8"))
        defaults["profile_ranks"] = {"lite": 2, "standard": 1, "exhaustive": 3}
        p.write_text(json.dumps(defaults, indent=2) + "\n", encoding="utf-8")
        self.refresh_framework_manifest_entry("_framework/defaults/workspace-defaults.json")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("profile ranks must increase strictly", result.stdout)

    def test_custom_multidigit_phase_is_registered_and_reported(self):
        self.add_custom_doc(doc_id="D10.01", phase=10, path="10-special/custom.md")
        self.refresh_framework_manifest_entry("_framework/DOC-CATALOG.md")
        self.run_cli("status", "--write", expected=0)
        self.run_cli("index", expected=0)
        result = self.run_cli("check", "--strict", expected=0)
        status = self.run_cli("status", expected=0)
        self.assertIn("10 | Custom phase 10", status.stdout)
        self.assertIn("0 / 1", status.stdout)

    def test_unregistered_phase_is_error(self):
        self.add_custom_doc(doc_id="D9.01", phase=9)
        phase_file = self.root / "_control/PHASES.md"
        phase_file.write_text("\n".join(line for line in phase_file.read_text(encoding="utf-8").splitlines() if not line.startswith("| 9 |")) + "\n", encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("not registered", result.stdout)


class ApplicabilityAndProfileTests(BlueprintTestCase):
    def test_conditional_doc_cannot_be_scaffolded_until_activated(self):
        result = self.run_cli("scaffold", "--only", "D1.05", expected=2)
        self.assertIn("applicability=\"conditional\"", result.stdout)
        self.assertFalse((self.root / "docs/01-discovery/market-and-alternatives.md").exists())

    def test_applicability_command_requires_reason_and_updates_manifest(self):
        result = self.run_cli("applicability", "D1.05", "active", expected=2)
        self.assertIn("--reason", result.stdout)
        self.run_cli("applicability", "D1.05", "active", "--reason", "Product decision requires competitor research", expected=0)
        row = self.manifest_row("D1.05")
        self.assertIn("| active |", row)
        self.assertIn("Product decision requires competitor research", row)

    def test_applicability_activation_scaffolds_synchronized_metadata(self):
        self.run_cli("applicability", "D1.05", "active", "--reason", "Required by this project profile", expected=0)
        self.run_cli("scaffold", "--only", "D1.05", "--override-architecture-gate", "--override-reason", "Test-only scope exception", expected=0)
        doc = self.root / "docs/01-discovery/market-and-alternatives.md"
        text = doc.read_text(encoding="utf-8")
        self.assertIn("applicability: active", text)
        self.assertIn('applicability_rationale: "Required by this project profile"', text)
        self.assertTrue(list((self.root / "_control/logs/overrides").glob("architecture-gate-*.md")))
        check = self.run_cli("check", "--strict", expected=0)
        self.assertNotIn("front-matter applicability", check.stdout)

    def test_deferred_and_excluded_are_not_counted_in_progress(self):
        self.run_cli("applicability", "D1.05", "excluded", "--reason", "No competitor research needed for this internal tool", expected=0)
        result = self.run_cli("status", expected=0)
        self.assertIn("active / not-started / lite=", result.stdout)
        self.assertIn("excluded / not-started / standard=1", result.stdout)
        self.assertNotIn("| 1 | Discovery & business framing | 0 / 5", result.stdout)

    def test_profile_tiers_control_phase_scaffolding(self):
        lite = self.run_cli("scaffold", "--phase", "7", "--profile", "lite", "--dry-run", expected=0)
        standard = self.run_cli("scaffold", "--phase", "7", "--profile", "standard", "--dry-run", expected=0)
        self.assertNotIn("docs/07-delivery/work-breakdown-structure.md", lite.stdout)
        self.assertIn("docs/07-delivery/work-breakdown-structure.md", standard.stdout)

    def test_profile_command_persists_selection(self):
        self.run_cli("profile", "lite", expected=0)
        config = json.loads((self.root / "_control/WORKSPACE.json").read_text(encoding="utf-8"))
        self.assertEqual(config["profile"], "lite")
        status = self.run_cli("status", expected=0)
        self.assertIn("Selected profile: **Lite**", status.stdout)


class DependencySeparationTests(BlueprintTestCase):
    def test_d002_is_not_encoded_as_content_dependency_for_every_doc(self):
        text = (self.root / "_control/registry/MANIFEST.md").read_text(encoding="utf-8")
        headers = next(line for line in text.splitlines() if line.startswith("| Doc ID |"))
        h = [c.strip() for c in headers.strip("|").split("|")]
        dep_idx = h.index("Depends on")
        id_idx = h.index("Doc ID")
        for line in text.splitlines():
            if not line.startswith("| D"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) > dep_idx and cells[id_idx] != "D0.02":
                self.assertNotIn("D0.02", [x.strip() for x in cells[dep_idx].split(",")])

    def test_architecture_impact_separates_content_and_structural_candidates(self):
        result = self.run_cli("impact", "D0.02", expected=0)
        self.assertIn("Content-dependency impact for D0.02", result.stdout)
        self.assertIn("Structural-impact review candidates for D0.02 (NOT content dependents)", result.stdout)
        self.assertIn("[STRUCTURAL CANDIDATE] D1.01", result.stdout)

    def test_graph_is_content_dependency_only(self):
        result = self.run_cli("graph", expected=0)
        self.assertIn("edges represent content dependencies only", result.stdout)
        self.assertNotIn("D0_02 --> D1_01", result.stdout)

    def test_override_requires_reason(self):
        result = self.run_cli("scaffold", "--all", "--override-architecture-gate", expected=2)
        self.assertIn("requires --override-reason", result.stdout)


class ApprovalLintIndexTests(BlueprintTestCase):
    """v2.3 behaviours: approvals, SHA-256 fingerprints, lint, set-status, profiles, index, clean starter."""

    VALID_BODY = ("\n# {title}\n\n## Summary\n\nThe owner wants a small tool; scope agreed.\n\n## Content\n\n"
                  "- **Users:** the owner and two colleagues\n\n## Checklist\n\n- [x] Everything covered\n\n"
                  "## Change history\n\n| Version | Date | Change | Reason |\n|---|---|---|---|\n| 1.0 | 2026-10-21 | Created | Test |\n")

    def make_reviewable(self, doc_id="D0.01", extra=""):
        self.run_cli("scaffold", "--only", doc_id, expected=0)
        row = next(l for l in (self.root / "_control/registry/MANIFEST.md").read_text(encoding="utf-8").splitlines()
                   if l.startswith(f"| {doc_id} |"))
        rel = [c.strip() for c in row.strip("|").split("|")][1]
        path = self.root / "docs" / rel
        text = path.read_text(encoding="utf-8")
        front = text[: text.index("\n---\n", 4) + 5].replace('summary: ""', 'summary: "Test summary of what is decided."')
        title = re.search(r"^title: (.*)$", front, re.M).group(1)
        path.write_text(front + self.VALID_BODY.format(title=title) + extra, encoding="utf-8")
        self.run_cli("set-status", doc_id, "drafting", expected=0)
        self.run_cli("set-status", doc_id, "in-review", expected=0)
        return path

    def make_approved_architecture(self):
        vision_path = self.make_reviewable("D0.01")
        self.run_cli("approve", "D0.01", "--evidence", "owner approved vision for test", expected=0)
        self.run_cli("scaffold", "--only", "D0.02", expected=0)
        arch = self.root / "docs/00-overview/documentation-scope.md"
        text = arch.read_text(encoding="utf-8")
        front = text[: text.index("\n---\n", 4) + 5].replace('summary: ""', 'summary: "Test architecture accepted as a provisional structure."')
        headings = [
            "## Project profile and documentation drivers",
            "## Proposed document architecture",
            "## Document inventory and applicability",
            "## Phase and sequencing adaptations",
            "## Source-of-truth and dependency model",
            "## Diagrams and visual artifacts",
            "## Quality coverage map",
            "## Architecture evolution triggers",
            "## Owner review and current agreement",
        ]
        body = "\n\n".join(h + "\n\nThis section records the agreed test fixture content and its rationale." for h in headings)
        arch.write_text(front + "# Adaptive documentation architecture test fixture\n\n" + body + "\n", encoding="utf-8")
        self.run_cli("set-status", "D0.02", "drafting", expected=0)
        self.run_cli("set-status", "D0.02", "in-review", expected=0)
        self.run_cli("approve", "D0.02", "--evidence", "owner approved architecture for test", expected=0)
        return vision_path, arch

    def test_approval_fingerprint_binds_all_manifest_metadata_fields(self):
        spec = importlib.util.spec_from_file_location("blueprint_under_test", self.root / "_framework" / "tools" / "blueprint.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.set_workspace_paths(module.WorkspacePaths.from_root(self.root))
        text = ("---\n"
                "doc_id: D1.01\n"
                "title: Vision\n"
                "phase: 1\n"
                "status: approved\n"
                "maturity: outline\n"
                "version: 1.0\n"
                "last_updated: 2026-10-22\n"
                "depends_on: [D0.01]\n"
                "summary: Original summary\n"
                "applicability: active\n"
                "applicability_rationale: Not conditional\n"
                "profile_tier: standard\n"
                "---\n\n# Body\nStable body text.\n")
        base = {"id": "D1.01", "path": "01-discovery/vision.md", "title": "Vision",
                "phase": "1", "depends": ["D0.01"], "applicability": "active",
                "applicability_rationale": "Not conditional", "profile_tier": "standard"}
        original = module.approval_fingerprint(text, base)
        manifest_variants = {
            "id": "D1.02", "path": "01-discovery/renamed.md", "title": "Changed title",
            "phase": "2", "depends": ["D0.02"], "applicability": "deferred",
            "applicability_rationale": "Changed rationale", "profile_tier": "exhaustive",
        }
        for key, value in manifest_variants.items():
            with self.subTest(manifest_field=key):
                changed = dict(base)
                changed[key] = value
                self.assertNotEqual(original, module.approval_fingerprint(text, changed))

    def test_approval_fingerprint_binds_all_front_matter_metadata_fields(self):
        spec = importlib.util.spec_from_file_location("blueprint_under_test", self.root / "_framework" / "tools" / "blueprint.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.set_workspace_paths(module.WorkspacePaths.from_root(self.root))
        text = ("---\n"
                "doc_id: D1.01\n"
                "title: Vision\n"
                "phase: 1\n"
                "status: approved\n"
                "maturity: outline\n"
                "version: 1.0\n"
                "last_updated: 2026-10-22\n"
                "depends_on: [D0.01]\n"
                "summary: Original summary\n"
                "applicability: active\n"
                "applicability_rationale: Not conditional\n"
                "profile_tier: standard\n"
                "---\n\n# Body\nStable body text.\n")
        base = {"id": "D1.01", "path": "01-discovery/vision.md", "title": "Vision",
                "phase": "1", "depends": ["D0.01"], "applicability": "active",
                "applicability_rationale": "Not conditional", "profile_tier": "standard"}
        original = module.approval_fingerprint(text, base)
        variants = {
            "doc_id": "D1.02", "title": "Changed title", "phase": "2",
            "depends_on": "[D0.02]", "summary": "Changed summary",
            "applicability": "deferred", "applicability_rationale": "Changed rationale",
            "profile_tier": "exhaustive",
        }
        for field, value in variants.items():
            with self.subTest(front_matter_field=field):
                changed = re.sub(rf"^{re.escape(field)}:.*$", f"{field}: {value}", text, count=1, flags=re.M)
                self.assertNotEqual(original, module.approval_fingerprint(changed, base))

    def test_approve_records_evidence_hash_and_check_passes(self):
        self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "owner said: approved (test)", expected=0)
        approvals = (self.root / "_control/registry/APPROVALS.md").read_text(encoding="utf-8")
        self.assertIn("| D0.01 | 1.0 |", approvals)
        self.assertIn("owner said: approved (test)", approvals)
        self.run_cli("status", "--write", expected=0)
        self.run_cli("check", "--strict", expected=0)

    def test_approve_requires_in_review_and_evidence(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        self.assertEqual(self.run_cli("approve", "D0.01", "--evidence", "x").returncode, 2)  # not in review
        missing = self.run_cli("approve", "D0.01")
        self.assertNotEqual(missing.returncode, 0)  # --evidence is mandatory

    def test_approve_refuses_hollow_document(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        doc = self.root / "docs/00-overview/vision-capture.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace('summary: ""', 'summary: "x"'), encoding="utf-8")
        self.run_cli("set-status", "D0.01", "drafting", expected=0)
        self.run_cli("set-status", "D0.01", "in-review", expected=0)
        result = self.run_cli("approve", "D0.01", "--evidence", "test", expected=1)
        self.assertIn("empty section", result.stdout)
        self.assertIn("unfilled template prompt", result.stdout)
        self.assertIn("checklist item", result.stdout)
        self.assertEqual(len(re.findall(r"^\| D0\.01 \|", (self.root / "_control/registry/APPROVALS.md").read_text(encoding="utf-8"), re.M)), 0)

    def test_manual_approval_without_record_is_an_error(self):
        path = self.make_reviewable()
        self.replace_manifest_cell("D0.01", "Status", "approved")
        path.write_text(path.read_text(encoding="utf-8").replace("status: in-review", "status: approved", 1), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("approvals registry has no record", result.stdout)

    def test_editing_approved_content_is_detected_and_revision_cycle_bumps_version(self):
        path = self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        path.write_text(path.read_text(encoding="utf-8") + "\nSilent change.\n", encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("content changed after owner approval", result.stdout)
        path.write_text(path.read_text(encoding="utf-8").replace("\nSilent change.\n", ""), encoding="utf-8")
        self.run_cli("check", "--strict", expected=0)  # restoring the text restores validity
        self.run_cli("maturity", "D0.01", "working", expected=0)  # metadata edits don't break approval
        self.run_cli("check", "--strict", expected=0)
        self.run_cli("set-status", "D0.01", "needs-revision", "--reason", "scope changed", expected=0)
        path.write_text(path.read_text(encoding="utf-8") + "\nRevised sentence.\n", encoding="utf-8")
        self.run_cli("set-status", "D0.01", "drafting", expected=0)
        self.run_cli("set-status", "D0.01", "in-review", expected=0)
        out = self.run_cli("approve", "D0.01", "--evidence", "re-approved", expected=0)
        self.assertIn("1.1", out.stdout)
        self.run_cli("check", "--strict", expected=0)

    def test_approval_fingerprint_binds_summary_metadata_and_uses_full_sha256(self):
        path = self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        approvals = (self.root / "_control/registry/APPROVALS.md").read_text(encoding="utf-8")
        row = next(line for line in approvals.splitlines() if line.startswith("| D0.01 |"))
        digest = row.strip("|").split("|")[-1].strip()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace('summary: "Test summary of what is decided."',
                                         'summary: "Changed summary after approval."'), encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("approval-bearing metadata changed", result.stdout)

    def test_approval_fingerprint_binds_title_metadata_too(self):
        path = self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r"^title:.*$", "title: Revised title after approval", text, count=1, flags=re.M), encoding="utf-8")
        self.replace_manifest_cell("D0.01", "Title", "Revised title after approval")
        self.replace_catalog_cell("D0.01", "Title", "Revised title after approval")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("approval-bearing metadata changed", result.stdout)

    def test_last_updated_change_does_not_invalidate_approval_when_synced(self):
        path = self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r"^last_updated:.*$", "last_updated: 2026-10-23", text, count=1, flags=re.M), encoding="utf-8")
        self.replace_manifest_cell("D0.01", "Last updated", "2026-10-23")
        self.run_cli("check", "--strict", expected=0)

    def test_crlf_line_endings_do_not_invalidate_approval_fingerprint(self):
        path = self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.run_cli("check", "--strict", expected=0)

    def test_legacy_body_only_approval_hash_requires_reapproval(self):
        self.make_reviewable()
        self.run_cli("approve", "D0.01", "--evidence", "test", expected=0)
        path = self.root / "_control/registry/APPROVALS.md"
        content = path.read_text(encoding="utf-8")
        content = re.sub(r"(\| D0\.01 \| 1\.0 \|[^|]*\|[^|]*\|[^|]*\|) [0-9a-f]{64} (\|)", r"\1 abcdef123456 \2", content, count=1)
        path.write_text(content, encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("legacy body-only hash", result.stdout)

    def test_approved_document_is_invalid_when_active_upstream_is_no_longer_approved(self):
        self.make_approved_architecture()
        self.run_cli("set-status", "D0.01", "needs-revision", "--reason", "upstream vision materially changed", expected=0)
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("D0.02 is approved but depends on D0.01", result.stdout)

    def test_override_cannot_bypass_an_approved_architecture_with_unapproved_input(self):
        self.make_approved_architecture()
        self.run_cli("set-status", "D0.01", "needs-revision", "--reason", "upstream vision materially changed", expected=0)
        result = self.run_cli("scaffold", "--only", "D1.01", "--override-architecture-gate",
                              "--override-reason", "test-only override", expected=2)
        self.assertIn("Cannot override a broken approved architecture baseline", result.stdout)
        self.assertFalse((self.root / "docs/01-discovery/vision-and-problem.md").exists())

    def test_scaffold_blocks_when_approved_architecture_input_fingerprint_is_stale(self):
        vision, _arch = self.make_approved_architecture()
        content = vision.read_text(encoding="utf-8")
        vision.write_text(content.replace('summary: "Test summary of what is decided."',
                                          'summary: "Tampered approved vision summary."'), encoding="utf-8")
        result = self.run_cli("scaffold", "--only", "D1.01", expected=2)
        self.assertIn("input D0.01", result.stdout)
        self.assertIn("fingerprint mismatch", result.stdout)
        self.assertFalse((self.root / "docs/01-discovery/vision-and-problem.md").exists())

    def test_architecture_override_cannot_bypass_stale_approval_fingerprint(self):
        vision, _arch = self.make_approved_architecture()
        content = vision.read_text(encoding="utf-8")
        vision.write_text(content.replace('summary: "Test summary of what is decided."',
                                          'summary: "Tampered approved vision summary."'), encoding="utf-8")
        result = self.run_cli("scaffold", "--only", "D1.01", "--override-architecture-gate",
                              "--override-reason", "test-only override", expected=2)
        self.assertIn("cannot be bypassed", result.stdout)
        self.assertFalse((self.root / "docs/01-discovery/vision-and-problem.md").exists())

    def test_downstream_approval_blocks_on_stale_approved_ancestor(self):
        vision, _arch = self.make_approved_architecture()
        doc = self.make_reviewable("D1.01")
        content = vision.read_text(encoding="utf-8")
        vision.write_text(content.replace('summary: "Test summary of what is decided."',
                                          'summary: "Tampered approved vision summary."'), encoding="utf-8")
        result = self.run_cli("approve", "D1.01", "--evidence", "test", expected=1)
        self.assertIn("adaptive architecture gate", result.stdout)
        self.assertIn("fingerprint mismatch", result.stdout)

    def test_scaffold_rejects_approved_ancestor_status_or_version_front_matter_drift(self):
        vision, _arch = self.make_approved_architecture()
        original = vision.read_text(encoding="utf-8")
        mutations = [
            (r"^status:.*$", "status: drafting", "front-matter status"),
            (r"^version:.*$", "version: 9.9", "front-matter version"),
        ]
        for pattern, replacement, expected_message in mutations:
            with self.subTest(field=expected_message):
                changed = re.sub(pattern, replacement, original, count=1, flags=re.M)
                vision.write_text(changed, encoding="utf-8")
                result = self.run_cli("scaffold", "--only", "D1.01", expected=2)
                self.assertIn(expected_message, result.stdout)
                self.assertFalse((self.root / "docs/01-discovery/vision-and-problem.md").exists())
                vision.write_text(original, encoding="utf-8")

    def test_repeatable_family_can_expand_beyond_42_catalog_records(self):
        self.replace_manifest_cell("D5.03", "Status", "expanded")
        manifest = self.root / "_control/registry/MANIFEST.md"
        lines = manifest.read_text(encoding="utf-8").splitlines()
        insert_at = max(i for i, line in enumerate(lines) if line.startswith("| D")) + 1
        for n in range(1, 106):
            did = f"D5.03.{n:02d}"
            lines.insert(insert_at + n - 1,
                         f"| {did} | 05-design/components/component-{n:02d}.md | 5 | active | Generated repeatable component specification. | standard | M | not-started | D4.03 | Component {n:02d} specification | outline | 0.1 | 2026-10-22 |")
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.run_cli("status", "--profile", "standard", expected=0)
        total = int(re.search(r"\*\*All\*\* \| \| \*\*\d+ / (\d+)\*\*", result.stdout).group(1))
        self.assertGreater(total, 42)
        self.run_cli("check", "--strict", expected=0)

    def test_starter_profile_is_consistently_standard_and_counts_are_not_a_cap(self):
        config = json.loads((self.root / "_control/WORKSPACE.json").read_text(encoding="utf-8"))
        self.assertEqual(config["profile"], "standard")
        state = (self.root / "_control/STATE.md").read_text(encoding="utf-8")
        self.assertIn("**Standard**", state)
        self.run_cli("status", "--write", expected=0)
        self.run_cli("index", "--check", expected=0)
        self.assertIn("0 / 32", (self.root / "_control/STATE.md").read_text(encoding="utf-8"))
        config_doc = (self.root / "_framework/WORKSPACE-CONFIG.md").read_text(encoding="utf-8")
        self.assertIn("neither a document cap nor a mandatory generation target", config_doc)
        self.assertIn("Repeatable families", config_doc)

    def test_set_status_blocks_direct_approval_and_illegal_transitions(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        self.assertEqual(self.run_cli("set-status", "D0.01", "approved").returncode, 2)
        self.assertEqual(self.run_cli("set-status", "D0.01", "in-review").returncode, 2)  # skips drafting
        self.assertEqual(self.run_cli("set-status", "D0.01", "needs-revision", "--reason", "x").returncode, 2)
        self.run_cli("set-status", "D0.01", "drafting", expected=0)
        front = (self.root / "docs/00-overview/vision-capture.md").read_text(encoding="utf-8")
        self.assertIn("status: drafting", front)
        self.assertIn("| drafting |", self.manifest_row("D0.01"))

    def test_gate_message_names_the_real_blocker(self):
        self.make_reviewable("D0.01")
        self.make_reviewable("D0.02")
        result = self.run_cli("scaffold", "--phase", "1", expected=2)
        self.assertIn("D0.02 has status 'in-review'", result.stdout)

    def test_profiles_are_meaningfully_different(self):
        def total(profile):
            out = self.run_cli("status", "--profile", profile, expected=0).stdout
            return int(re.search(r"\*\*All\*\* \| \| \*\*\d+ / (\d+)\*\*", out).group(1))
        lite, standard, exhaustive = total("lite"), total("standard"), total("exhaustive")
        self.assertLessEqual(lite, 18)
        self.assertGreater(standard, lite + 8)
        self.assertGreater(exhaustive, standard + 5)
        for profile in ("lite", "standard", "exhaustive"):
            self.run_cli("check", "--strict", "--profile", profile, expected=0)

    def test_index_is_generated_and_staleness_detected(self):
        self.run_cli("index", "--check", expected=0)
        self.replace_manifest_cell("D0.01", "Status", "drafting")  # unsynced manual edit makes the index stale
        self.run_cli("index", "--check", expected=1)
        self.run_cli("index", expected=0)
        index = (self.root / "_control/registry/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| D0.01 |", index)
        self.assertIn("Generated file", index)

    def test_index_shows_summaries_and_defined_ids(self):
        self.make_reviewable("D0.01", extra="\n## Goals\n\n| ID | Goal |\n|---|---|\n| G-001 | First goal |\n| G-002 | Second goal |\n")
        self.run_cli("index", expected=0)
        index = (self.root / "_control/registry/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("Test summary of what is decided.", index)
        self.assertIn("G-001…002 (2)", index)

    def test_starter_workspace_is_clean_of_framework_history(self):
        self.assertFalse(list((self.root / "_control/logs/sessions").glob("session-*.md")))
        self.assertNotIn("| Q-", (self.root / "_control/registry/QUESTIONS.md").read_text(encoding="utf-8"))
        self.assertEqual(len(re.findall(r"^\| D\d", (self.root / "_control/registry/APPROVALS.md").read_text(encoding="utf-8"), re.M)), 0)
        self.assertFalse((self.root / "INTEGRATION-REVIEW.md").exists())
        out = self.run_cli("check", "--gate", "0")
        self.assertNotIn("open question", out.stdout)
        self.assertIn("session-001-", self.run_cli("session", expected=0).stdout)

    def test_framework_dev_folder_is_ignored_by_project_checks(self):
        (self.root / "framework-dev").mkdir(exist_ok=True)
        (self.root / "framework-dev/NOTES.md").write_text("[broken](missing.md) FR-999 [unfilled template prompt here]\n", encoding="utf-8")
        self.run_cli("check", "--strict", expected=0)

    def test_scaffold_keeps_manifest_date_in_sync_with_new_files(self):
        self.run_cli("scaffold", "--only", "D0.01,D0.02", expected=0)
        self.run_cli("check", "--strict", expected=0)

    def test_lint_flags_bare_tbd_and_empty_fields_in_review(self):
        self.make_reviewable(extra="\n## Owner\n\n- **Owner:**\n- Decision: TBD\n")
        result = self.run_cli("check", "--strict", expected=0)
        self.assertIn("empty field", result.stdout)
        self.assertIn("untagged 'TBD'", result.stdout)
        self.run_cli("approve", "D0.01", "--evidence", "x", expected=1)


class ReleaseReadinessTests(BlueprintTestCase):
    """v2.3.3 regression tests for lint precision, compatibility, readiness, and release drift."""

    VALID_BODY = ApprovalLintIndexTests.VALID_BODY

    def make_reviewable(self, doc_id="D0.01", extra=""):
        return ApprovalLintIndexTests.make_reviewable(self, doc_id, extra)

    def load_blueprint_module(self):
        spec = importlib.util.spec_from_file_location("blueprint_under_test", self.root / "_framework" / "tools" / "blueprint.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.set_workspace_paths(module.WorkspacePaths.from_root(self.root))
        return module

    def read_events(self):
        path = self.root / "_control/logs/status-transitions.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_explicit_fill_markers_trigger_tpl001_but_natural_brackets_do_not(self):
        module = self.load_blueprint_module()
        natural = """# Example

A source is [Source: Acme pricing page], and the reader moves to [the next section].
Inline `[[FILL: this is code documentation]]` is literal.
\\[[FILL: this is an escaped literal marker]]
<!-- [[FILL: comment-only marker]] -->
"""
        natural_findings = module.lint_document(natural, "approved")
        self.assertFalse(any("TPL001" in message for _, message in natural_findings), natural_findings)
        actual = module.lint_document("# Example\n\n[[FILL: Describe the actual behavior.]]\n", "approved")
        self.assertTrue(any("TPL001" in message for _, message in actual), actual)

    def test_each_shipped_template_has_explicit_marker_and_fails_approval_lint(self):
        module = self.load_blueprint_module()
        templates = sorted((self.root / "_framework/templates").glob("*.md"))
        self.assertGreaterEqual(len(templates), 10)
        for template in templates:
            with self.subTest(template=template.name):
                raw = template.read_text(encoding="utf-8")
                self.assertIn("[[FILL:", raw, f"{template.name} needs an explicit prompt marker")
                findings = module.lint_document(raw, "approved")
                self.assertTrue(any("TPL001" in message for _, message in findings),
                                f"Unedited template did not fail TPL001: {template.name}; findings={findings}")

    def test_inline_code_and_escaped_fill_marker_are_ignored(self):
        module = self.load_blueprint_module()
        samples = [
            "`[[FILL: shown literally in code]]`",
            "``[[FILL: shown literally in a double-backtick span]]``",
            r"\[[FILL: escaped literal marker]]",
            "<!-- [[FILL: inside an HTML comment]] -->",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                markers, issues = module.find_fill_markers(sample)
                self.assertEqual([], markers)
                self.assertEqual([], issues)

    def test_inline_ignore_line_suppresses_only_tpl_marker_with_reason(self):
        module = self.load_blueprint_module()
        raw = "Literal `[[FILL: marker example]]` [[FILL: literal display]] <!-- blueprint-lint: ignore-line -- reason: this line documents marker syntax -->"
        markers, issues = module.find_fill_markers(raw)
        self.assertEqual([], markers)
        self.assertEqual([], issues)

    def test_ignore_next_line_uses_immediate_physical_line(self):
        module = self.load_blueprint_module()
        raw = "<!-- blueprint-lint: ignore-next-line -- reason: next line is a literal marker -->\n[[FILL: literal display]]"
        markers, issues = module.find_fill_markers(raw)
        self.assertEqual([], markers)
        self.assertEqual([], issues)

    def test_bad_or_stale_lint_suppressions_are_reported(self):
        module = self.load_blueprint_module()
        malformed = "<!-- blueprint-lint: ignore-next-line -->\n[[FILL: literal display]]"
        _, issues = module.find_fill_markers(malformed)
        self.assertTrue(any("reason" in issue.lower() for _, issue in issues), issues)
        stale = "<!-- blueprint-lint: ignore-next-line -- reason: marker was removed already -->\nOrdinary prose."
        _, issues = module.find_fill_markers(stale)
        self.assertTrue(any("did not target" in issue for _, issue in issues), issues)
        bad_token = "<!-- blueprint-lint: disable-all -- reason: not a supported directive -->"
        _, issues = module.find_fill_markers(bad_token)
        self.assertTrue(any("unrecognized" in issue for _, issue in issues), issues)

    def test_every_lint_rule_has_a_documented_catalog_entry(self):
        module = self.load_blueprint_module()
        docs = (self.root / "_framework/LINT-RULES.md").read_text(encoding="utf-8")
        for rule_id in module.LINT_RULES:
            with self.subTest(rule_id=rule_id):
                self.assertRegex(docs, rf"(?m)^\|\s*`{re.escape(rule_id)}`\s*\|")

    def test_guide_version_and_command_inventory_match_the_cli(self):
        version = (self.root / "_framework/FRAMEWORK-MANIFEST.json").read_text(encoding="utf-8")
        version = json.loads(version)["framework_version"]
        guide = (self.root / "_framework/GUIDE.md").read_text(encoding="utf-8")
        self.assertRegex(guide, rf'(?m)^framework_version:\s*"{re.escape(version)}"$')
        cli_version = self.run_cli("--version", expected=0).stdout.strip()
        self.assertEqual(f"Project Blueprint Framework {version}", cli_version)
        self.assertIn("_framework/GUIDE.md", (self.root / "README.md").read_text(encoding="utf-8"))
        self.assertIn("framework-managed", (self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertRegex((self.root / "_control/STATE.md").read_text(encoding="utf-8"), r"(?m)^\| Framework version \| See `_framework/FRAMEWORK-MANIFEST\.json` \|")
        changelog = (SOURCE_ROOT / "framework-dev/CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {version} —", changelog)
        help_text = self.run_cli("--help", expected=0).stdout
        match = re.search(r"\{([^}]+)\}", help_text)
        self.assertIsNotNone(match, help_text)
        actual_commands = {x.strip() for x in match.group(1).split(",")}
        marked = re.search(r"<!-- blueprint-cli-commands:start -->(.*?)<!-- blueprint-cli-commands:end -->", guide, re.S)
        self.assertIsNotNone(marked, "Guide command table needs drift-check markers")
        documented_commands = set(re.findall(r"(?m)^\|\s*`([a-z-]+)`\s*\|", marked.group(1)))
        self.assertEqual(actual_commands, documented_commands)
        check_help = self.run_cli("check", "--help", expected=0).stdout
        self.assertIn("--readiness", check_help)
        check_row = next(line for line in marked.group(1).splitlines() if line.startswith("| `check` |"))
        self.assertIn("--readiness", check_row)

    def test_guide_starter_catalog_inventory_matches_manifest(self):
        guide = (self.root / "_framework/GUIDE.md").read_text(encoding="utf-8")
        manifest_lines = (self.root / "_control/registry/MANIFEST.md").read_text(encoding="utf-8").splitlines()
        header_index = next(i for i, line in enumerate(manifest_lines) if line.startswith("| Doc ID |"))
        headers = [cell.strip() for cell in manifest_lines[header_index].strip("|").split("|")]
        rows = {}
        for line in manifest_lines[header_index + 1:]:
            if not line.startswith("| D"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == len(headers):
                row = dict(zip(headers, cells))
                rows[row["Doc ID"]] = row

        def guide_records(section_start, section_end):
            start = guide.index(section_start)
            end = guide.index(section_end, start)
            records = {}
            for line in guide[start:end].splitlines():
                match = re.match(r"^\|\s*`(D[0-9]+\.[0-9]+(?:\.[0-9]+)*)`\s*\|", line)
                if not match:
                    continue
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                records[match.group(1)] = {
                    "title": cells[1],
                    "path": cells[2].strip("`"),
                    "tier": cells[3].lower(),
                }
            return records

        active = guide_records("### 6.1 The 42 active records", "### 6.2 The 16 conditional records")
        conditional = guide_records("### 6.2 The 16 conditional records", "### 6.3 Structural tailoring decisions")
        self.assertEqual(42, len(active), "Starter active inventory changed; review guide/catalog counts")
        self.assertEqual(16, len(conditional), "Starter conditional inventory changed; review guide/catalog counts")
        expected_active = {doc_id for doc_id, row in rows.items() if row["Applicability"] == "active"}
        expected_conditional = {doc_id for doc_id, row in rows.items() if row["Applicability"] == "conditional"}
        self.assertEqual(expected_active, set(active))
        self.assertEqual(expected_conditional, set(conditional))
        for doc_id, record in {**active, **conditional}.items():
            with self.subTest(doc_id=doc_id):
                manifest = rows[doc_id]
                self.assertEqual(manifest["Title"], record["title"])
                self.assertEqual(manifest["Path"], record["path"])
                self.assertEqual(manifest["Profile tier"], record["tier"])


    def test_v232_approval_fingerprint_golden_is_unchanged(self):
        module = self.load_blueprint_module()
        fixture = json.loads((SOURCE_ROOT / "framework-dev/tests/fixtures/v2.3.2-fingerprint-golden.json").read_text(encoding="utf-8"))
        actual = module.approval_fingerprint(fixture["document_text"], fixture["manifest_document"])
        self.assertEqual(fixture["expected_sha256"], actual)
        self.assertEqual("2.3.2", fixture["source_release"])

    def test_manifest_tiers_and_profile_config_match_v232_snapshot(self):
        snapshot = json.loads((SOURCE_ROOT / "framework-dev/tests/fixtures/v2.3.2-profile-snapshot.json").read_text(encoding="utf-8"))
        lines = (self.root / "_control/registry/MANIFEST.md").read_text(encoding="utf-8").splitlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("| Doc ID |"))
        headers = [c.strip() for c in lines[header_idx].strip("|").split("|")]
        current = {}
        for line in lines[header_idx + 1:]:
            if line.startswith("| D"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) == len(headers):
                    row = dict(zip(headers, cells))
                    current[row["Doc ID"]] = {"profile_tier": row["Profile tier"], "depends_on": row["Depends on"]}
        self.assertEqual(snapshot["manifest_docs"], current)
        config = json.loads((self.root / "_control/WORKSPACE.json").read_text(encoding="utf-8"))
        defaults = json.loads((self.root / "_framework/defaults/workspace-defaults.json").read_text(encoding="utf-8"))
        actual_cfg = {
            "architecture_document_id": defaults["architecture_document_id"],
            "bootstrap_doc_ids": defaults["bootstrap_doc_ids"],
            "id_index_document_ids": defaults["id_index_document_ids"],
            "profile": config["profile"],
            "profile_policy": defaults["profile_policy"],
            "profile_ranks": defaults["profile_ranks"],
            "vision_document_id": defaults["vision_document_id"],
        }
        self.assertEqual(snapshot["workspace_config"], actual_cfg)

    def test_check_readiness_reports_unedited_draft_without_changing_exit_code(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        self.run_cli("set-status", "D0.01", "drafting", expected=0)
        strict = self.run_cli("check", "--strict", expected=0)
        self.assertIn("0 error(s)", strict.stdout)
        advisory = self.run_cli("check", "--readiness", expected=0)
        self.assertIn("DRAFT READINESS", advisory.stdout)
        self.assertIn("READINESS D0.01 [drafting]", advisory.stdout)
        combined = self.run_cli("check", "--strict", "--readiness", expected=0)
        self.assertIn("READINESS D0.01 [drafting]", combined.stdout)
        self.assertIn("advisory", combined.stdout.lower())

    def test_readiness_scopes_to_active_in_profile_drafting_statuses(self):
        self.run_cli("scaffold", "--only", "D0.01,D0.02", expected=0)
        self.run_cli("set-status", "D0.01", "drafting", expected=0)
        self.run_cli("set-status", "D0.02", "drafting", expected=0)
        out = self.run_cli("check", "--readiness", "--profile", "lite", expected=0).stdout
        self.assertIn("READINESS D0.01", out)
        # D0.02 remains active and Lite-eligible, so both should be included.
        self.assertIn("READINESS D0.02", out)

    def test_dedicated_signoff_template_and_traceability_fields_are_mapped(self):
        catalog = (self.root / "_framework/DOC-CATALOG.md").read_text(encoding="utf-8")
        self.assertRegex(catalog, r"(?m)^\| D8\.02 \|[^\n]*\| planning-baseline-signoff \|")
        template = self.root / "_framework/templates/planning-baseline-signoff.md"
        self.assertTrue(template.exists())
        self.assertIn("Lite", template.read_text(encoding="utf-8"))
        self.run_cli("scaffold", "--only", "D8.02", "--override-architecture-gate", "--override-reason", "Verify mapped D8.02 template", expected=0)
        scaffolded = (self.root / "docs/08-acceptance/planning-baseline-signoff.md").read_text(encoding="utf-8")
        self.assertIn("## Profile-specific quality evidence", scaffolded)
        self.assertIn("## Traceability and coherence review record", scaffolded)
        self.assertNotIn("{{CHECKLIST}}", scaffolded)
        req = (self.root / "_framework/templates/requirement.md").read_text(encoding="utf-8")
        comp = (self.root / "_framework/templates/component-spec.md").read_text(encoding="utf-8")
        for field in ("Goals (G-)", "Use cases (UC-)", "Design component/interface (CMP-/API-)", "Acceptance tests (TC-)"):
            self.assertIn(f"**{field}:**", req)
        self.assertIn("**Verification (TC-):**", comp)
        catalog_row = next(line for line in catalog.splitlines() if line.startswith("| D0.01 |"))
        self.assertIn("Target audience, user and actor types, and context", catalog_row)
        d204 = next(line for line in catalog.splitlines() if line.startswith("| D2.04 |"))
        self.assertIn("_framework/templates/requirement.md", d204)
        manifest_line = self.manifest_row("D8.02")
        self.assertIn("| D8.02 |", manifest_line)
        self.assertIn("| D7.05 |", manifest_line)
        self.assertNotIn("D8.01", manifest_line)

    def test_requirement_traceability_field_format_uses_existing_fld001(self):
        module = self.load_blueprint_module()
        raw = "# Requirement\n\n## Traceability\n- **Goals (G-):**\n- **Use cases (UC-):** FR-001\n"
        findings = module.lint_document(raw, "in-review")
        fld = [message for severity, message in findings if "FLD001" in message]
        self.assertEqual(1, len(fld), findings)
        self.assertIn("Goals (G-)", fld[0])
        completed = raw.replace("- **Goals (G-):**", "- **Goals (G-):** G-001")
        findings = module.lint_document(completed, "in-review")
        self.assertFalse(any("FLD001" in message for _, message in findings), findings)

    def test_profile_traceability_gate_timing_reserves_final_audits_for_g8(self):
        gates = (self.root / "_framework/QUALITY-GATES.md").read_text(encoding="utf-8")
        g7 = gates.split("### G7 — Delivery planning", 1)[1].split("### G8 — Coherence and sign-off", 1)[0]
        g8 = gates.split("### G8 — Coherence and sign-off", 1)[1]
        self.assertIn("final manual traceability audit at G8", g7)
        self.assertIn("Track gaps for the D8.01 coherence/coverage audit at G8", g7)
        self.assertNotIn("D8.02 records a manual", g7)
        self.assertIn("Lite records the manual audit in D8.02", g8)
        self.assertIn("Standard completes D8.01", g8)
        self.assertIn("Exhaustive reconciles D7.04", g8)
        plan = (self.root / "_framework/WORKFLOW-PLAN.md").read_text(encoding="utf-8")
        plan_g7 = plan.split("**Gate G7:**", 1)[1].split("### P8", 1)[0]
        self.assertIn("G7 does not require future-phase audit/sign-off documents", plan_g7)

    def test_live_policy_docs_do_not_use_legacy_placeholder_convention(self):
        live_docs = ["_framework/QUALITY-GATES.md", "_framework/LINT-RULES.md", "_framework/WORKFLOW-PLAN.md", "AGENTS.md"]
        legacy = re.compile(r"(?<!\\)\[\s*…\s*\]")
        for rel in live_docs:
            with self.subTest(path=rel):
                self.assertIsNone(legacy.search((self.root / rel).read_text(encoding="utf-8")), rel)

    def test_lint_rules_suppression_example_is_self_consistent(self):
        module = self.load_blueprint_module()
        rules = (self.root / "_framework/LINT-RULES.md").read_text(encoding="utf-8")
        row = next(line for line in rules.splitlines() if "| Example syntax |" in line)
        markers, issues = module.find_fill_markers(row)
        self.assertEqual([], markers, "The documented example directive should suppress its literal marker")
        self.assertEqual([], issues, "The documented example must not contain a stale/malformed directive")

    def test_readme_is_owner_entry_point_without_duplicate_quickstart_or_approval_doc(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("_framework/GUIDE.md", readme)
        self.assertIn("AGENTS.md", readme)
        self.assertIn("WINDOWS-USAGE.md", readme)
        self.assertFalse((self.root / "QUICKSTART.md").exists())
        self.assertFalse((self.root / "_framework/APPROVAL-PROTOCOL.md").exists())
        protocols = (self.root / "_framework/PROTOCOLS.md").read_text(encoding="utf-8")
        self.assertIn("### 5.7 Approve", protocols)

    def test_status_transition_reason_is_persisted_and_approval_is_logged(self):
        # Include a README-like decoy and a real numbered session; the actor context must use the latter.
        sessions = self.root / "_control/logs/sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "README.md").write_text("Not a session handoff.\n", encoding="utf-8")
        (sessions / "session-004-2026-10-23.md").write_text("# Real handoff\n", encoding="utf-8")
        self.make_reviewable("D0.01")
        self.run_cli("approve", "D0.01", "--evidence",
                     "Owner explicitly approved D0.01 during session-004-2026-10-23.md review", expected=0)
        self.run_cli("set-status", "D0.01", "needs-revision", "--reason",
                     "Owner requested a revision after reviewing updated scope", expected=0)
        events = self.read_events()
        status_events = [e for e in events if e["event_type"] == "status_transition" and e.get("document_id") == "D0.01"]
        self.assertTrue(status_events)
        self.assertEqual("Owner requested a revision after reviewing updated scope", status_events[-1]["reason"])
        approval = next(e for e in events if e["event_type"] == "approval" and e.get("document_id") == "D0.01")
        self.assertEqual("in-review", approval["from_status"])
        self.assertEqual("approved", approval["to_status"])
        self.assertEqual("session-004-2026-10-23", approval["session_id"])
        self.run_cli("check", "--strict", expected=0)

    def test_mutation_events_cover_scaffold_applicability_maturity_profile_and_override(self):
        self.run_cli("scaffold", "--only", "D0.01", expected=0)
        self.run_cli("set-status", "D0.01", "drafting", "--reason", "Initial draft started", expected=0)
        self.run_cli("maturity", "D0.01", "working", "--reason", "Core structure now exists", expected=0)
        self.run_cli("applicability", "D1.05", "active", "--reason", "Product discovery requires competitive research", expected=0)
        self.run_cli("profile", "lite", "--reason", "Initial scope limited to minimum viable documentation", expected=0)
        self.run_cli("scaffold", "--only", "D1.03", "--override-architecture-gate", "--override-reason",
                     "Test override to verify event logging", expected=0)
        events = self.read_events()
        types = {e["event_type"] for e in events}
        self.assertTrue({"scaffold", "status_transition", "maturity_change", "applicability_change", "profile_change", "architecture_override"}.issubset(types), types)
        self.run_cli("check", "--strict", expected=0)

    def test_check_rejects_invalid_jsonl_event_record(self):
        path = self.root / "_control/logs/status-transitions.jsonl"
        path.write_text('{"event_type":\n', encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=1)
        self.assertIn("invalid JSON", result.stdout)

    def test_check_warns_when_last_logged_status_differs_from_manifest(self):
        self.make_reviewable("D0.01")
        self.replace_manifest_cell("D0.01", "Status", "drafting")
        doc_path = self.root / "docs/00-overview/vision-capture.md"
        content = doc_path.read_text(encoding="utf-8")
        content = re.sub(r"(?m)^status:.*$", "status: drafting", content, count=1)
        doc_path.write_text(content, encoding="utf-8")
        result = self.run_cli("check", "--strict", expected=0)
        self.assertIn("last logged status for D0.01", result.stdout)
        self.assertIn("warning", result.stdout.lower())

    def test_weak_approval_evidence_is_warned_but_not_misrepresented_as_authenticated(self):
        self.make_reviewable("D0.01")
        result = self.run_cli("approve", "D0.01", "--evidence", "x", expected=0)
        self.assertIn("evidence is very short", result.stdout)
        self.assertIn("no session reference", result.stdout)

    def test_approval_is_not_recorded_when_front_matter_sync_fails(self):
        from argparse import Namespace
        from unittest.mock import patch

        self.make_reviewable("D0.01")
        module = self.load_blueprint_module()
        args = Namespace(
            doc_id="D0.01",
            evidence="Owner explicitly approved D0.01 during session-004-2026-10-23.md review",
            by="test-owner",
        )
        with patch.object(module, "update_front_matter_fields", return_value=False):
            code = module.cmd_approve(args)
        self.assertEqual(2, code)
        current_doc = next(d for d in module.load_manifest() if d["id"] == "D0.01")
        self.assertEqual("in-review", current_doc["status"], "failed approval must not leave a false approved manifest status")
        output = (self.root / "_control/registry/APPROVALS.md").read_text(encoding="utf-8")
        self.assertNotRegex(output, r"(?m)^\| D0\.01 \|")
        events = self.read_events()
        self.assertFalse(any(e.get("event_type") == "approval" and e.get("document_id") == "D0.01" for e in events))



if __name__ == "__main__":
    unittest.main(verbosity=2)
