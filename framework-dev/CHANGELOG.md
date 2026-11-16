# Changelog

This changelog records meaningful framework-level changes.

## 3.0.0 — Stable release

- Established the canonical documentation workspace with distinct `docs/`, `_framework/` and `_control/` ownership.
- Accepted workspace architecture revision 1.3.4.
- Centralized workspace path resolution and separated `SourcePaths` from `WorkspacePaths`.
- Established the single root `VERSION` input and generated framework integrity manifest.
- Added safe workspace starter packaging and `bp.py new` creation/verification.
- Preserved compatibility behavior through 94 regression tests and golden fixtures.
- Added state reconciliation, dependency applicability and completion-reporting contracts.
- Established a portable agent-operating contract without claiming universal harness compatibility.
- Added the Agent-First distribution, curated bootstrap runtime, and reproducible full release build process.

### Validation, distribution and developer workflow improvements

- Use forward scanners for HTML comments and Markdown link extraction to keep malformed-input processing bounded and predictable.
- Keep the 2,048-character parsing limit for local link targets while accepting syntactically valid long external URIs, including HTTP(S) links and data images.
- Report malformed external URI syntax, invalid/overlong local link targets and unterminated HTML comments as source-located validation findings instead of silently masking content or terminating the workspace check.
- Include Apache-2.0 licensing information with developer, agent, runtime and generated workspace distributions.
- Clarify that Apache-2.0 covers PBF-provided framework components and does not automatically license owner-authored project content or third-party material in generated workspaces.
- Include community, contribution and private security-reporting guidance for the public repository.
- Keep generated verification evidence free of host-specific identifiers while preserving observed test results and artifact digests.
- Use neutral path examples, verify Git author and committer identity before the first commit, and provide root-scoped secret-directory exclusions.
- Apply explicit LF handling to `*.template` files and isolate maintainer test execution from ambient `PYTHONPATH`.

## 2.3.3 compatibility baseline

PBF v3.0.0 preserves selected workspace behavior and compatibility fingerprints established by the v2.3.3 baseline. The maintained regression identities and one-to-one port mapping are recorded in `tests/fixtures/regression-baseline.json`; the superseded source archive and migration accounting are not required by current verification.
