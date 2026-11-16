# Framework Development References

This directory contains maintainer-only documentation and active test material. It is not copied into a generated project workspace. Only selected product documentation from `release-assets/` is included in the ordinary Agent-First Release.

## Contents

- `architecture/V3.0-WORKSPACE-ARCHITECTURE.md` — normative PBF v3.0.0 architecture specification, accepted workspace architecture revision 1.3.4.
- `tests/` — maintained regression, path, source-verification, CLI, release-readiness and integrity tests plus compact fixtures.
- `SOURCE-MANIFEST.json` — source identity marker used by source/workspace mode selection.
- `CHANGELOG.md` — concise release-level change history.
- `RELEASE-CHECKLIST.md` — current gates for the single Agent-First Release ZIP.

Development setup and commands are in the repository-root `DEVELOPMENT.md`. Contribution expectations are in `CONTRIBUTING.md`.

Keep this directory focused on the current architecture, maintained tests, source identity and release-maintenance references. Record enduring decisions in the architecture specification and release-level changes in the changelog.
