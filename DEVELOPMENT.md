# Development Guide

This document describes how to work on the PBF developer repository and produce the ordinary user-facing release.

## 1. Development boundaries

PBF has three distinct deliverables or working forms:

1. **Developer repository:** full maintained source, tests, architecture and release tooling.
2. **Agent-First Release ZIP:** the single product artifact generated for ordinary users.
3. **Generated project workspace:** an instance created from the workspace starter by `bp.py new`.


Do not change the accepted workspace architecture revision 1.3.4 as part of a packaging or onboarding change. If a concrete defect appears to require an architectural change, document the defect, trade-off and proposed revision before changing the design.

## 2. Environment

Use CPython 3.11 or newer. The build and runtime tooling use the Python standard library; there is no dependency-install step. Git is recommended for source history and is exercised by a Git line-ending regression test when available.

Check the interpreter and source identity:

```bash
python --version
python -B bp.py --version
```

### First-time Git repository setup

This developer package is a clean source snapshot. It intentionally contains no `.git/` directory or previous commit history. The root `.gitignore` and `.gitattributes` are included. Secret-directory exclusions are anchored to the workspace root so nested documentation directories named `secrets/` or `credentials/` remain trackable. The conservative `*.pem`, `*.key`, `*.p12`, `*.pfx` and `*.keystore` rules apply at any depth; force-add a matching asset only after verifying that it contains no private key or secret material.

After extracting the package, open a terminal at the repository root. Create an empty remote repository first, then initialize the local snapshot. Before adding files, configure the intended Git author identity. When publishing on GitHub, use the account's GitHub-provided no-reply address if you do not want a personal email address exposed in commit metadata.

```bash
git init
git config user.name "YOUR_PUBLIC_AUTHOR_NAME"
git config user.email "YOUR_GITHUB_NO_REPLY_ADDRESS"
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git add .
git status --short
git diff --cached --stat
git commit -m "Initial PBF developer repository"
git log --format="Author: %an <%ae>%nCommitter: %cn <%ce>" -1
git branch -M main
git remote add origin YOUR_REMOTE_URL
git push -u origin main
```

Replace `YOUR_REMOTE_URL` with the URL of your own empty remote repository. PowerShell uses the same commands. Confirm both author and committer identities and the staged files before committing; changing the identity later does not rewrite existing commit history. Use a GitHub-provided no-reply address if you do not want a personal email exposed. The generated `dist/` directory is ignored and should not be committed as source; the Agent-First Release ZIP can be attached separately to a Git hosting release when appropriate. Do not force-push over an existing remote history. If the remote is not empty, reconcile its contents deliberately before pushing.

The project is licensed under Apache-2.0; retain the root `LICENSE` file in every source and product distribution. Do not remove or replace it without an approved licensing decision.

## 3. Repository map

- `_framework/`: canonical workspace runtime and project-facing framework reference material.
- `starter/`: inputs copied into the generated workspace starter package.
- `src/blueprint_framework/`: source-only commands, build and package implementation.
- `framework-dev/architecture/`: normative architecture specification.
- `framework-dev/tests/`: active maintained tests and small golden/baseline fixtures.
- `release-assets/`: authored inputs copied into the outer release.
- `tools/agent-bootstrap/`: bootstrap implementation and test suite.
- `tools/release/`: full release build compiler and its tests.
- `dist/`: generated artifacts and local build evidence; ignored by Git.

## 4. Verification scopes

Bootstrap verification and maintainer verification intentionally differ.

```bash
python -B bp.py verify --scope bootstrap
python -B bp.py verify
python -B bp.py verify --tests
```

- `bootstrap` verifies only the launcher, source marker, version, workspace runtime, framework defaults, starter and source modules required for workspace creation. It does not require maintainer tests or development records.
- `maintainer` (the default) verifies the complete maintained source tree, documentation, source files, tests, release assets and tools.
- `maintainer --tests` also executes all maintained test modules in separate interpreter processes.

The bootstrap scope is what ships inside the user-facing runtime bundle. The maintainer scope is what is expected in a developer checkout.

## 5. Workspace starter build

```bash
python -B bp.py build
```

This command performs maintainer verification and runs the maintained test suite by default. It builds the project-neutral workspace starter, extracts and validates a materialized copy, packages the exact candidate ZIP and validates the archive by fresh extraction before publishing it under `dist/`.

`--skip-tests` is available for narrow local iteration only. It must not be used to claim that a release passed the maintained test gate.

## 6. Full Agent-First Release build

```bash
python -B tools/release/build_release.py
```

The full builder reads only the root `VERSION` value. It then verifies the developer tree and tests, calls the existing `bp.py build` workflow, assembles the curated bootstrap runtime, creates the nested agent package, creates the outer Agent-First Release and verifies the exact final ZIP through extraction and disposable end-to-end bootstrap.

The normal output is exactly:

```text
dist/PBF-v<VERSION>-Agent-First-Release.zip
```

The builder does not consume a previous release ZIP as an input. It uses the authored release inputs under `release-assets/` and the current source tree. It generates checksums and manifests each time. `--force` is required to replace an existing final release artifact.

Local build logs and intermediate archives remain in ignored `dist/` subdirectories. Only concise sanitized verification evidence is included in the user-facing ZIP.

## 7. Making changes safely

1. Read `framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md` before changing runtime or workspace structure.
2. Identify the owning source file and any generated/canonical counterpart. Do not edit generated release ZIPs as the source of truth.
3. Add or update focused tests. Keep the 94 compatibility regression methods and the two golden fixtures unless a separately justified behavior change is approved.
4. Run the smallest relevant test module while iterating.
5. Run `python -B bp.py verify --tests` before treating the maintained source tree as validated.
6. Run the full release builder to validate the complete product distribution.
7. Inspect the final archive and compare its manifests/checksums; do not rely solely on the builder's success message.

Do not commit credentials, secret values, private user data, machine-specific paths or raw operational logs. Record enduring architectural decisions in the architecture specification and release-level changes in the changelog.

## 8. Compatibility and security claims

Python 3.11+ is the declared minimum. Do not claim that every Python minor version, native Windows environment or AI harness has been tested unless a reproducible test result establishes that claim. Procedural agent instructions do not grant OS privileges or establish a sandbox. Checksums detect inconsistency relative to the included checksum list but are not publisher signatures.

## 9. Version and license discipline

The root `VERSION` is the only authoritative framework version input. Workspace architecture revision 1.3.4 is separate and remains unchanged unless an explicit architecture decision is made.

The project uses Apache-2.0 for PBF-provided components. The root `LICENSE` and `starter/LICENSE` must remain byte-identical and must propagate into the outer release, nested agent package, bootstrap runtime and generated workspace. The generated workspace must also contain `starter/PBF-LICENSE-SCOPE.md` so the PBF license is not mistaken for a license on owner-authored project content or third-party material. `verify` and release-asset validation check these files.
