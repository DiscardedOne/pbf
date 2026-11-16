# Project Blueprint Framework v{{PBF_VERSION}} — Maintainer Handbook

This document describes the supported maintenance and release-production workflow. It is included as a reference in the Agent-First release; the full source repository and tests are maintained separately in the developer repository.

## 1. Source repository and ownership

The developer repository is the authoritative source of PBF. Its principal areas are:

| Path | Purpose |
|---|---|
| `VERSION` | Sole framework release-version input |
| `_framework/` | Canonical reusable workspace runtime and reference material |
| `starter/` | Project-neutral workspace seed inputs |
| `src/blueprint_framework/` | Source-only CLI, build and package implementation |
| `framework-dev/architecture/` | Accepted architecture specification, revision 1.3.4 |
| `framework-dev/tests/` | Maintained regression suite and compact fixtures |
| `release-assets/` | Authored user documentation and agent setup instructions |
| `tools/agent-bootstrap/` | Bootstrap helper and tests |
| `tools/release/` | Full Agent-First Release compiler |
| `dist/` | Generated output, ignored by Git |

The generated project workspace is a separate artifact. Do not copy developer tests, release tooling, maintenance records or private working notes into it.

## 2. Development environment

- CPython 3.11 or newer is the declared minimum.
- Source tests and packaging tools use the Python standard library.
- Run commands from the developer repository root with an explicit interpreter.
- Keep generated workspaces and temporary tests outside the source tree.
- Do not edit generated ZIPs as the source of truth.

The release evidence records the actual environment used for the build. Native Windows and complete test execution across every supported Python minor are not claimed unless separately verified.

## 3. Verification and tests

```bash
python -B bp.py verify --scope bootstrap
python -B bp.py verify
python -B bp.py verify --tests
```

`bootstrap` verifies only the files needed for workspace creation. `maintainer` is the default and verifies the full maintained developer tree. `maintainer --tests` additionally runs all maintained source and bootstrap test modules in separate Python processes.

The current maintained test inventory contains 235 methods under `framework-dev/tests/` and 19 focused bootstrap-helper methods, for 254 total methods. The 94 compatibility regressions have one-to-one port mappings in `framework-dev/tests/fixtures/regression-baseline.json`; source verification depends only on the maintained fixture and current source tree.

Run a focused module during development with:

```bash
PYTHONPATH=framework-dev/tests:src:_framework/tools python -B -m unittest discover -s framework-dev/tests -p test_source_verification.py -v
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "framework-dev/tests;src;_framework/tools"
python -B -m unittest discover -s framework-dev/tests -p test_source_verification.py -v
Remove-Item Env:PYTHONPATH
```

## 4. Workspace starter build

```bash
python -B bp.py build
```

This validates the maintained source and runs the full maintained suite by default. It generates the framework integrity manifest from `VERSION`, assembles the project-neutral workspace starter, validates a materialized workspace and freshly extracts the exact candidate ZIP for final verification.

Output: `dist/project-blueprint-workspace-<VERSION>.zip`. This is not a live project workspace; use `bp.py new` to instantiate it.

## 5. Agent bootstrap helper

The bootstrap helper is a distribution tool. It does not replace the source CLI or reimplement workspace creation. Its role is to verify its package and curated runtime, then call the existing `bp.py new` command.

Required invariants:

- Standard-library-only; no package installation or network calls.
- Exact package inventory and checksum verification, including manifest-declared runtime/workspace archive hashes.
- Safe ZIP inspection and extraction; reject path traversal, absolute/drive paths, unsafe components, symlinks, encryption, duplicate/case/Unicode aliases, parent-component collisions and file/directory conflicts.
- Require a non-existing destination and existing writable parent; never overwrite or merge.
- Require the agent to obtain human approval for the exact path; the helper's repeated approved path is only an invocation guard.
- Verify the extracted runtime with `bp.py verify --scope bootstrap`, then invoke `bp.py new` with the workspace starter.
- Run `check --strict`, `index --check` and `audit-state --strict`.
- Preserve a created workspace after a post-creation failure and remove only helper-created temporary runtime extraction.
- Emit a machine-readable `PBF_BOOTSTRAP_RESULT` and truthful exit status.

Run the helper's focused tests from the repository root:

```bash
PYTHONPATH=framework-dev/tests:src:_framework/tools python -B -m unittest discover -s tools/agent-bootstrap/tests -p 'test_*.py' -v
```

## 6. Full release compilation

The authoritative release command is:

```bash
python -B tools/release/build_release.py
```

The builder reads the root `VERSION`, validates the maintained source, runs the maintained tests, calls the existing workspace starter build, creates the curated bootstrap runtime ZIP, assembles the nested agent package, then assembles and verifies the outer Agent-First Release ZIP.

The normal output is exactly:

```text
dist/PBF-v<VERSION>-Agent-First-Release.zip
```

The builder uses deterministic ZIP metadata, generates manifests and checksums, verifies the exact final archive and performs an end-to-end bootstrap into a disposable destination. Raw build logs stay under ignored `dist/` and are not included in the user-facing package. Only concise current-build evidence is shipped.

An existing final release is not replaced unless `--force` is explicitly supplied. A failed candidate build must preserve any previously published output.

## 7. Release asset maintenance

The `release-assets/` directory is the authored input for the outer release. Update these source files rather than editing a previously generated ZIP:

- `README-RELEASE.md` and `QUICKSTART.md` — end-user entry points.
- `docs/` — six consolidated references and an index.
- `agent/AGENT-OPERATING-INSTRUCTIONS.md` and `agent/AGENT-STARTUP-PROMPT.md` — agent onboarding contract.

Keep documentation flat under `docs/`. Verify links, filenames, commands and package descriptions against the actual generated archive. Keep credentials, secret values, private user data, machine-specific paths and raw operational logs out of release assets.

## 8. Compatibility, security and licensing

Python 3.11 or newer is the declared minimum. Do not claim native Windows support, universal AI-harness compatibility or a complete Python-version matrix without evidence. Agent instructions do not create an OS-level sandbox. For public downloads, users compare the outer ZIP SHA-256 with the digest in the official GitHub Release description; this relies on trust in the project GitHub account/repository and is not a detached signature.

PBF is licensed under Apache License 2.0 (`Apache-2.0`). Preserve the root `LICENSE` and ensure the release compiler propagates it to every applicable distribution layer.
