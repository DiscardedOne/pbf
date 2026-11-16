# Project Blueprint Framework — Architecture and Technical Reference

This document describes the stable PBF v{{PBF_VERSION}} architecture, generated workspace, source/runtime boundaries, CLI behavior, setup contract, validation and compatibility limits. The normative workspace architecture is `framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md` in the developer repository; executable source and tests remain authoritative for implemented behavior.

## 1. System boundaries

PBF is a reusable methodology and supporting software for collaboratively exploring, planning, documenting and maintaining projects across domains, including software, hardware, embedded systems, research, products, operations and hybrid initiatives. Its documentation architecture adapts to the project's domain, complexity and engineering requirements. PBF structures and documents the work; it does not perform the underlying engineering or replace specialist design, simulation, prototyping, manufacturing or validation tools. It is not an AI model, autonomous agent or execution sandbox.

Three actors have distinct responsibilities:

| Actor | Responsibility |
|---|---|
| Human owner | Supplies project vision, domain knowledge, context, priorities, decisions, approvals and corrections. |
| AI agent | Performs discovery, research, analysis, synthesis, documentation and validation within actual tool access and permissions. |
| PBF | Supplies methodology, instructions, templates, state management, registers, runtime commands and validation procedures. |

PBF is designed to be harness-neutral. That is an architectural goal, not a claim of universal compatibility. Harnesses differ in filesystem access, persistence, instruction loading, execution tools, context limits and security controls.

## 2. Developer repository, bootstrap runtime and workspace

These are separate artifacts with different audiences.

### 2.1 Developer repository

The developer repository is the maintainer's complete working tree. It contains the source, maintained tests, architecture specification, development documentation, authored release assets and release compiler. It is the authoritative input for future changes.

Its important areas are:

- `VERSION`: the single authoritative framework release version.
- `bp.py`: the source/workspace command dispatcher.
- `_framework/`: canonical framework runtime material and its source-side tools.
- `starter/`: the seed files used to generate a new workspace.
- `src/blueprint_framework/`: source-only CLI, build, package and verification implementation.
- `framework-dev/`: source manifest, accepted architecture, changelog, release checklist and maintained tests.
- `release-assets/`: authored user documentation and agent onboarding material used by the release compiler.
- `tools/agent-bootstrap/`: bootstrap implementation and its tests.
- `tools/release/`: deterministic Agent-First release compiler.
- `dist/`: ignored generated output; the normal release build produces one product ZIP.

### 2.2 Curated bootstrap runtime

The nested agent package contains a small bootstrap runtime ZIP rather than the full maintainer repository. It contains only the source CLI dependencies and files needed to verify the bootstrap scope and invoke the existing workspace-generation command. It excludes maintainer tests and release-building tools.

The bootstrap runtime is temporary setup material. The agent extracts it into a new temporary directory, verifies it, invokes `bp.py new`, and removes only that temporary extraction after the operation. It is not copied into the live project workspace.

### 2.3 Workspace starter and live workspace

The workspace starter ZIP is produced by the existing `bp.py build` workflow. It contains the reusable runtime and starter files, but no maintainer source tree, test suite, source identity marker or release-builder code.

The live workspace is created by `bp.py new` from that already-built starter. The starter has `_control/WORKSPACE.json.template`; a generated workspace has a live `_control/WORKSPACE.json`. Workspace creation does not initialize Git and does not generate the entire possible document catalog.

## 3. Accepted workspace architecture

Workspace architecture revision **1.3.4** is accepted and remains stable for PBF v{{PBF_VERSION}}. The canonical top-level structure is:

```text
<ProjectName>-Blueprint/
├── README.md
├── AGENTS.md
├── bp.py
├── .gitignore
├── .gitattributes
├── docs/
├── _framework/
└── _control/
```

The three main directories have non-overlapping responsibilities:

- `docs/`: project-specific knowledge and deliverables.
- `_framework/`: reusable methodology, operating instructions, templates, defaults and runtime.
- `_control/`: project-specific configuration, state, registers, approvals and continuity records.

The exact documents and directory groups under `docs/` are determined adaptively through discovery and the accepted D0.02 documentation architecture. PBF does not force every project to create every possible document.

### 3.1 Root entry points

| Path | Role |
|---|---|
| `README.md` | Project introduction and first-session guidance. |
| `AGENTS.md` | Portable agent operating contract. |
| `bp.py` | Thin context-aware CLI launcher. |
| `.gitignore` | Workspace version-control exclusions. |
| `.gitattributes` | Stable line-ending and text handling. |

