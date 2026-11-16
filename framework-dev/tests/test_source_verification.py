"""Tests for the source verifier's maintainer/bootstrap scope separation."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
if str(SOURCE_ROOT / "_framework" / "tools") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "_framework" / "tools"))
from blueprint_framework.source_cli import _required_source_files, verify_source  # noqa: E402
from workspace_paths import SourcePaths, WorkspacePaths  # noqa: E402
from workspace_fixture import create_workspace  # noqa: E402
import blueprint  # noqa: E402


class SourceVerificationScopeTests(unittest.TestCase):
    def _runtime_copy(self, root: Path) -> SourcePaths:
        for relative in ("VERSION", "LICENSE", "bp.py", "framework-dev/SOURCE-MANIFEST.json"):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_ROOT / relative, target)
        for directory in ("_framework", "starter", "src"):
            shutil.copytree(SOURCE_ROOT / directory, root / directory)
        return SourcePaths.from_root(root)

    def test_bootstrap_scope_passes_without_maintainer_test_tree(self):
        with tempfile.TemporaryDirectory(prefix="pbf-bootstrap-scope-") as temporary:
            paths = self._runtime_copy(Path(temporary))
            ok, issues = verify_source(paths, scope="bootstrap")
            self.assertTrue(ok, issues)
            self.assertFalse((paths.root / "framework-dev/tests").exists())

    def test_maintainer_scope_requires_development_material(self):
        with tempfile.TemporaryDirectory(prefix="pbf-maintainer-scope-") as temporary:
            paths = self._runtime_copy(Path(temporary))
            ok, issues = verify_source(paths, scope="maintainer")
            self.assertFalse(ok)
            self.assertTrue(any("DEVELOPMENT.md" in issue for issue in issues), issues)
            self.assertTrue(any("framework-dev/tests/README.md" in issue for issue in issues), issues)

    def test_bootstrap_scope_rejects_maintainer_test_flag(self):
        paths = SourcePaths.from_root(SOURCE_ROOT)
        ok, issues = verify_source(paths, run_tests=True, scope="bootstrap")
        self.assertFalse(ok)
        self.assertTrue(any("does not run maintainer tests" in issue for issue in issues), issues)

    def test_bootstrap_requirements_are_limited_to_runtime_inputs(self):
        paths = SourcePaths.from_root(SOURCE_ROOT)
        required = _required_source_files(paths, "bootstrap")
        relatives = {item.relative_to(paths.root).as_posix() for item in required}
        self.assertIn("framework-dev/SOURCE-MANIFEST.json", relatives)
        self.assertIn("bp.py", relatives)
        allowed_roots = ("_framework/", "starter/", "src/", "framework-dev/SOURCE-MANIFEST.json")
        self.assertTrue(all(item in {"VERSION", "LICENSE", "bp.py"} or item.startswith(allowed_roots) for item in relatives), sorted(relatives))

    def test_developer_and_workspace_gitignore_cover_common_secret_files(self):
        required = (".env", ".env.*", "!.env.example", "*.pem", "*.key", "*.p12", "*.pfx", "/.secrets/", "/secrets/", "/credentials/")
        for relative in (".gitignore", "starter/.gitignore"):
            text = (SOURCE_ROOT / relative).read_text(encoding="utf-8")
            attributes = (SOURCE_ROOT / relative.replace(".gitignore", ".gitattributes")).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for pattern in required:
                    self.assertIn(pattern, text)
                self.assertIn("*.template text eol=lf", attributes)

    def test_html_comment_scanner_preserves_supported_comment_behavior(self):
        module = blueprint
        self.assertEqual("beforeafter", module.strip_html_comments("before<!-- hidden -->after"))
        self.assertEqual("amiddleb", module.strip_html_comments("a<!-- one -->middle<!-- two -->b"))
        self.assertEqual("prefix<!-- unterminated", module.strip_html_comments("prefix<!-- unterminated"))
        self.assertEqual("az", module.strip_html_comments("a<!-- outer <!-- inner -->z"))

    def test_markdown_link_scanners_preserve_inline_image_and_reference_targets(self):
        module = blueprint
        markdown = (
            '[inline](docs/inline.md) ![image](assets/image.png) '
            '[angle](<docs/angle.md>) [title](docs/title.md "description") '
            '[reference][guide] [collapsed][]\n\n'
            '[guide]: docs/guide.md\n[collapsed]: docs/collapsed.md\n'
        )
        self.assertEqual(
            ["docs/inline.md", "assets/image.png", "docs/angle.md", "docs/title.md"],
            module.inline_markdown_link_targets(markdown),
        )
        self.assertEqual(
            [("reference", "guide"), ("collapsed", "")],
            module.reference_markdown_link_labels(markdown),
        )
        self.assertEqual(
            ["docs/inline.md", "assets/image.png", "docs/angle.md", "docs/title.md", "docs/guide.md", "docs/collapsed.md"],
            module.markdown_link_targets(markdown),
        )

    def test_malformed_comment_and_link_inputs_have_bounded_scan_work(self):
        import time
        module = blueprint
        malformed_comments = "<!-- blueprint-lint:  " * 20_000
        malformed_links = "[" * 100_000 + "](" * 50_000
        repeated_unclosed_links = "[](" + ("x" * 64 + "[](") * 2_000
        malformed_references = "[" * 100_000 + "][" * 50_000
        dense_candidates = "[](" * 200_000
        dense_angle_candidates = "[](<" * 100_000
        dense_unclosed_targets = "[a](xxxxxxxxxx" * 50_000
        metrics: dict[str, int] = {}
        angle_metrics: dict[str, int] = {}
        unclosed_metrics: dict[str, int] = {}
        started = time.perf_counter()
        module.strip_html_comments(malformed_comments)
        module.find_fill_markers(malformed_comments)
        module.markdown_link_targets(malformed_links)
        module.markdown_link_targets(repeated_unclosed_links)
        module.reference_markdown_link_labels(malformed_references)
        targets, issues = module.inline_markdown_link_occurrences(dense_candidates, metrics)
        angle_targets, angle_issues = module.inline_markdown_link_occurrences(dense_angle_candidates, angle_metrics)
        unclosed_targets, unclosed_issues = module.inline_markdown_link_occurrences(dense_unclosed_targets, unclosed_metrics)
        elapsed = time.perf_counter() - started
        self.assertEqual([], targets)
        self.assertEqual([], angle_targets)
        self.assertEqual([], unclosed_targets)
        self.assertGreater(metrics.get("candidates", 0), 100_000)
        self.assertEqual(1, metrics.get("stop_searches"), metrics)
        self.assertEqual(1, angle_metrics.get("stop_searches"), angle_metrics)
        self.assertEqual(1, unclosed_metrics.get("stop_searches"), unclosed_metrics)
        self.assertLessEqual(metrics.get("whitespace_searches", 0), metrics.get("candidates", 0) * 3)
        self.assertTrue(issues)
        self.assertTrue(angle_issues)
        self.assertTrue(unclosed_issues)
        self.assertLess(elapsed, 15.0, f"Malformed Markdown scan took {elapsed:.3f}s")

    def test_link_diagnostics_preserve_original_offsets_after_ignored_blocks(self):
        markdown = (
            "# Heading\n\n"
            "```text\n[not a link](ignored.md)\n```\n"
            "<!-- hidden [also not a link](ignored.md) -->\n"
            "Visible text\n[broken](http://[broken)\n"
        )
        occurrences, issues = blueprint.markdown_link_occurrences(markdown)
        self.assertEqual(1, len(occurrences))
        self.assertFalse(issues)
        target, offset = occurrences[0]
        self.assertEqual("http://[broken", target)
        self.assertEqual(markdown.index("[broken]"), offset)
        self.assertEqual(8, blueprint.markdown_line_number(offset, blueprint.markdown_line_starts(markdown)))

    def test_overlong_inline_link_labels_are_reported(self):
        markdown = "[" + ("l" * 2050) + "](target.md)"
        occurrences, issues = blueprint.markdown_link_occurrences(markdown)
        self.assertFalse(occurrences)
        self.assertTrue(issues)
        self.assertIn("label exceeds", issues[0][1])

    def test_state_audit_reports_malformed_links_without_crashing(self):
        with tempfile.TemporaryDirectory(prefix="pbf-state-invalid-links-") as temporary:
            workspace = Path(temporary) / "workspace"
            create_workspace(SOURCE_ROOT, workspace, "Malformed State Links")
            state = workspace / "_control/STATE.md"
            content = state.read_text(encoding="utf-8")
            content += "\n## Link validation fixture\n\n[bad URL](http://[broken)\n[NUL](%00)\n"
            state.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [sys.executable, "-B", str(workspace / "bp.py"), "audit-state", "--strict"],
                cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False, timeout=45,
            )
            self.assertNotIn("Traceback", result.stdout)
            self.assertIn("invalid link target", result.stdout)
            self.assertEqual(2, sum("STATE-008:" in line for line in result.stdout.splitlines()))

    def test_git_ignore_rules_preserve_nested_security_documentation(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("Git is unavailable")
        with tempfile.TemporaryDirectory(prefix="pbf-gitignore-") as temporary:
            repo = Path(temporary)
            shutil.copy2(SOURCE_ROOT / "starter/.gitignore", repo / ".gitignore")
            subprocess.run([git, "init", "-q", str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            paths = (
                ".env", ".env.local", "server.pem", "id.key", "store.p12", "ca.pfx",
                "app.keystore", ".secrets/key", "secrets/key", "credentials/key",
                "docs/security/credentials/policy.md", "docs/security/secrets/policy.md",
                ".env.example", ".env.template", "docs/slides/Slides.key",
            )
            for relative in paths:
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("fixture\n", encoding="utf-8")
            def ignored(relative: str) -> bool:
                result = subprocess.run(
                    [git, "-C", str(repo), "check-ignore", "-q", "--", relative],
                    check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                return result.returncode == 0
            for relative in (".env", ".env.local", "server.pem", "id.key", "store.p12", "ca.pfx", "app.keystore", ".secrets/key", "secrets/key", "credentials/key"):
                with self.subTest(path=relative):
                    self.assertTrue(ignored(relative), f"Expected secret to be ignored: {relative}")
            for relative in ("docs/security/credentials/policy.md", "docs/security/secrets/policy.md", ".env.example", ".env.template"):
                with self.subTest(path=relative):
                    self.assertFalse(ignored(relative), f"Expected documentation/example to remain trackable: {relative}")
            self.assertTrue(ignored("docs/slides/Slides.key"), "The broad *.key safety rule is deliberate and documented")

    def test_long_external_urls_and_data_uris_bypass_local_path_limit(self):
        long_url = "https://example.test/diagram/" + ("q" * 2100)
        data_image = "data:image/png;base64," + ("A" * 4096)
        long_reference_url = "https://example.test/edit/" + ("d" * 2300)
        markdown = (
            f"[long URL]({long_url}) ![embedded image]({data_image}) "
            "[reference][diagram]\n\n"
            f"[diagram]: <{long_reference_url}>\n"
        )
        occurrences, issues = blueprint.markdown_link_occurrences(markdown)
        self.assertFalse(issues, issues)
        self.assertEqual([long_url, data_image, long_reference_url], [target for target, _ in occurrences])
        for target in (long_url, data_image, long_reference_url):
            with self.subTest(target_prefix=target[:32]):
                self.assertEqual(("exists", "external link"), blueprint.markdown_link_target_exists(Path("sample.md"), target))

        local_target = "x" * 2100
        local_occurrences, local_issues = blueprint.markdown_link_occurrences(f"[local]({local_target})")
        self.assertFalse(local_occurrences)
        self.assertTrue(local_issues)
        self.assertIn("2048-character", local_issues[0][1])
        self.assertEqual("invalid", blueprint.markdown_link_target_exists(Path("sample.md"), local_target)[0])

        malformed_long_url = "https://[broken/" + ("x" * 2100)
        state, detail = blueprint.markdown_link_target_exists(Path("sample.md"), malformed_long_url)
        self.assertEqual("invalid", state)
        self.assertIn("invalid link target", detail.lower())
        state, detail = blueprint.markdown_link_target_exists(Path("sample.md"), "data:image/png;base64")
        self.assertEqual("invalid", state)
        self.assertIn("comma separator", detail)

    def test_unterminated_html_comments_produce_offset_diagnostics(self):
        markdown = (
            "```html\n<!-- comment-like code\n```\n"
            "Visible text\n<!-- unmatched opener\n"
            "[escaping link](../../../../outside.md)\n"
        )
        occurrences, issues = blueprint.markdown_link_occurrences(markdown)
        self.assertFalse(occurrences, "Markdown inside an unterminated HTML comment remains masked")
        self.assertEqual(1, len(issues))
        offset, detail = issues[0]
        self.assertEqual(markdown.index("<!-- unmatched opener"), offset)
        self.assertEqual("unterminated HTML comment", detail)
        self.assertEqual(5, blueprint.markdown_line_number(offset, blueprint.markdown_line_starts(markdown)))

    def test_overlong_inline_link_targets_are_reported_with_source_offsets(self):
        markdown = "Heading\n[long](" + ("x" * 2100) + ")\n"
        occurrences, issues = blueprint.markdown_link_occurrences(markdown)
        self.assertFalse(occurrences)
        self.assertTrue(issues)
        offset, detail = issues[0]
        self.assertEqual(2, blueprint.markdown_line_number(offset, blueprint.markdown_line_starts(markdown)))
        self.assertIn("2048-character", detail)

    def test_invalid_url_and_filesystem_targets_return_controlled_findings(self):
        with tempfile.TemporaryDirectory(prefix="pbf-invalid-links-") as temporary:
            workspace = Path(temporary) / "workspace"
            create_workspace(SOURCE_ROOT, workspace, "Malformed Link Validation")
            source = workspace / "docs/99-appendix/research/link-check.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("# Link checks\n", encoding="utf-8")
            previous = blueprint._ACTIVE_WORKSPACE_PATHS
            blueprint.set_workspace_paths(WorkspacePaths.from_root(workspace))
            try:
                cases = (
                    ("http://[broken", "invalid"),
                    ("%00", "invalid"),
                    ("x" * 300, "invalid"),
                )
                for target, expected in cases:
                    with self.subTest(target=target[:30]):
                        state, detail = blueprint.markdown_link_target_exists(source, target)
                        self.assertEqual(expected, state)
                        self.assertTrue(detail)
            finally:
                blueprint.set_workspace_paths(previous)

    def test_workspace_check_reports_malformed_links_without_crashing(self):
        with tempfile.TemporaryDirectory(prefix="pbf-check-invalid-links-") as temporary:
            workspace = Path(temporary) / "workspace"
            create_workspace(SOURCE_ROOT, workspace, "Malformed Link CLI")
            target_file = workspace / "docs/99-appendix/research/malformed-links.md"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(
                "# Malformed links\n\n"
                "[bad URL](http://[broken)\n"
                "[NUL](%00)\n"
                "[long path](" + ("x" * 300) + ")\n"
                "[overlong](" + ("x" * 2200) + ")\n"
                "<!-- deliberately unterminated\n"
                "[workspace escape](../../../../outside.md)\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", str(workspace / "bp.py"), "check", "--strict"],
                cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False, timeout=45,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn("Traceback", result.stdout)
            self.assertIn("invalid link target", result.stdout)
            self.assertIn("invalid Markdown link", result.stdout)
            self.assertRegex(result.stdout, r"malformed-links\.md:7: invalid Markdown link \(unterminated HTML comment\)")

    def test_github_policy_and_apache_license_files_are_present_and_consistent(self):
        root_license = (SOURCE_ROOT / "LICENSE").read_bytes()
        starter_license = (SOURCE_ROOT / "starter/LICENSE").read_bytes()
        self.assertEqual(root_license, starter_license)
        self.assertIn(b"Apache License", root_license[:256])
        self.assertIn(b"Version 2.0, January 2004", root_license[:512])
        for relative in ("CODE_OF_CONDUCT.md", "SECURITY.md", "CONTRIBUTING.md"):
            self.assertTrue((SOURCE_ROOT / relative).is_file(), relative)
        security = (SOURCE_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("private vulnerability reporting", security.lower())
        self.assertIn("must enable", security.lower())
        self.assertNotRegex(security, r"\b(?:TODO|INSERT|FIXME)\b")
        contribute = (SOURCE_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("Apache License 2.0", contribute)
        changelog = (SOURCE_ROOT / "framework-dev/CHANGELOG.md").read_text(encoding="utf-8").lower()
        private_history_tokens = (
            ("removed", "references", "to", "internal", "review"),
            ("historical", "evaluation", "workflows"),
            ("host-specific", "fingerprints"),
        )
        for tokens in private_history_tokens:
            self.assertNotIn(" ".join(tokens), changelog)
        self.assertIn("forward scanners", changelog)

    def test_generated_workspace_receives_apache_license(self):
        scope_source = SOURCE_ROOT / "starter/PBF-LICENSE-SCOPE.md"
        self.assertTrue(scope_source.is_file())
        scope_text = scope_source.read_text(encoding="utf-8").lower()
        self.assertIn("does **not** automatically apply", scope_text)
        self.assertIn("owner-authored", scope_text)
        with tempfile.TemporaryDirectory(prefix="pbf-workspace-license-") as temporary:
            workspace = Path(temporary) / "workspace"
            create_workspace(SOURCE_ROOT, workspace, "Licensed Workspace")
            self.assertTrue((workspace / "LICENSE").is_file())
            self.assertEqual((SOURCE_ROOT / "LICENSE").read_bytes(), (workspace / "LICENSE").read_bytes())
            self.assertTrue((workspace / "PBF-LICENSE-SCOPE.md").is_file())
            self.assertEqual(scope_source.read_bytes(), (workspace / "PBF-LICENSE-SCOPE.md").read_bytes())

    def test_diagram_guidance_does_not_execute_or_upload_project_content_automatically(self):
        guidance = (SOURCE_ROOT / "_framework/DIAGRAMS.md").read_text(encoding="utf-8").lower()
        self.assertNotIn("npx -y", guidance)
        self.assertNotIn("mermaid.live", guidance)
        self.assertIn("already installed locally", guidance)
        self.assertIn("explicit owner approval", guidance)
        self.assertIn("explicitly approves the external disclosure", guidance)

    def test_source_verification_uses_independent_test_processes_and_generic_test_names(self):
        source_cli = (SOURCE_ROOT / "src/blueprint_framework/source_cli.py").read_text(encoding="utf-8")
        self.assertIn('test_modules = sorted(tests.glob("test_*.py")', source_cli)
        self.assertIn('"-p", test_file.name', source_cli)
        self.assertIn("Maintainer test modules passed:", source_cli)


if __name__ == "__main__":
    unittest.main()
