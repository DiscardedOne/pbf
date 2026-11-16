"""Current integrity and state-audit contract tests: approved architecture, dependency applicability and read-only state audit."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
import subprocess
import hashlib
import datetime
import json
import zipfile
from unittest.mock import patch

SOURCE_ROOT = Path(__file__).resolve().parents[2]
TOOLS = SOURCE_ROOT / "_framework" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import blueprint  # noqa: E402
from workspace_fixture import create_workspace  # noqa: E402


class ArchitectureConformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bp-p5-arch-")
        self.root = Path(self.temp.name)
        self.doc = self.root / "D0.02.md"
        self.doc.write_text("""---
doc_id: D0.02
title: Architecture
phase: 0
status: approved
maturity: detailed
version: 1.0
last_updated: 2026-11-10
depends_on: []
summary: Accepted project architecture.
applicability: active
profile_tier: standard
---
# Architecture

| Catalog item / concern | Disposition (core / conditional / merged / split / new / excluded) | Proposed canonical document(s) | Rationale / activation trigger | Decision status |
|---|---|---|---|---|
| Vision | Core | D0.01 | Needed | Accepted |
| Documentation architecture | Core | D0.02 | Defines structure | Accepted |
| Optional audit | Conditional | D6.01 | Triggered later | Accepted |
| Old module | Merged | D4.01 → D4.02 | Covered by host | Accepted |
| Retired item | Excluded | D5.01 | Not applicable | Accepted |
| Delayed work | Deferred | D7.01 | Later phase | Accepted |
""", encoding="utf-8")
        self.ws = SimpleNamespace(docs=self.root, resolve_document=lambda rel: self.root / rel)

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, docs):
        by_id = {d["id"]: d for d in docs}
        with patch.object(blueprint, "workspace_paths", return_value=self.ws), \
             patch.object(blueprint, "load_workspace_config", return_value={"architecture_document_id": "D0.02"}), \
             patch.object(blueprint, "approval_problem", return_value=None), \
             patch.object(blueprint, "load_approvals", return_value={}):
            return blueprint.architecture_disposition_findings(docs, by_id)

    def _doc(self, did, applicability, rationale=""):
        return {"id": did, "path": did + ".md", "status": "approved", "version": "1.0",
                "applicability": applicability, "applicability_rationale": rationale}

    def test_approved_architecture_detects_core_manifest_mismatch(self):
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "conditional", "optional"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "Merged into D4.02"), self._doc("D4.02", "active"),
                self._doc("D5.01", "excluded", "not used"), self._doc("D7.01", "deferred", "later")]
        errors, _ = self._run(docs)
        self.assertTrue(any("D0.01 is 'core'" in x and "expected 'active'" in x for x in errors))

    def test_merged_requires_excluded_and_host_rationale(self):
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "merged elsewhere"), self._doc("D4.02", "active"),
                self._doc("D5.01", "excluded", "not used"), self._doc("D7.01", "deferred", "later")]
        errors, _ = self._run(docs)
        self.assertTrue(any("merged document D4.01 must identify its host" in x for x in errors))

    def test_unapproved_architecture_is_advisory_and_not_blocking(self):
        text = self.doc.read_text(encoding="utf-8").replace("status: approved", "status: in-review")
        self.doc.write_text(text, encoding="utf-8")
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "conditional", "optional")]
        docs[0]["status"] = "in-review"
        errors, warnings = self._run(docs)
        self.assertEqual([], errors)
        self.assertTrue(any("not approved" in x for x in warnings))

    def test_all_supported_dispositions_and_excluded_without_canonical_file(self):
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "trigger later"),
                self._doc("D4.01", "excluded", "Merged into D4.02"), self._doc("D4.02", "active"),
                self._doc("D7.01", "deferred", "later")]
        text = self.doc.read_text(encoding="utf-8").replace(
            "| Retired item | Excluded | D5.01 | Not applicable | Accepted |",
            "| Retired item | Excluded | — | Not applicable | Accepted |")
        self.doc.write_text(text, encoding="utf-8")
        errors, warnings = self._run(docs)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_repeated_same_disposition_reference_is_allowed_but_conflict_is_not(self):
        text = self.doc.read_text(encoding="utf-8").replace(
            "| Optional audit | Conditional | D6.01 | Triggered later | Accepted |",
            "| Optional audit | Conditional | D6.01 | Triggered later | Accepted |\n| Another concern | Conditional | D6.01 | Same canonical document | Accepted |")
        self.doc.write_text(text, encoding="utf-8")
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "Merged into D4.02"),
                self._doc("D4.02", "active"), self._doc("D5.01", "excluded", "not used"), self._doc("D7.01", "deferred", "later")]
        errors, _ = self._run(docs)
        self.assertFalse(any("appears more than once" in x for x in errors))
        self.doc.write_text(text.replace("| Another concern | Conditional |", "| Another concern | Core |"), encoding="utf-8")
        errors, _ = self._run(docs)
        self.assertTrue(any("conflicting dispositions" in x for x in errors))

    def test_new_requires_explicit_valid_manifest_applicability(self):
        text = self.doc.read_text(encoding="utf-8").replace(
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |",
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |\n"
            "| New module | New | D9.01 | Added module | Accepted |")
        self.doc.write_text(text, encoding="utf-8")
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "Merged into D4.02"),
                self._doc("D4.02", "active"), self._doc("D5.01", "excluded", "not used"),
                self._doc("D7.01", "deferred", "later"), self._doc("D9.01", "active")]
        errors, _ = self._run(docs)
        self.assertEqual([], errors)
        docs[-1]["applicability"] = ""
        errors, _ = self._run(docs)
        self.assertTrue(any("new document D9.01 requires an explicit valid manifest applicability" in x for x in errors))

    def test_split_requires_directional_original_to_two_children_mapping(self):
        text = self.doc.read_text(encoding="utf-8").replace(
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |",
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |\n"
            "| Split module | Split | D8.01, D8.01.01, D8.01.02 | Reorganized | Accepted |")
        self.doc.write_text(text, encoding="utf-8")
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "Merged into D4.02"),
                self._doc("D4.02", "active"), self._doc("D5.01", "excluded", "not used"),
                self._doc("D7.01", "deferred", "later"), self._doc("D8.01", "excluded", "Replaced by child documents"),
                self._doc("D8.01.01", "active"), self._doc("D8.01.02", "conditional", "later trigger")]
        errors, _ = self._run(docs)
        self.assertTrue(any("explicit directional mapping" in x for x in errors))

    def test_split_accepts_explicit_original_to_children_mapping(self):
        text = self.doc.read_text(encoding="utf-8").replace(
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |",
            "| Delayed work | Deferred | D7.01 | Later phase | Accepted |\n"
            "| Split module | Split | D8.01 → D8.01.01, D8.01.02 | Reorganized | Accepted |")
        self.doc.write_text(text, encoding="utf-8")
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active"),
                self._doc("D6.01", "conditional", "later"), self._doc("D4.01", "excluded", "Merged into D4.02"),
                self._doc("D4.02", "active"), self._doc("D5.01", "excluded", "not used"),
                self._doc("D7.01", "deferred", "later"), self._doc("D8.01", "excluded", "Replaced by child documents"),
                self._doc("D8.01.01", "active"), self._doc("D8.01.02", "conditional", "later trigger")]
        errors, warnings = self._run(docs)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_missing_architecture_document_id_is_detected(self):
        docs = [self._doc("D0.02", "active"), self._doc("D0.01", "active")]
        errors, _ = self._run(docs)
        self.assertTrue(any("missing from MANIFEST.md" in x for x in errors))


class DependencyApplicabilityTests(unittest.TestCase):
    def test_active_consumer_cannot_depend_on_conditional_deferred_or_excluded(self):
        docs = [
            {"id": "D1.01", "applicability": "active", "depends": ["D1.02", "D1.03", "D1.04"]},
            {"id": "D1.02", "applicability": "conditional", "depends": []},
            {"id": "D1.03", "applicability": "deferred", "depends": []},
            {"id": "D1.04", "applicability": "excluded", "depends": []},
        ]
        findings = blueprint.dependency_applicability_findings(docs, {d["id"]: d for d in docs})
        self.assertEqual(3, len(findings))

    def test_non_active_consumers_may_retain_planning_references(self):
        docs = [
            {"id": "D1.01", "applicability": "conditional", "depends": ["D1.02"]},
            {"id": "D1.02", "applicability": "excluded", "depends": []},
        ]
        self.assertEqual([], blueprint.dependency_applicability_findings(docs, {d["id"]: d for d in docs}))

    def test_active_to_active_dependency_is_valid(self):
        docs = [
            {"id": "D1.01", "applicability": "active", "depends": ["D1.02"]},
            {"id": "D1.02", "applicability": "active", "depends": []},
        ]
        self.assertEqual([], blueprint.dependency_applicability_findings(docs, {d["id"]: d for d in docs}))


class StateAuditTests(unittest.TestCase):
    def test_state_audit_is_read_only_and_detects_explicit_stale_claims(self):
        with tempfile.TemporaryDirectory(prefix="bp-p5-state-") as temp:
            root = Path(temp)
            control, logs, registry, docs_dir = root / "_control", root / "_control/logs", root / "_control/registry", root / "docs"
            logs.mkdir(parents=True); registry.mkdir(parents=True); docs_dir.mkdir()
            state = control / "STATE.md"
            state.write_text("# State\n\n| Field | Value |\n|---|---|\n| Current document | D0.02 — Architecture v1.0 |\n| Latest handoff | session-001 |\n| Last updated | session-001 |\n\n## Key decisions\n- (none yet)\n", encoding="utf-8")
            (logs / "session-001.md").write_text("# Session 001\n", encoding="utf-8")
            (logs / "session-002.md").write_text("# Session 002\n", encoding="utf-8")
            (registry / "DECISIONS.md").write_text("| ID | Title | Status |\n|---|---|---|\n| ADR-001 | Accepted decision | accepted |\n", encoding="utf-8")
            (registry / "APPROVALS.md").write_text("| Doc ID | Version | Date | Approved by | Evidence | Content hash |\n|---|---|---|---|---|---|\n", encoding="utf-8")
            (docs_dir / "D0.02.md").write_text("---\ndoc_id: D0.02\ntitle: Architecture\nphase: 0\nstatus: in-review\nversion: 1.1\nlast_updated: 2026-11-10\ndepends_on: []\nsummary: Current architecture\napplicability: active\nprofile_tier: standard\n---\n# Architecture\n", encoding="utf-8")
            paths = SimpleNamespace(state=state, logs=control / "_control/logs", sessions=logs, decisions=registry / "DECISIONS.md", approvals=registry / "APPROVALS.md", docs=docs_dir, resolve_document=lambda rel: docs_dir / rel)
            docs = [{"id": "D0.02", "path": "D0.02.md", "status": "in-review", "version": "1.1", "applicability": "active", "depends": []}]
            before = {p: p.read_bytes() for p in [state, logs / "session-001.md", logs / "session-002.md"]}
            with patch.object(blueprint, "workspace_paths", return_value=paths), patch.object(blueprint, "load_manifest", return_value=docs), patch.object(blueprint, "load_approvals", return_value={}):
                findings = blueprint.state_reconciliation_findings()
            messages = [m for _, m in findings]
            self.assertTrue(any("current document D0.02 says v1.0" in m for m in messages))
            self.assertTrue(any("older than available latest session" in m for m in messages))
            self.assertTrue(any("no key decisions exist" in m for m in messages))
            self.assertEqual(before, {p: p.read_bytes() for p in before})


class StateAuditCommandTests(unittest.TestCase):
    def test_audit_state_cli_is_available_and_does_not_modify_state(self):
        with tempfile.TemporaryDirectory(prefix="bp-p5-audit-cli-") as temp:
            workspace = create_workspace(SOURCE_ROOT, Path(temp) / "workspace", "Audit CLI Fixture", preserve_onboarding=True)
            state = workspace / "_control" / "STATE.md"
            before = state.read_bytes()
            result = subprocess.run([sys.executable, "-B", str(workspace / "bp.py"), "audit-state"],
                                    cwd=workspace, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("read-only", result.stdout.lower())
            self.assertIn("No files were modified", result.stdout)
            self.assertEqual(before, state.read_bytes())


class ArchitectureCliIntegrationTests(unittest.TestCase):
    """Exercise the public workspace CLI, including approval-state severity."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bp-p5-cli-arch-")
        self.root = create_workspace(SOURCE_ROOT, Path(self.temp.name) / "workspace",
                                     "Architecture CLI Integration", preserve_onboarding=True)
        _, context = blueprint.discover_context(start=self.root, launcher_path=self.root / "bp.py")
        blueprint.set_workspace_paths(context)

    def tearDown(self):
        blueprint._ACTIVE_WORKSPACE_PATHS = None
        self.temp.cleanup()

    def _run(self, *args):
        return subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), *args],
                              cwd=self.root, capture_output=True, text=True, timeout=45)

    def _write_architecture(self, status="in-review", version=None, mismatch=False):
        docs = blueprint.load_manifest()
        by_id = {item["id"]: item for item in docs}
        arch = by_id["D0.02"]
        vision = by_id["D0.01"]
        version = version or arch["version"]
        today = datetime.date.today().isoformat()
        arch_path = self.root / "docs" / arch["path"]
        arch_path.parent.mkdir(parents=True, exist_ok=True)

        # Give the inventory one explicit row for every manifest record. The only
        # intentional mismatch is D0.01, whose architecture disposition is
        # Conditional while its manifest applicability remains active.
        table = [
            "| Concern | Disposition | Proposed canonical document(s) | Rationale | Decision status |",
            "|---|---|---|---|---|",
        ]
        disposition = {"active": "Core", "conditional": "Conditional",
                       "deferred": "Deferred", "excluded": "Excluded"}
        for item in docs:
            value = "Conditional" if mismatch and item["id"] == "D0.01" else disposition[item["applicability"]]
            table.append(f"| {item['id']} | {value} | {item['id']} | Explicit integration fixture classification | Accepted |")

        body = "# Architecture integration fixture\n\n"
        for heading in blueprint.ARCHITECTURE_REQUIRED_HEADINGS:
            body += heading + "\n\n"
            if heading == "## Document inventory and applicability":
                body += "\n".join(table) + "\n\n"
            else:
                body += "This section records a concrete fixture decision for public CLI validation.\n\n"

        arch_front = (
            "---\n"
            f"doc_id: D0.02\ntitle: {arch['title']}\nphase: {arch['phase']}\n"
            f"status: {status}\nmaturity: {arch['maturity']}\n"
            f"applicability: {arch['applicability']}\n"
            f"applicability_rationale: \"{arch['applicability_rationale']}\"\n"
            f"profile_tier: {arch['profile_tier']}\nversion: {version}\nlast_updated: {today}\n"
            "depends_on: [D0.01]\n"
            "summary: \"Architecture integration fixture used to verify disposition conformance.\"\n---\n\n"
        )
        arch_path.write_text(arch_front + body, encoding="utf-8", newline="\n")
        updates = {"Status": status, "Version": version, "Last updated": today}
        self.assertTrue(blueprint.update_manifest_row("D0.02", updates))

        if status == "approved":
            # A valid upstream approval is needed because D0.02 consumes D0.01.
            vision_path = self.root / "docs" / vision["path"]
            vision_path.parent.mkdir(parents=True, exist_ok=True)
            vision_front = (
                "---\n"
                f"doc_id: D0.01\ntitle: {vision['title']}\nphase: {vision['phase']}\n"
                "status: approved\n"
                f"maturity: {vision['maturity']}\napplicability: {vision['applicability']}\n"
                f"applicability_rationale: \"{vision['applicability_rationale']}\"\n"
                f"profile_tier: {vision['profile_tier']}\nversion: 1.0\nlast_updated: {today}\n"
                "depends_on: []\n"
                "summary: \"Vision fixture defining a concrete test project scope.\"\n---\n\n"
            )
            vision_body = (
                "# Project vision\n\n"
                "The project defines a concrete scope for a deterministic framework validation test.\n"
            )
            vision_path.write_text(vision_front + vision_body, encoding="utf-8", newline="\n")
            self.assertTrue(blueprint.update_manifest_row("D0.01", {
                "Status": "approved", "Version": "1.0", "Last updated": today
            }))

            # Re-read after metadata synchronization and issue genuine metadata-bound
            # fingerprints so the integration test exercises approval_problem().
            for did in ("D0.01", "D0.02"):
                current = next(item for item in blueprint.load_manifest() if item["id"] == did)
                path = self.root / "docs" / current["path"]
                digest = blueprint.approval_fingerprint(path.read_text(encoding="utf-8"), current)
                blueprint.append_table_row(blueprint.workspace_paths().approvals, [
                    did, current["version"], today, "test-owner",
                    f"Owner approval fixture for {did}; session-999-2026-11-10", digest
                ])

    def test_strict_cli_keeps_draft_architecture_drift_advisory(self):
        self._write_architecture(status="in-review", mismatch=True)
        indexed = self._run("index")
        self.assertEqual(0, indexed.returncode, indexed.stdout + indexed.stderr)
        result = self._run("check", "--strict")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("WARN  ARCH-CONFORMANCE: D0.02 is 'in-review', not approved", result.stdout)
        self.assertNotIn("ERROR ARCH-CONFORMANCE:", result.stdout)

    def test_strict_cli_blocks_validly_approved_architecture_mismatch(self):
        self._write_architecture(status="approved", version="1.0", mismatch=True)
        indexed = self._run("index")
        self.assertEqual(0, indexed.returncode, indexed.stdout + indexed.stderr)
        result = self._run("check", "--strict")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("ARCH-CONFORMANCE: D0.01 is 'conditional' in approved D0.02", result.stdout)
        self.assertNotIn("approval evidence is not valid", result.stdout)

    def test_public_strict_check_reports_active_to_conditional_dependency(self):
        self.assertTrue(blueprint.update_manifest_row("D1.01", {"Depends on": "D1.05"}))
        result = self._run("check", "--strict")
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("DEPENDENCY-APPLICABILITY: active document D1.01 depends on D1.05", result.stdout)
        self.assertIn("applicability is 'conditional'", result.stdout)

    def test_approved_architecture_strict_check_is_read_only(self):
        self._write_architecture(status="approved", version="1.0", mismatch=True)
        before = {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.root.rglob("*")) if path.is_file()
        }
        result = self._run("check", "--strict")
        after = {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.root.rglob("*")) if path.is_file()
        }
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(before, after)


class StateAuditReadOnlyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bp-p5-state-cli-")
        self.root = create_workspace(SOURCE_ROOT, Path(self.temp.name) / "workspace",
                                     "State Audit Integration", preserve_onboarding=True)

    def tearDown(self):
        blueprint._ACTIVE_WORKSPACE_PATHS = None
        self.temp.cleanup()

    def _snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.root.rglob("*")) if path.is_file()
        }

    def test_audit_state_command_is_read_only_across_entire_workspace(self):
        before = self._snapshot()
        result = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "audit-state"],
                                cwd=self.root, capture_output=True, text=True, timeout=45)
        after = self._snapshot()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("No files were modified", result.stdout)
        self.assertEqual(before, after)

    def test_fresh_workspace_state_audit_has_no_starter_reference_warnings(self):
        result = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "audit-state", "--strict"],
                                cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("Errors: 0 | Warnings: 0", result.stdout)
        self.assertIn("No files were modified", result.stdout)

    def test_strict_audit_reports_stale_session_references_without_mutation(self):
        state = self.root / "_control" / "STATE.md"
        content = state.read_text(encoding="utf-8")
        content = content.replace("| Last updated | — |", "| Last updated | session-000 |")
        content = content.replace("| Latest handoff | — |", "| Latest handoff | session-000 |")
        state.write_text(content, encoding="utf-8", newline="\n")
        session_dir = self.root / "_control" / "logs" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session-001-2026-11-10.md").write_text(
            "# Session 001\n\nA test session record.\n", encoding="utf-8", newline="\n")
        before = self._snapshot()
        result = subprocess.run([sys.executable, "-B", str(self.root / "bp.py"), "audit-state", "--strict"],
                                cwd=self.root, capture_output=True, text=True, timeout=45)
        after = self._snapshot()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("STATE-003: STATE latest handoff is older than available latest session", result.stdout)
        self.assertIn("STATE-004: STATE last-updated reference is older than available latest session", result.stdout)
        self.assertIn("No files were modified", result.stdout)
        self.assertEqual(before, after)

    def test_portable_completion_contract_requires_readback_and_validation(self):
        instructions = (SOURCE_ROOT / "starter" / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in ("Planned", "Attempted", "Completed", "Verified", "Partial", "Failed", "Blocked",
                       "read-back", "run the relevant checks", "approval/review status separately"):
            self.assertIn(phrase, instructions)


    def test_completion_contract_defines_distinct_outcome_states_and_boundaries(self):
        instructions = (SOURCE_ROOT / "starter" / "AGENTS.md").read_text(encoding="utf-8")
        manual = (SOURCE_ROOT / "_framework" / "OPERATING-MANUAL.md").read_text(encoding="utf-8")
        protocols = (SOURCE_ROOT / "_framework" / "PROTOCOLS.md").read_text(encoding="utf-8")
        for term in ("Planned", "Attempted", "Completed", "Verified", "Partial", "Failed", "Blocked"):
            self.assertIn(term, instructions)
            self.assertIn(term, manual)
        for phrase in ("read-back", "validation", "approval", "successful validation command", "tool or command reports success", "remaining work"):
            self.assertIn(phrase, manual.lower())
        self.assertIn("5.5.1 Consequential change completion and reporting", protocols)
        self.assertIn("read the files back", protocols.lower())

    def test_completion_contract_does_not_require_hashes_or_new_registers_for_routine_edits(self):
        instructions = (SOURCE_ROOT / "starter" / "AGENTS.md").read_text(encoding="utf-8").lower()
        manual = (SOURCE_ROOT / "_framework" / "OPERATING-MANUAL.md").read_text(encoding="utf-8").lower()
        self.assertIn("do not create a separate report file", instructions)
        self.assertIn("rather than a new mandatory register", manual)
        self.assertIn("do not add per-edit hashes", manual)

class StateAuditCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bp-p5-state-coverage-")
        self.root = Path(self.temp.name)
        self.control = self.root / "_control"
        self.logs = self.control / "logs" / "sessions"
        self.registry = self.control / "registry"
        self.docs_dir = self.root / "docs"
        self.logs.mkdir(parents=True)
        self.registry.mkdir(parents=True)
        self.docs_dir.mkdir(parents=True)
        self.state = self.control / "STATE.md"
        self.approvals = self.registry / "APPROVALS.md"
        self.decisions = self.registry / "DECISIONS.md"
        self.index = self.registry / "INDEX.md"
        self.document = self.docs_dir / "D1.01.md"
        self.document.write_text(
            "---\ndoc_id: D1.01\ntitle: Vision\nphase: 1\nstatus: in-review\n"
            "maturity: working\nversion: 1.2\nlast_updated: 2026-11-11\n"
            "depends_on: []\nsummary: Fixture\napplicability: active\nprofile_tier: standard\n---\n# Vision\n",
            encoding="utf-8")
        self.docs = [{"id": "D1.01", "path": "D1.01.md", "status": "in-review", "version": "1.2",
                      "applicability": "active", "depends": [], "phase": 1, "size": "M", "profile_tier": "standard",
                      "title": "Vision", "maturity": "working", "last_updated": "2026-11-11"}]
        self.paths = SimpleNamespace(root=self.root, state=self.state, sessions=self.logs,
                                      approvals=self.approvals, decisions=self.decisions, docs=self.docs_dir,
                                      index=self.index, resolve_document=lambda rel: self.docs_dir / rel)
        self.approval_rows = {}
        self.state.write_text(self._state(), encoding="utf-8")
        self.approvals.write_text("| Doc ID | Version | Date | Approved by | Evidence | Content hash |\n|---|---|---|---|---|---|\n", encoding="utf-8")
        self.decisions.write_text("| ID | Title | Status | Date | Phase | Supersedes | File |\n|---|---|---|---|---|---|---|\n", encoding="utf-8")
        self.index.write_text("# INDEX\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _state(self, current="D1.01 — Vision v1.2 (in-review)", last_updated="session-002",
               checkpoint="session-002 — clean", handoff="session-002", next_action="Review D1.01 v1.2 with the owner.",
               awaiting="(none)", decisions="- ADR-001 accepted"):
        return ("# State\n\n| Field | Value |\n|---|---|\n"
                f"| Current document | {current} |\n| Latest handoff | {handoff} |\n"
                f"| Last clean checkpoint | {checkpoint} |\n| Last updated | {last_updated} |\n\n"
                f"## Next action\n{next_action}\n\n## Awaiting the owner\n{awaiting}\n\n"
                f"## Key decisions\n{decisions}\n")

    def _run(self, index_stale=False):
        with patch.object(blueprint, "workspace_paths", return_value=self.paths), \
             patch.object(blueprint, "load_manifest", return_value=self.docs), \
             patch.object(blueprint, "load_approvals", return_value=self.approval_rows), \
             patch.object(blueprint, "approval_problem", return_value=None), \
             patch.object(blueprint, "index_is_stale", return_value=index_stale):
            return blueprint.state_reconciliation_findings()

    def test_state004_compares_clean_checkpoint_and_accepts_reasoned_exception(self):
        (self.logs / "session-001.md").write_text("# Session 001\n", encoding="utf-8")
        (self.logs / "session-002.md").write_text("# Session 002\n", encoding="utf-8")
        self.state.write_text(self._state(last_updated="session-001", checkpoint="session-002 — clean"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-004" in message for message in messages))
        self.state.write_text(self._state(last_updated="session-001 (reason: state file intentionally unchanged during checkpoint)",
                                          checkpoint="session-002 — clean"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertFalse(any("STATE-004" in message for message in messages))

    def test_state006_detects_exact_version_awaiting_approval_but_registry_approved(self):
        self.approval_rows = {"D1.01": {"version": "1.2", "content hash": "a" * 64}}
        self.state.write_text(self._state(awaiting="D1.01 v1.2 is awaiting approval."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-006" in message and "valid approval record for that exact version" in message for message in messages))

    def test_state007_reports_missing_next_action_and_contradictory_status_claims(self):
        self.state.write_text(self._state(next_action="(none)"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-007" in message and "missing" in message for message in messages))
        self.state.write_text(self._state(next_action="D1.01 v1.2 (approved)\nD1.01 v1.2 (in-review)"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("contradictory status claims" in message for message in messages))

    def test_state008_checks_scoped_session_document_and_local_link_references(self):
        (self.logs / "session-001.md").write_text("# Session\nSee [missing](not-here.md), D9.99 and session-999.\n", encoding="utf-8")
        self.state.write_text(self._state(handoff="session-001"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-008" in message and "session-999" in message for message in messages))
        self.assertTrue(any("STATE-008" in message and "D9.99" in message for message in messages))
        self.assertTrue(any("STATE-008" in message and "not-here.md" in message for message in messages))

    def test_state009_reports_stale_index_and_progress_without_mutation(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        findings = self._run(index_stale=True)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        messages = [message for _, message in findings]
        self.assertTrue(any("INDEX.md is missing or stale" in message for message in messages))
        self.assertTrue(any("STATE-009" in message and "PROGRESS markers" in message for message in messages))
        self.assertEqual(before, after)

    def test_session_reference_matching_uses_exact_numeric_identity(self):
        (self.logs / "session-0010.md").write_text("# Session 10\n", encoding="utf-8")
        self.assertFalse(blueprint._session_exists(self.logs, "session-001"))
        self.assertTrue(blueprint._session_exists(self.logs, "session-0010"))

    def test_explicit_status_and_version_claims_are_not_inferred_from_free_prose(self):
        claims = blueprint._explicit_doc_claims("Plan to approve D1.01 after review.\nD1.01 v1.1 (in-review)")
        self.assertEqual("", claims[0]["version"])
        self.assertEqual("1.1", claims[1]["version"])
        self.assertEqual("in-review", claims[1]["status"])

    def test_state001_compares_explicit_current_document_status(self):
        self.state.write_text(self._state(current="D1.01 — Vision v1.2 (approved)"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-001" in message and "status 'approved'" in message for message in messages))

    def test_state002_detects_stale_version_in_next_action(self):
        self.state.write_text(self._state(next_action="Revise D1.01 v1.1 before review."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-002" in message and "D1.01 v1.1" in message for message in messages))

    def test_state006_detects_multiline_awaiting_approval_for_exact_version(self):
        self.approval_rows = {"D1.01": {"version": "1.2", "content hash": "a" * 64}}
        self.state.write_text(self._state(awaiting="D1.01 v1.2\nAwaiting approval from the owner."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-006" in message and "D1.01 v1.2" in message for message in messages))

    def test_state006_does_not_treat_invalid_fingerprint_as_approval(self):
        self.approval_rows = {"D1.01": {"version": "1.2", "content hash": "legacy-hash"}}
        self.state.write_text(self._state(awaiting="D1.01 v1.2 is awaiting approval."), encoding="utf-8")
        with patch.object(blueprint, "workspace_paths", return_value=self.paths), \
             patch.object(blueprint, "load_manifest", return_value=self.docs), \
             patch.object(blueprint, "load_approvals", return_value=self.approval_rows), \
             patch.object(blueprint, "approval_problem", return_value="approval fingerprint is invalid"), \
             patch.object(blueprint, "index_is_stale", return_value=False):
            messages = [message for _, message in blueprint.state_reconciliation_findings()]
        self.assertTrue(any("STATE-006" in message and "do not treat the row as valid approval" in message for message in messages))

    def test_state006_does_not_transfer_approval_to_another_version(self):
        self.approval_rows = {"D1.01": {"version": "1.3", "content hash": "a" * 64}}
        self.state.write_text(self._state(awaiting="D1.01 v1.2 is awaiting approval."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertFalse(any("STATE-006" in message and "awaiting approval" in message for message in messages))

    def test_state005_requires_no_decisions_claim_inside_key_decisions_section(self):
        self.decisions.write_text(
            "| ID | Title | Status | Date | Phase | Supersedes | File |\n|---|---|---|---|---|---|---|\n"
            "| ADR-001 | Accepted | accepted | 2026-11-11 | 1 | — | docs/adr.md |\n", encoding="utf-8")
        self.state.write_text(self._state(decisions="- (none yet)"), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertTrue(any("STATE-005" in message for message in messages))
        self.state.write_text(self._state(decisions="Decisions are listed in DECISIONS.md."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertFalse(any("STATE-005" in message for message in messages))

    def test_state008_planned_manifest_document_is_not_reported_missing(self):
        self.docs.append({"id": "D2.01", "path": "02-product/future.md", "status": "not-started",
                          "version": "0.1", "applicability": "active", "depends": [], "phase": 2,
                          "size": "M", "profile_tier": "standard", "title": "Future", "maturity": "outline",
                          "last_updated": "2026-11-11"})
        (self.state).write_text(self._state(next_action="Prepare D2.01 when discovery is complete."), encoding="utf-8")
        messages = [message for _, message in self._run()]
        self.assertFalse(any("D2.01" in message and "not present in MANIFEST" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