Project-specific agent constraints belong in `_control/PROJECT-RULES.md`, not in the shared framework runtime.

### 3.2 `_control/` records

The workspace control area includes:

- `WORKSPACE.json`: live workspace identity, schema/layout and profile.
- `PHASES.md`: project phase configuration.
- `STATE.md`: concise current checkpoint, progress, focus, decisions and next action.
- `PROJECT-RULES.md`: project-specific agent constraints.
- `registry/MANIFEST.md`: operational document inventory and lifecycle metadata.
- `registry/INDEX.md`: generated document navigation.
- `registry/APPROVALS.md`: explicit owner approval evidence.
- `registry/DECISIONS.md`: material decisions and references.
- Assumption, question, risk, glossary and changelog registers.
- `logs/status-transitions.jsonl`: status transition history.

The new-workspace `STATE.md` contains an existing `Workspace setup provenance` field. Agent-assisted setup records a concise date, method, framework/Python versions and verification result there. This does not require a separate setup log.

## 4. Launcher, path resolution and version ownership

The root `bp.py` launcher determines whether it is operating in a source repository or a live workspace:

- Source mode is identified by `framework-dev/SOURCE-MANIFEST.json`.
- Workspace mode is identified by `_control/WORKSPACE.json`.
- The starter template `_control/WORKSPACE.json.template` is not a live workspace marker.

Source-only commands and workspace commands are intentionally separate. `SourcePaths` resolves the developer repository; `WorkspacePaths` resolves the live workspace. Workspace physical paths are centrally resolved and are not arbitrarily redirected by values in `WORKSPACE.json`.

`VERSION` is the sole release-version input in the developer repository. Workspace architecture revision `1.3.4` is a separate accepted architecture identifier; it is not another release version.

The framework integrity manifest is generated by the workspace build. Creating a workspace verifies an existing package and does not regenerate the manifest as a side effect.

## 5. Command-line operations

Run commands from the relevant repository or workspace root. Python **3.11 or newer** is the declared minimum. These commands use only the Python standard library.

### 5.1 Developer repository commands

```bash
python -B bp.py --version
python -B bp.py verify
python -B bp.py verify --tests
python -B bp.py build
```

`verify` defaults to maintainer scope. It checks the full maintained source tree and current source invariants. `verify --tests` also executes each maintained test module in a separate Python process, including the bootstrap-tool tests.

`build` runs maintained verification/tests by default, creates the project-neutral workspace starter and verifies a fresh materialization of that artifact. `build --skip-tests` is a development convenience and is not sufficient release evidence by itself.

### 5.2 Bootstrap runtime verification

The curated runtime supports:

```bash
python -B bp.py verify --scope bootstrap
```

Bootstrap scope checks only the files and documentation needed for workspace creation. It does not run the maintainer test suite. Passing bootstrap verification does not establish that the complete developer repository or all maintainer tests are present.

### 5.3 Workspace commands

The generated workspace supports commands including:

```bash
python -B bp.py check --strict
python -B bp.py index --check
python -B bp.py audit-state --strict
python -B bp.py status
```

The actual command surface is provided by `python -B bp.py --help` in a generated workspace. Strict checks, index validation and state audit are the standard post-creation checks used by the agent bootstrap. The state audit is read-only; it does not silently rewrite project state.

## 6. Agent-assisted setup contract

The recommended route is to provide the complete outer Agent-First Release ZIP to an agentic AI environment that has actual read/write access to a persistent destination and can execute Python 3.11 or newer.

The operating instructions require the agent to:

1. Verify the entire outer release inventory and cross-check the nested package path/hash in the outer manifest.
2. Safely extract and verify the nested agent package.
3. Check actual filesystem, terminal, Python and persistence capabilities.
4. Identify the working path visible to the agent and distinguish persistent from ephemeral storage.
5. Propose a project name and exact absolute destination, inspect the parent and detect conflicts.
6. Obtain the owner's explicit approval before creating anything.
7. Use the packaged helper for deterministic mechanical setup; the helper orchestrates the existing PBF CLI and does not reimplement workspace creation.
8. Verify the bootstrap runtime, invoke `bp.py new`, and run `check --strict`, `index --check` and `audit-state --strict`.
9. Read back generated instructions and project-control files, then write concise setup provenance to the existing `_control/STATE.md` field and rerun the state audit.
10. Remove only temporary files it created and report exact results and limitations.
11. Stop after reporting setup and ask whether the owner is ready to begin P0 discovery.

