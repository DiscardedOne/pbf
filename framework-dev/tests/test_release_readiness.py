"""Regression-baseline and Git checkout tests for regression accounting and Git checkout policy."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = SOURCE_ROOT / "framework-dev" / "tests"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
TOOLS = SOURCE_ROOT / "_framework" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from workspace_fixture import create_workspace  # noqa: E402
from workspace_paths import SourcePaths  # noqa: E402
from blueprint_framework.source_cli import validate_v3_documentation_paths  # noqa: E402

REGRESSION_PORT = SOURCE_ROOT / "framework-dev/tests/test_compatibility_regressions.py"
REGRESSION_BASELINE = SOURCE_ROOT / "framework-dev/tests/fixtures/regression-baseline.json"


def _test_methods(source: str) -> dict[str, list[str]]:
    parsed = ast.parse(source)
    output: dict[str, list[str]] = {}
    for node in parsed.body:
        if isinstance(node, ast.ClassDef):
            methods = [
                child.name for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name.startswith("test_")
            ]
            if methods:
                output[node.name] = methods
    return output


class RegressionBaselineTests(unittest.TestCase):
    def test_all_94_baseline_tests_have_one_to_one_v3_ports(self):
        report = json.loads(REGRESSION_BASELINE.read_text(encoding="utf-8"))
        ported_methods = _test_methods(REGRESSION_PORT.read_text(encoding="utf-8"))
        self.assertEqual(1, report["schema_version"])
        self.assertEqual(94, report["test_count"])
        self.assertEqual("framework-dev/tests/test_compatibility_regressions.py", report["ported_test_module"])
        self.assertEqual(report["method_identities"], ported_methods)
        self.assertEqual(94, sum(len(methods) for methods in ported_methods.values()))
        self.assertRegex(report["baseline_archive_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["baseline_test_module_sha256"], r"^[0-9a-f]{64}$")
        baseline_pairs = {
            f"{class_name}.{method}"
            for class_name, methods in report["method_identities"].items()
            for method in methods
        }
        mapped_pairs = {row["baseline_test"] for row in report["mappings"]}
        self.assertEqual(baseline_pairs, mapped_pairs)

    def test_regression_baseline_has_no_duplicate_or_missing_targets(self):
        report = json.loads(REGRESSION_BASELINE.read_text(encoding="utf-8"))
        targets = [row["ported_test"] for row in report["mappings"]]
        self.assertEqual(94, len(targets))
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(94, len(report["mappings"]))
        self.assertTrue(all(row.get("equivalence_note") for row in report["mappings"]))
        self.assertTrue(all(row["ported_test"] in {
            f"{class_name}.{method}"
            for class_name, methods in report["method_identities"].items()
            for method in methods
        } for row in report["mappings"]))


class GitAutocrlfTests(unittest.TestCase):
    def test_autocrlf_true_checkout_preserves_lf_policy_and_workspace_integrity(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("Git is unavailable on this execution host")

        with tempfile.TemporaryDirectory(prefix="bp-git-eol-") as temp_dir:
            base = Path(temp_dir)
            source = base / "source-workspace"
            clone = base / "autocrlf-clone"
            create_workspace(SOURCE_ROOT, source, "Git EOL Regression", preserve_onboarding=True)

            # Add fixtures for each important text class plus one binary class.
            (source / "docs/99-appendix/research").mkdir(parents=True, exist_ok=True)
            (source / "docs/99-appendix/research/git-eol-fixture.jsonl").write_bytes(
                b'{"test":"git-eol","value":42}\n'
            )
            (source / "docs/99-appendix/research/git-eol-fixture.txt").write_bytes(
                b"line one\nline two\n"
            )
            binary = b"\x89PNG\r\n\x1a\n\x00binary-git-eol-fixture\xff\x00"
            binary_path = source / "docs/_assets/images/git-eol-fixture.png"
            binary_path.parent.mkdir(parents=True, exist_ok=True)
            binary_path.write_bytes(binary)

            def git_run(*args: str, cwd: Path | None = None, expected: int = 0) -> subprocess.CompletedProcess[str]:
                result = subprocess.run(
                    [git, *args], cwd=cwd, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    check=False, timeout=30,
                )
                if result.returncode != expected:
                    self.fail(f"git {' '.join(args)} returned {result.returncode}, expected {expected}:\n{result.stdout}")
                return result

            git_run("init", "--quiet", str(source))
            git_run("config", "core.autocrlf", "true", cwd=source)
            git_run("config", "user.name", "PBF Test", cwd=source)
            git_run("config", "user.email", "pbf-test@example.invalid", cwd=source)
            git_run("add", "--all", cwd=source)
            git_run("commit", "--quiet", "-m", "EOL policy fixture", cwd=source)

            # Explicitly enable autocrlf at clone time and on the clone itself.
            git_run("-c", "core.autocrlf=true", "clone", "--quiet", "--local", "--no-hardlinks", str(source), str(clone), cwd=base)
            git_run("config", "core.autocrlf", "true", cwd=clone)
            self.assertEqual("true", git_run("config", "--get", "core.autocrlf", cwd=clone).stdout.strip())

            text_paths = [
                "README.md", "AGENTS.md", "bp.py", "LICENSE", "PBF-LICENSE-SCOPE.md", ".gitattributes",
                "_control/WORKSPACE.json", "_framework/FRAMEWORK-MANIFEST.json",
                "docs/99-appendix/research/git-eol-fixture.jsonl",
                "docs/99-appendix/research/git-eol-fixture.txt",
            ]
            for relative in text_paths:
                data = (clone / relative).read_bytes()
                with self.subTest(path=relative):
                    self.assertNotIn(b"\r", data, f"CR byte found after autocrlf=true checkout: {relative}")
                    data.decode("utf-8")
                    attrs = git_run("check-attr", "text", "eol", "--", relative, cwd=clone).stdout
                    self.assertIn("text: set", attrs)
                    self.assertIn("eol: lf", attrs)

            self.assertEqual(binary, (clone / "docs/_assets/images/git-eol-fixture.png").read_bytes())
            binary_attrs = git_run("check-attr", "text", "--", "docs/_assets/images/git-eol-fixture.png", cwd=clone).stdout
            self.assertIn("text: unset", binary_attrs)
            self.assertEqual("", git_run("status", "--porcelain", cwd=clone).stdout.strip())

            # Runtime hash verification and index freshness must survive the checkout.
            launcher = clone / "bp.py"
            for command in (("check", "--strict"), ("index", "--check")):
                result = subprocess.run(
                    [sys.executable, "-B", str(launcher), *command], cwd=clone,
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    check=False, timeout=45,
                )
                self.assertEqual(0, result.returncode, f"{command} failed after autocrlf checkout:\n{result.stdout}")
            self.assertEqual("", git_run("status", "--porcelain", cwd=clone).stdout.strip())


class DocumentationPathTests(unittest.TestCase):
    def test_active_v3_operating_docs_contain_no_legacy_paths(self):
        paths = SourcePaths.from_root(SOURCE_ROOT)
        self.assertEqual([], validate_v3_documentation_paths(paths))

    def test_scanner_detects_legacy_commands_but_exempts_historical_guide_appendices(self):
        with tempfile.TemporaryDirectory(prefix="bp-doc-scan-") as temp_dir:
            root = Path(temp_dir)
            shutil.copytree(SOURCE_ROOT / "_framework", root / "_framework")
            shutil.copytree(SOURCE_ROOT / "starter", root / "starter")
            (root / "framework-dev").mkdir()
            for relative in ("framework-dev/SOURCE-MANIFEST.json", "framework-dev/README.md", "framework-dev/RELEASE-CHECKLIST.md", "README.md"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE_ROOT / relative, target)

            guide = root / "_framework/GUIDE.md"
            guide.write_text(
                guide.read_text(encoding="utf-8")
                + "\n## Appendix B: Historical v2.3.2 audit and verification record\n"
                + "Historical example: `python tools/blueprint.py check --strict` and `registry/MANIFEST.md`.\n",
                encoding="utf-8", newline="\n",
            )
            paths = SourcePaths.from_root(root)
            self.assertEqual([], validate_v3_documentation_paths(paths))

            active = root / "_framework/PROTOCOLS.md"
            active.write_text(active.read_text(encoding="utf-8") + "\nOld example: python tools/blueprint.py check\n", encoding="utf-8", newline="\n")
            hits = validate_v3_documentation_paths(paths)
            self.assertTrue(any("legacy workspace command" in issue for issue in hits), hits)

    def test_scanner_rejects_maintainer_only_workspace_paths_and_test_commands(self):
        with tempfile.TemporaryDirectory(prefix="bp-maintainer-doc-scan-") as temp_dir:
            root = Path(temp_dir)
            shutil.copytree(SOURCE_ROOT / "_framework", root / "_framework")
            shutil.copytree(SOURCE_ROOT / "starter", root / "starter")
            (root / "framework-dev").mkdir()
            for relative in ("framework-dev/SOURCE-MANIFEST.json", "framework-dev/README.md", "framework-dev/RELEASE-CHECKLIST.md", "README.md"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE_ROOT / relative, target)
            guide = root / "_framework/GUIDE.md"
            guide.write_text(
                guide.read_text(encoding="utf-8")
                + "\nMaintainer-only reference: framework-dev/tests/test_*.py\n"
                + "Run `python -m unittest discover -s framework-dev/tests`.\n",
                encoding="utf-8", newline="\n",
            )
            issues = validate_v3_documentation_paths(SourcePaths.from_root(root))
            self.assertTrue(any("maintainer-only repository path" in item for item in issues), issues)
            self.assertTrue(any("maintainer test discovery command" in item for item in issues), issues)

    def test_test_readme_module_counts_match_discovered_test_methods(self):
        readme = (TESTS_ROOT / "README.md").read_text(encoding="utf-8")
        documented = {
            filename: int(count)
            for filename, count in re.findall(r"^\| `(?P<file>test_[^`]+\.py)` \| (?P<count>\d+) \|", readme, re.MULTILINE)
        }
        discovered = {
            path.name: sum(len(methods) for methods in _test_methods(path.read_text(encoding="utf-8")).values())
            for path in sorted(TESTS_ROOT.glob("test_*.py"))
        }
        self.assertEqual(discovered, documented)



if __name__ == "__main__":
    unittest.main()
