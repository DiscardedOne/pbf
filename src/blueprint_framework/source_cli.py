"""Source-only command-line interface for the framework maintainer repository.

This module is imported only after the root launcher has selected source mode.
It is never copied into a generated documentation workspace.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workspace_paths import SourcePaths  # type: ignore


def validate_agents_instructions(path: Path) -> list[str]:
    """Check the compact shipped agent contract for encoding, size and hygiene.

    This is a deliberately narrow release-hygiene scan, not a prompt-injection
    detector or a security boundary. Patterns target overt instruction attacks
    and hidden control characters while avoiding ordinary workflow language.
    """
    issues: list[str] = []
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read AGENTS instructions as UTF-8: {exc}"]
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append("AGENTS.md must not contain a UTF-8 BOM")
    if b"\r" in raw:
        issues.append("AGENTS.md must use LF line endings")
    if len(text) > 14_000:
        issues.append(f"AGENTS.md exceeds the 14,000-character hard limit ({len(text)} characters)")
    # 12,000 is the editing target; 14,000 is the normative hard limit.
    # Do not turn the target into a release blocker.

    import re
    import unicodedata

    for index, char in enumerate(text):
        category = unicodedata.category(char)
        if category == "Cf" or (category == "Cc" and char not in "\n\r\t"):
            issues.append(f"AGENTS.md contains an invisible/control character U+{ord(char):04X} at character {index}")
            break

    tripwires = (
        (r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b", "instruction-override phrase"),
        (r"\b(?:reveal|print|expose)\s+(?:the\s+)?(?:system|developer)\s+prompt\b", "hidden-prompt disclosure phrase"),
        (r"\bconceal\s+(?:this|these|your)\s+(?:actions?|instructions?|activity)\b", "concealment phrase"),
        (r"\bdo\s+not\s+(?:tell|inform)\s+(?:the\s+)?user\b", "user-concealment phrase"),
        (r"\b(?:exfiltrate|steal)\s+(?:the\s+)?(?:credentials?|secrets?|tokens?)\b", "credential-exfiltration phrase"),
        (r"\bbypass\s+(?:all\s+)?(?:security|safety)\s+(?:checks|controls|rules)\b", "safeguard-bypass phrase"),
    )
    for pattern, label in tripwires:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(f"AGENTS.md contains a release-hygiene tripwire: {label}")

    # These are compact navigation/interaction contracts, not a harness scanner
    # or an operating-system security boundary.
    required_contract = (
        "## 9. Owner shortcuts", "`status`", "`next`", "`checkpoint`",
        "`gate`", "`audit`", "`park: <idea>`", "`revisit <doc/topic>`",
        "`replan`", "`explain <x>`", "`wrap up`",
        "## 10. State line", "End every substantive message",
        "## 11. On-demand reference map",
        "_framework/CONVERSATIONAL-WORKFLOW.md",
        "_framework/QUESTION-BANK.md",
        "_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md",
    )
    for phrase in required_contract:
        if phrase not in text:
            issues.append(f"AGENTS.md is missing mandatory operating-contract content: {phrase}")

    # Hidden HTML comments are not needed in this compact instruction file.
    if "<!--" in text or "-->" in text:
        issues.append("AGENTS.md must not contain hidden HTML comments")
    return issues


def _required_source_files(paths: SourcePaths, scope: str = "maintainer") -> list[Path]:
    """List runtime inputs or the full maintained source requirements.

    Bootstrap scope contains only workspace-creation inputs. Maintainer
    scope includes the complete maintained source and test suite.
    """
    runtime = (
        "VERSION", "LICENSE", "starter/LICENSE", "starter/PBF-LICENSE-SCOPE.md", "bp.py", "framework-dev/SOURCE-MANIFEST.json",
        "_framework/tools/blueprint.py", "_framework/tools/workspace_paths.py",
        "_framework/defaults/workspace-defaults.json",
        "_framework/defaults/workspace-policy-defaults.md",
        "_framework/GUIDE.md", "_framework/WORKSPACE-CONFIG.md",
        "_framework/OPERATING-MANUAL.md", "_framework/WORKFLOW-PLAN.md",
        "_framework/WINDOWS-USAGE.md", "_framework/DOC-CATALOG.md",
        "_framework/QUALITY-GATES.md", "_framework/PROTOCOLS.md",
        "_framework/CONVENTIONS.md", "_framework/LINT-RULES.md",
        "_framework/QUESTION-BANK.md", "_framework/DIAGRAMS.md",
        "_framework/CONVERSATIONAL-WORKFLOW.md",
        "_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md",
        "starter/AGENTS.md", "starter/README.md.template",
        "starter/.gitignore", "starter/.gitattributes",
        "starter/_control/WORKSPACE.json.template", "starter/_control/PHASES.md",
        "starter/_control/STATE.md", "starter/_control/PROJECT-RULES.md",
        "starter/_control/registry/MANIFEST.md", "starter/_control/registry/INDEX.md",
        "starter/_control/registry/APPROVALS.md", "starter/_control/registry/DECISIONS.md",
        "starter/_control/registry/ASSUMPTIONS.md", "starter/_control/registry/QUESTIONS.md",
        "starter/_control/registry/RISKS.md", "starter/_control/registry/GLOSSARY.md",
        "starter/_control/registry/CHANGELOG.md", "starter/_control/logs/status-transitions.jsonl",
        "starter/docs/README.md", "starter/docs/04-architecture/adr/README.md",
        "starter/docs/99-appendix/research/README.md",
        "src/blueprint_framework/__init__.py", "src/blueprint_framework/source_cli.py",
        "src/blueprint_framework/build.py", "src/blueprint_framework/package.py",
    )
    if scope == "bootstrap":
        return [paths.root / item for item in runtime]
    if scope != "maintainer":
        raise ValueError(f"Unknown source verification scope: {scope!r}")
    maintained = (
        ".gitignore", ".gitattributes", "README.md", "DEVELOPMENT.md", "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md", "SECURITY.md",
        "framework-dev/README.md", "framework-dev/CHANGELOG.md", "framework-dev/RELEASE-CHECKLIST.md",
        "framework-dev/SOURCE-MANIFEST.json", "framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md",
        "framework-dev/tests/README.md", "framework-dev/tests/fixtures/regression-baseline.json",
        "framework-dev/tests/fixtures/v2.3.2-fingerprint-golden.json",
        "framework-dev/tests/fixtures/v2.3.2-profile-snapshot.json",
        "framework-dev/tests/test_workspace_paths.py", "framework-dev/tests/test_source_cli.py",
        "framework-dev/tests/test_compatibility_regressions.py", "framework-dev/tests/test_release_readiness.py",
        "framework-dev/tests/test_integrity_contracts.py", "framework-dev/tests/test_agent_instructions.py",
        "framework-dev/tests/test_source_verification.py", "framework-dev/tests/test_release_builder.py", "framework-dev/tests/workspace_fixture.py",
        "tools/agent-bootstrap/bootstrap.py", "tools/agent-bootstrap/tests/test_bootstrap.py",
        "tools/release/build_release.py",
    )
    return [paths.root / item for item in (*runtime, *maintained)]


def validate_v3_documentation_paths(paths: SourcePaths, *, include_maintainer_docs: bool = True) -> list[str]:
    """Reject active v2.x workspace commands/paths in current v3 operating docs.

    Explicitly labeled historical appendices, when present, are excluded from
    the active-instruction scan; current workspace instructions are still checked.
    """
    import re

    patterns = {
        "legacy workspace command": re.compile(r"python\s+tools/blueprint\.py"),
        "legacy runtime path": re.compile(r"(?<!_framework/)tools/blueprint\.py"),
        "duplicated framework runtime path": re.compile(r"_framework/_framework/tools/blueprint\.py"),
        "legacy registry root": re.compile(r"(?<!_control/)registry/"),
        "legacy state root": re.compile(r"(?<!_control/)STATE\.md"),
        "legacy logs root": re.compile(r"(?<!_control/)logs/"),
        "legacy workflow plan filename": re.compile(r"(?<![\w-])PLAN\.md"),
        "legacy agent filename": re.compile(r"AGENT\.md"),
        "maintainer-only repository path": re.compile(r"\bframework-dev(?:[\\/]|\b)", re.IGNORECASE),
        "maintainer test discovery command": re.compile(r"python(?:\s+-B)?\s+-m\s+unittest\s+discover", re.IGNORECASE),
    }
    candidates: list[Path] = []
    for base in (paths.root / "_framework", paths.starter):
        if base.exists():
            candidates.extend(sorted(base.rglob("*.md")))
    if include_maintainer_docs:
        candidates.extend([
            paths.root / "README.md",
            paths.framework_dev / "README.md",
            paths.framework_dev / "RELEASE-CHECKLIST.md",
        ])
    issues: list[str] = []
    seen: set[Path] = set()
    for file in candidates:
        if not file.is_file() or file in seen:
            continue
        seen.add(file)
        try:
            content = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"Cannot inspect v3 operating documentation {file}: {exc}")
            continue
        if file == (paths.root / "_framework" / "GUIDE.md"):
            # Do not treat an explicitly historical appendix as current instructions.
            marker = "## Appendix B: Historical v2.3.2 audit and verification record"
            if marker in content:
                content = content.split(marker, 1)[0]
        relative = file.relative_to(paths.root).as_posix()
        is_workspace_document = relative.startswith("_framework/") or relative.startswith("starter/")
        for label, pattern in patterns.items():
            if label in {"maintainer-only repository path", "maintainer test discovery command"} and not is_workspace_document:
                continue
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                issues.append(f"Active v3 documentation contains {label} in {relative}:{line}: {match.group(0)}")
    return issues

def verify_source(paths: SourcePaths, run_tests: bool = False, scope: str = "maintainer") -> tuple[bool, list[str]]:
    """Validate runtime-only bootstrap inputs or the full maintained source tree."""
    import ast
    import json
    import os
    import re
    import subprocess

    issues: list[str] = []
    version_text = ""
    try:
        version_text = paths.version.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        issues.append(f"Cannot read source VERSION: {exc}")
    if version_text:
        import re
        if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version_text):
            issues.append(f"VERSION is not a supported semantic version: {version_text!r}")

    if scope not in {"bootstrap", "maintainer"}:
        issues.append(f"Unknown source verification scope: {scope!r}")
    if scope == "bootstrap" and run_tests:
        issues.append("Bootstrap verification does not run maintainer tests; use maintainer scope for --tests")
    try:
        required_files = _required_source_files(paths, scope)
    except ValueError as exc:
        issues.append(str(exc))
        required_files = []
    for file in required_files:
        if not file.is_file():
            issues.append(f"Required {scope} source file is missing: {file.relative_to(paths.root).as_posix()}")

    source_license = paths.root / "LICENSE"
    starter_license = paths.starter / "LICENSE"
    if source_license.is_file() and starter_license.is_file():
        try:
            source_bytes = source_license.read_bytes()
            starter_bytes = starter_license.read_bytes()
            if source_bytes != starter_bytes:
                issues.append("LICENSE and starter/LICENSE must be byte-identical Apache-2.0 license texts")
            if b"Apache License" not in source_bytes[:256] or b"Version 2.0, January 2004" not in source_bytes[:512]:
                issues.append("LICENSE must contain the canonical Apache License 2.0 text")
        except OSError as exc:
            issues.append(f"Cannot verify Apache-2.0 license files: {exc}")

    issues.extend(validate_v3_documentation_paths(paths, include_maintainer_docs=(scope == "maintainer")))

    try:
        template = json.loads(paths.starter_workspace_seed.read_text(encoding="utf-8"))
        if (isinstance(template.get("workspace_schema_version"), bool)
                or template.get("workspace_schema_version") != 1
                or isinstance(template.get("layout_version"), bool)
                or template.get("layout_version") != 1):
            issues.append("Starter WORKSPACE.json.template must declare integer workspace schema 1 and layout 1")
        if template.get("project", {}).get("name") != "{{PROJECT_NAME}}":
            issues.append("Starter WORKSPACE.json.template must use the {{PROJECT_NAME}} seed value")
        if template.get("profile") not in {"lite", "standard", "exhaustive"}:
            issues.append("Starter WORKSPACE.json.template has an unsupported profile")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
        issues.append(f"Starter workspace configuration template is invalid: {exc}")

    if (paths.starter / "_control" / "WORKSPACE.json").exists():
        issues.append("Starter must contain WORKSPACE.json.template, never a live WORKSPACE.json")
    if (paths.starter / "bp.py").exists():
        issues.append("Starter must not maintain a second bp.py launcher copy")
    if (paths.starter / "AGENT.md").exists():
        issues.append("Starter must use AGENTS.md, not the legacy AGENT.md filename")

    agents = paths.starter / "AGENTS.md"
    if agents.is_file():
        issues.extend(validate_agents_instructions(agents))
    readme_template = paths.starter / "README.md.template"
    if readme_template.is_file():
        try:
            readme = readme_template.read_text(encoding="utf-8")
            for obsolete in ("python tools/blueprint.py", "AGENT.md", "registry/WORKSPACE.json", "tools/blueprint.py"):
                if obsolete in readme:
                    issues.append(f"Starter README contains an obsolete v2 command/path reference: {obsolete}")
            for required_phrase in ("First-session prompt", "Python **3.11 or newer**", "did **not** run `git init`", "_control/registry/INDEX.md"):
                if required_phrase not in readme:
                    issues.append(f"Starter README is missing required first-run guidance: {required_phrase}")
        except (OSError, UnicodeError) as exc:
            issues.append(f"Cannot read starter README template: {exc}")

    # The starter is deliberately documentation-light; only navigation and
    # guidance seeds are allowed under docs/ before D0.02 is accepted.
    allowed_docs = {
        "README.md", "04-architecture/adr/README.md",
        "99-appendix/research/README.md",
    }
    docs_root = paths.starter / "docs"
    if docs_root.exists():
        for item in docs_root.rglob("*"):
            if item.is_file():
                relative = item.relative_to(docs_root).as_posix()
                if relative not in allowed_docs:
                    issues.append(f"Starter contains an unexpected project document seed: docs/{relative}")

    # Require source text to be valid UTF-8/LF; never silently normalize the
    # canonical source while verifying it.
    text_suffixes = {".md", ".py", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".toml", ".csv", ".xml", ".svg"}
    scan_roots = (
        (paths.root / "_framework", paths.starter, paths.source_modules,
         paths.root / "VERSION", paths.launcher, paths.marker)
        if scope == "bootstrap" else (paths.root,)
    )
    scan_files: set[Path] = set()
    for scan_root in scan_roots:
        if scan_root.is_file():
            scan_files.add(scan_root)
        elif scan_root.is_dir():
            scan_files.update(scan_root.rglob("*"))
    for item in sorted(scan_files, key=lambda value: value.as_posix()):
        try:
            relative_parts = item.relative_to(paths.root).parts
        except ValueError:
            continue
        if any(part in {".git", "dist", "__pycache__"} for part in relative_parts) or item.suffix == ".pyc":
            continue
        if not item.is_file():
            continue
        is_text = item.suffix.lower() in text_suffixes or item.name in {".gitignore", ".gitattributes", "README.md.template"}
        if not is_text:
            continue
        try:
            raw = item.read_bytes()
            raw.decode("utf-8")
            if raw.startswith(b"\xef\xbb\xbf"):
                issues.append(f"Text file has a UTF-8 BOM: {item.relative_to(paths.root).as_posix()}")
            if b"\r" in raw:
                issues.append(f"Text file is not LF-normalized: {item.relative_to(paths.root).as_posix()}")
        except (OSError, UnicodeError) as exc:
            issues.append(f"Text file is not valid UTF-8: {item.relative_to(paths.root).as_posix()}: {exc}")

    # Root launcher and Git-hygiene seeds are copied into every workspace;
    # validate their exact source bytes before the build can proceed.
    for item in (paths.launcher, paths.starter / ".gitattributes", paths.starter / ".gitignore", paths.root / ".gitattributes", paths.root / ".gitignore"):
        if not item.is_file():
            continue
        try:
            raw = item.read_bytes()
            raw.decode("utf-8")
            if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
                issues.append(f"Root packaged text must be UTF-8 without BOM/LF: {item.name}")
        except (OSError, UnicodeError) as exc:
            issues.append(f"Root packaged text is not valid UTF-8: {item.name}: {exc}")

    # Parse, but do not import, every maintained Python source file.
    ast_roots = (paths.root / "_framework", paths.source_modules)
    if scope == "maintainer":
        ast_roots += (paths.framework_dev / "tests", paths.root / "tools")
    for scan_root in ast_roots:
        if not scan_root.exists():
            continue
        for item in scan_root.rglob("*.py"):
            if "__pycache__" in item.parts:
                continue
            try:
                ast.parse(item.read_text(encoding="utf-8"), filename=str(item))
            except (OSError, UnicodeError, SyntaxError) as exc:
                issues.append(f"Python source does not parse: {item.relative_to(paths.root).as_posix()}: {exc}")

    # Symlinks in packaged input trees are not accepted: following them could
    # add files outside the source roots or make output host-dependent.
    symlink_roots = (paths.starter, paths.root / "_framework", paths.source_modules)
    if scope == "maintainer":
        symlink_roots += (paths.framework_dev, paths.root / "tools", paths.root / "release-assets")
    for scan_root in symlink_roots:
        if scan_root.exists():
            for item in scan_root.rglob("*"):
                if item.is_symlink():
                    issues.append(f"Symlinks are not allowed in packaged source trees: {item.relative_to(paths.root).as_posix()}")

    if run_tests and not issues:
        tests = paths.tests
        bootstrap_tests = paths.root / "tools" / "agent-bootstrap" / "tests" / "test_bootstrap.py"
        if not tests.is_dir():
            issues.append("framework-dev/tests is missing; cannot run maintainer verification tests")
        else:
            env = dict(os.environ)
            # Each maintainer test module and its workspace-facing subprocess
            # helpers use ``python -B`` where bytecode writes would affect
            # assertions. Do not export PYTHONDONTWRITEBYTECODE globally: it
            # makes every disposable workspace CLI invocation recompile the
            # full runtime. Also replace, rather than append to, ambient
            # PYTHONPATH so another checkout cannot shadow this source tree in
            # copied-source integration tests.
            test_paths = (tests, paths.source_modules.parent, paths.root / "_framework" / "tools")
            env["PYTHONPATH"] = os.pathsep.join(str(item) for item in test_paths)
            test_modules = sorted(tests.glob("test_*.py"), key=lambda item: item.name)
            if bootstrap_tests.is_file():
                test_modules.append(bootstrap_tests)
            if not test_modules:
                issues.append("No maintained test_*.py modules were found")
            executed_test_count = 0
            for test_file in test_modules:
                try:
                    module_ast = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
                    executed_test_count += sum(
                        1 for node in ast.walk(module_ast)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
                    )
                except (OSError, UnicodeError, SyntaxError) as exc:
                    issues.append(f"Cannot count maintainer tests in {test_file.name}: {exc}")
                    continue
                command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(test_file.parent), "-p", test_file.name, "-v"]
                print(f"\n=== Maintainer test module: {test_file.relative_to(paths.root).as_posix()} ===", flush=True)
                try:
                    result = subprocess.run(command, cwd=paths.root, env=env, timeout=300)
                except subprocess.TimeoutExpired:
                    issues.append(f"Maintainer test module {test_file.name} exceeded the 300-second verification limit")
                    return False, issues
                if result.returncode != 0:
                    issues.append(f"Maintainer test module {test_file.name} failed (exit {result.returncode})")
                    return False, issues
            if not issues:
                print(f"Maintainer test modules passed: {len(test_modules)}; test methods: {executed_test_count}", flush=True)

    return not issues, issues


def main(argv: list[str] | None = None) -> int:
    from .build import build_workspace
    from .package import create_workspace

    try:
        paths = SourcePaths.from_root(Path(__file__).resolve().parents[2])
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: cannot identify framework source repository: {exc}")
        return 2

    version = paths.version.read_text(encoding="utf-8").strip()
    parser = argparse.ArgumentParser(prog="bp.py", description="Project Blueprint Framework source-maintenance commands")
    parser.add_argument("--version", action="version", version=f"Project Blueprint Framework source {version}")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify the source tree and optionally run active tests")
    verify.add_argument("--tests", action="store_true", help="run the maintained regression and tooling test suite (maintainer scope only)")
    verify.add_argument("--scope", choices=("maintainer", "bootstrap"), default="maintainer",
                        help="maintainer verifies the full developer tree; bootstrap verifies only workspace-creation inputs")

    build = sub.add_parser("build", help="build and freshly verify the workspace starter ZIP")
    build.add_argument("--skip-tests", action="store_true", help="skip active tests (development use only; not recommended for release builds)")

    new = sub.add_parser("new", help="create a project documentation workspace from an existing built package")
    new.add_argument("--name", required=True, help="project display name")
    new.add_argument("--destination", help="workspace destination; defaults to a sibling <slug>-Blueprint folder")
    new.add_argument("--package", help="already-built workspace ZIP; defaults to dist/project-blueprint-workspace-<VERSION>.zip")

    args = parser.parse_args(argv)
    if args.command == "verify":
        print(f"Source verification environment: Python {sys.version.split()[0]} | {sys.platform} | {__import__('platform').machine()}")
        ok, issues = verify_source(paths, run_tests=args.tests, scope=args.scope)
        if issues:
            for issue in issues:
                print(f"ERROR: {issue}")
            return 1
        success_label = "Source verification passed" if args.scope == "maintainer" else "Bootstrap source verification passed"
        print(success_label + f" ({args.scope} scope)." + (" Maintainer tests passed." if args.tests else " (tests not requested)."))
        return 0
    if args.command == "build":
        return build_workspace(paths, run_tests=not args.skip_tests)
    if args.command == "new":
        return create_workspace(paths, name=args.name, destination=args.destination, package=args.package)
    parser.error("unknown source command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