Setup and discovery are separate stages. The original prompt cannot authorize the agent to begin P0 automatically. The owner must confirm after successful setup.

The helper uses an exact destination-approval argument as a mechanical guard. That argument is not cryptographic proof of human approval; the agent must still obtain actual owner consent before invoking it.

## 7. Manual setup alternative

Agent-assisted setup is recommended, not mandatory. The user guide includes a manual workflow using the curated bootstrap runtime and workspace starter ZIP. The user can extract the runtime to a temporary directory, run `bp.py verify --scope bootstrap`, use `bp.py new --name ... --destination ... --package ...`, and run the generated workspace's strict/index/state checks.

The bootstrap helper is not a mandatory prerequisite for manual CLI setup. Manual workspace creation does not itself begin P0; discovery begins only when the owner chooses to start it.

## 8. Security and operational boundaries

PBF's safety properties should be described precisely:

- The package verifier and bootstrap helper reject unsafe archive paths, symbolic links, encrypted members, duplicate/ambiguous archive paths, checksum mismatches and unreasonable archive sizes/ratios.
- The helper refuses an existing destination; it does not overwrite or merge a workspace.
- It does not install Python or other system software, make network requests or initialize Git.
- It extracts the curated runtime temporarily and removes only the temporary directory it created on successful completion.
- If workspace creation succeeds but a later check fails, the partial destination is preserved for inspection; it is not automatically deleted.
- The helper does not provide an OS-level sandbox, constrain unrelated agent tools or prove that the owner approved a path.
- A container or cloud-agent path is not automatically a path on the owner's host machine. Persistence and access must be established in the actual environment.
- The public GitHub Release description publishes the outer ZIP SHA-256; compare it with the downloaded archive. The project GitHub account/repository is the publication trust source. This is not a detached signature and does not protect against compromise of that account or release.

The PBF distribution is licensed under Apache License 2.0 (`Apache-2.0`); the canonical license text is included as `LICENSE` in source and product distributions.

## 9. Compatibility and evidence

The declared minimum is Python 3.11. The cleaned maintained suite currently contains **235 framework/developer test methods** plus **19 bootstrap-tool test methods**, for **254 maintained test methods**. The release compiler's generated `release-evidence/BUILD-VERIFICATION.md` records the actual test count and results for the specific build. Do not substitute a historical result for that current build evidence.

The maintained suite and release compiler must be validated on the actual build environment. Python 3.11 and 3.12 full-suite coverage, native Windows execution, CI and additional AI harnesses are not established by design claims alone.

Cross-harness compatibility remains un-certified. A compatible harness must provide the needed file access, persistent storage, terminal/Python execution and explicit instruction loading. No universal agent behavior or OS-level isolation is claimed.

## 10. Release production

`tools/release/build_release.py` is the authoritative release compiler. It reads `VERSION`, performs maintainer verification/tests, runs the existing workspace build in an isolated temporary source copy, creates a curated bootstrap runtime ZIP, assembles the nested agent package and outer release, generates manifests/checksums and exercises the exact packaged bootstrap flow against a disposable destination.

The standard build output is one product artifact:

```text
dist/
└── PBF-v<VERSION>-Agent-First-Release.zip
```

Build logs may be retained locally under the ignored `dist/build-logs/` directory; raw logs are not copied into the user-facing release. The release includes concise generated verification evidence without host-specific environment fingerprints.

The final ZIP is deterministic for identical inputs and the same supported Python/zlib toolchain. Reproducibility must be demonstrated by actual clean builds; it should not be claimed across arbitrary Python/zlib versions without comparing outputs.

## 11. Versioning, migration and deferred capabilities

- PBF framework version is read only from the developer repository's root `VERSION` file.
- Workspace architecture revision **1.3.4** remains accepted.
- There is no general workspace upgrade or alpha-refresh mechanism.
- There is no v2.x workspace migration path.
- Creating a workspace does not initialize Git.
- The framework does not bulk-scaffold every possible document.
- Cross-harness certification, native Windows validation, macOS validation and CI are not implied by this release. The public release uses the project GitHub repository/account as its publication trust source and publishes the outer ZIP SHA-256 in the GitHub Release description; no detached digital signature is included.

These constraints should not be changed merely to simplify packaging. A proposed change needs an explicit technical reason, impact analysis and owner approval.
