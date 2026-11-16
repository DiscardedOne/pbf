# Project Blueprint Framework (PBF)

**Turn an evolving idea into a clear, structured and maintainable project blueprint — through human–AI collaboration.**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Release: v3.0.0](https://img.shields.io/badge/Release-v3.0.0-informational.svg)](https://github.com/DiscardedOne/pbf/releases)

Project Blueprint Framework (PBF) is an **adaptive, agent-agnostic framework for exploring, planning, documenting and maintaining projects**. It helps a project owner and an AI agent turn an early idea, incomplete brief or evolving initiative into a coherent, reviewable and traceable project baseline.

> 💡 **Start with the idea you have — not the specification you think you should already have.** PBF helps you discover what is missing, make decisions deliberately and preserve project knowledge in a durable workspace that can be continued across people, agents and sessions.

PBF is not limited to software. Its documentation approach adapts to projects involving **software, hardware, electronics, embedded systems, physical products, research, operations, infrastructure and hybrid systems**. It helps determine what needs to be understood and documented for a particular project instead of forcing every project into the same set of templates.

**Project links:** [Source repository](https://github.com/DiscardedOne/pbf) · [Releases and downloads](https://github.com/DiscardedOne/pbf/releases) · [Report an issue](https://github.com/DiscardedOne/pbf/issues)

> ⚡ **Get started in under 2 minutes:** [Download the official Agent-First Release ZIP](https://github.com/DiscardedOne/pbf/releases), attach it to your preferred agentic AI, and simply say: **“Let’s get this set up.”** Use an agent with persistent file access and terminal capability (Python 3.11+).

## Table of contents

- [🚀 Quick setup](#-quick-setup)
- [✨ Features](#-features)
- [🧠 How PBF works](#-how-pbf-works)
- [📥 For users: getting started with a project](#-for-users-getting-started-with-a-project)
- [For developers: working on PBF](#for-developers-working-on-pbf)
  - [Development requirements](#development-requirements)
  - [Repository structure](#repository-structure)
  - [Verify, test and build](#verify-test-and-build)
- [📚 Documentation](#-documentation)
- [🔐 Trust, safety and security](#-trust-safety-and-security)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🚀 Quick setup

There are two different ways to interact with this repository. **Use the Agent-First Release if you want to apply PBF to a project.** Clone this repository if you want to develop, inspect or contribute to PBF itself.

### Using PBF for your project?

1. Open the [GitHub Releases page](https://github.com/DiscardedOne/pbf/releases) and download the latest `PBF-vX.Y.Z-Agent-First-Release.zip`.
2. Verify the downloaded ZIP against the SHA-256 digest published in that release's description. Do not use it if the digest does not match.
3. Provide the **complete outer ZIP** to an AI-agent environment that can access a persistent destination, read and write files there, and run Python 3.11 or newer in a terminal.
4. Ask the agent to inspect the package, check its capabilities, propose a project name and exact destination, and wait for your approval before creating the workspace.
5. After setup and validation, the agent should report what it created and ask before starting P0 discovery. **P0 begins only after you explicitly approve.**

A suggested first instruction is:

> Prepare a PBF workspace using the recommended Agent-First setup. Inspect and verify the complete release package, check your actual filesystem, persistence and Python capabilities, and propose a project name and exact destination. Explain the planned operations and wait for my approval before creating anything. After setup, run the prescribed checks, report the results and ask whether I am ready to begin P0 discovery. Do not begin P0 until I confirm.

You do not necessarily need Python installed on your own computer if the agent runs in an environment that already has Python 3.11+ and access to the persistent location where you want the project workspace. An attachment-only chat or an ephemeral temporary directory is not sufficient for a workspace you expect to keep.

**New to PBF?** Read the [Project Overview and Method](release-assets/docs/PBF-Project-Overview-and-Method.md) for the reasoning behind the framework, then use the [Quick Start](release-assets/QUICKSTART.md) for the complete setup instructions.

### Developing PBF itself?

```bash
git clone https://github.com/DiscardedOne/pbf.git
cd pbf

python -B bp.py --version
python -B bp.py verify
python -B bp.py verify --tests
```

Development requires CPython 3.11 or newer. See [For developers](#️-for-developers-working-on-pbf) and the [Development Guide](DEVELOPMENT.md) for the complete workflow.

## ✨ Features

- **Start from an incomplete idea** — describe the problem, opportunity or goal in ordinary language. You do not need a finished brief or requirements document before beginning.
- **Adaptive documentation** — determine which documents, registers, diagrams and levels of detail a project actually needs based on its domain, complexity, risks and lifecycle.
- **Progressive elaboration** — move from context and discovery towards requirements, architecture, detailed design, validation and delivery planning without treating the process as a rigid waterfall.
- **Traceable decisions and assumptions** — keep open questions, evidence, alternatives, rationale, dependencies, risks, approvals and changes visible.
- **Persistent project context** — maintain canonical project knowledge in a structured, file-based workspace rather than relying only on chat history or an AI model's memory.
- **Human-controlled collaboration** — the owner supplies intent, domain knowledge, corrections and approvals; the agent assists with discovery, research, analysis, drafting and consistency checks.
- **Continuity and handoff** — help a new person, contributor or AI session understand the project from its current documentation and state.
- **Supporting validation tools** — use the PBF command-line tooling to create and check workspaces, validate indexes and audit documented state.

### 🌐 What kinds of projects can use PBF?

PBF is designed to be **domain-adaptive**. Examples include:

| Project type | Example areas that can be explored and documented |
|---|---|
| **Software and digital products** | Applications, APIs, platforms, integrations, data systems, cloud services and developer tools |
| **Hardware and electronics** | Devices, electronic products, PCB-related requirements, component decisions, interfaces and test plans |
| **Embedded and cyber-physical systems** | Hardware/software boundaries, firmware behavior, timing, communications, diagnostics, provisioning and updates |
| **Mechanical and physical products** | Product requirements, subsystems, materials or component decisions, manufacturing considerations and verification plans |
| **Research and experiments** | Objectives, hypotheses, methodology, assumptions, evidence, experiments, analysis and limitations |
| **Operations and infrastructure** | Operating models, workflows, dependencies, service requirements, resilience, controls and rollout planning |
| **Hybrid initiatives** | Projects combining software, hardware, people, processes, data, vendors or physical operations |

These examples describe the methodology's adaptability; they do not mean that PBF ships specialist engineering tools or a dedicated template for every discipline. Domain experts remain responsible for specialist judgments, calculations, testing and approvals.

## 🧠 How PBF works

PBF brings together three parts:

1. **A methodology** — workflows and principles for discovery, requirements, architecture, documentation, review, approvals, change control and continuity.
2. **A project workspace** — a project-specific, file-based home for documents, registers, decisions, assumptions, approvals, indexes and current state.
3. **Supporting tooling** — Python command-line utilities for deterministic tasks such as workspace creation, validation, indexing, state checks and release packaging.

A typical working cycle looks like this:

1. **You explain what you know.** Start with the goal, problem, opportunity, constraints or rough concept.
2. **The agent explores with you.** It identifies what is known, uncertain or assumed, and asks focused questions where the answers matter.
3. **A useful first slice is documented.** The agent creates or updates the smallest useful set of project documents instead of generating a large collection of empty templates.
4. **The structure adapts.** The documentation architecture is tailored to the project's domain, scale, complexity and intended outcomes.
5. **You review and decide.** The agent explains options, implications and unresolved matters; the owner retains decision and approval authority.
6. **The workspace stays coherent.** Documents, decisions, traceability, indexes and project state are maintained as the project evolves.
7. **Work continues across sessions.** A future conversation or agent can recover context from the workspace rather than reconstructing it from chat history.

### The P0–P8 lifecycle

PBF uses a lifecycle vocabulary to organize progressive work. It is **not a mandatory waterfall**: small projects may use only some phases, and complex projects may adapt their order or add domain-specific work.

| Phase | Focus |
|---|---|
| **P0 — Vision and structure** | Capture the initial idea and establish an appropriate documentation architecture. |
| **P1 — Discovery and framing** | Explore the problem, context, stakeholders, goals, constraints and success criteria. |
| **P2 — Product and requirements** | Develop scope, use cases, behavior, functional requirements and quality needs. |
| **P3 — Domain, data and integration** | Understand domain concepts, information, interfaces, dependencies and external relationships. |
| **P4 — High-level architecture** | Establish system boundaries, major components or subsystems and their relationships. |
| **P5 — Detailed design** | Elaborate technical or domain-specific design to the depth justified by the project. |
| **P6 — Quality and operations** | Plan verification, validation, safety or security considerations, deployment, support and operational needs as applicable. |
| **P7 — Delivery** | Structure implementation or execution planning, dependencies, milestones, readiness and handoff. |
| **P8 — Coherence and sign-off** | Review consistency, evidence, unresolved matters, approvals and the state of the project baseline. |

PBF can organize detailed design specifications, but it does not replace the engineering, scientific, legal, regulatory or other specialist work needed to establish that a design or decision is correct.

## 📥 For users: getting started with a project

### Recommended: Agent-First setup

The Agent-First Release is the normal product distribution. It contains the user documentation, agent operating instructions, a nested agent package, curated bootstrap runtime, workspace starter, helper tooling and integrity metadata. You do not need to clone this developer repository or manually assemble those components.

1. Download the latest Agent-First ZIP from [GitHub Releases](https://github.com/DiscardedOne/pbf/releases).
2. Verify its SHA-256 using the digest in the release description:

   **Windows PowerShell**
   ```powershell
   Get-FileHash .\PBF-vX.Y.Z-Agent-First-Release.zip -Algorithm SHA256
   ```

   **Linux/macOS**
   ```bash
   sha256sum PBF-vX.Y.Z-Agent-First-Release.zip
   ```

3. Attach the complete ZIP to an agent with persistent filesystem access and terminal access to Python 3.11+.
4. Ask the agent to inspect the package and environment, propose an exact destination, and explain what it will do.
5. Approve the project name and destination before the agent creates the workspace.
6. Review the setup report and validation results. The agent must ask for your confirmation before starting P0 discovery.

The [Quick Start](release-assets/QUICKSTART.md) contains the complete recommended procedure and startup instruction. The [User Guide](release-assets/docs/PBF-User-Guide.md) explains day-to-day operation, continuity between sessions, approvals, validation, backups and troubleshooting.

### First session: what happens after setup?

A new workspace is intentionally not filled with every possible project document. During P0, the owner and agent establish the project's initial vision, context and appropriate document architecture. The agent should explain its proposed structure and seek the required owner decisions rather than silently treating assumptions as approved facts.

As work continues, the workspace becomes the durable project reference. At the beginning of a later session, the agent should inspect the current project instructions and state before proposing new work. At the end, it should update the relevant records and leave a clear handoff for the next session.

### Prefer a manual setup?

A manual CLI setup is also supported. It requires Python 3.11+ in the environment where the commands are run. Follow **Alternative: manual CLI setup** in the [PBF User Guide](release-assets/docs/PBF-User-Guide.md); the guide covers package extraction, integrity checks, bootstrap verification, workspace creation and validation.

## For developers: working on PBF

This repository is the **maintained developer source**, not the normal product download. Work here when you want to inspect the implementation, change the framework, improve documentation, run tests or build a new Agent-First Release. If you only want to use PBF for a project, use the [latest release](https://github.com/DiscardedOne/pbf/releases).

### Development requirements

- **CPython 3.11 or newer.**
- **Git** for cloning and normal contribution workflows.
- **No third-party Python dependencies** are required for source verification, workspace building, bootstrap or release packaging; these use the Python standard library.

### Repository structure

```text
pbf/
├── README.md                         # Project overview and contributor entry point
├── VERSION                           # Sole authoritative release-version input
├── bp.py                             # Command-line entry point
├── DEVELOPMENT.md                    # Developer and maintainer workflow
├── CONTRIBUTING.md                   # Contribution expectations
├── LICENSE                           # Apache License 2.0
├── SECURITY.md                       # Vulnerability reporting policy
├── CODE_OF_CONDUCT.md                # Community standards
├── _framework/                       # Workspace runtime, instructions and templates
├── starter/                          # Project-neutral workspace starter source
├── src/blueprint_framework/           # Developer CLI, build and packaging implementation
├── framework-dev/                    # Architecture, maintained tests and maintainer references
├── release-assets/                    # User documentation and agent onboarding inputs
├── tools/agent-bootstrap/             # Standard-library bootstrap helper and tests
├── tools/release/                    # Agent-First Release compiler
└── dist/                              # Generated local output; ignored by Git
```

The developer repository, curated bootstrap runtime, workspace starter and generated project workspace serve different purposes. See the [Architecture and Technical Reference](release-assets/docs/PBF-Architecture-and-Technical-Reference.md) for the boundaries between them.

### Verify, test and build

Run commands from the repository root.

**Check the source tree and version:**

```bash
python -B bp.py --version
python -B bp.py verify
```

**Run the complete maintained test suite:**

```bash
python -B bp.py verify --tests
```

`verify` checks the maintained developer tree. `verify --tests` additionally runs the maintained test modules in independent Python processes.

**Build and validate the project-neutral workspace starter:**

```bash
python -B bp.py build
```

This runs the maintained verification and test gates by default, creates the workspace starter under `dist/` and validates a fresh materialization of that artifact.

**Build the complete Agent-First Release:**

```bash
python -B tools/release/build_release.py
```

The release compiler assembles and validates the product distribution and produces:

```text
dist/PBF-v<VERSION>-Agent-First-Release.zip
```

An existing release output is not overwritten unless `--force` is explicitly supplied. Do not use `--force` casually; preserve and compare artifacts when checking reproducibility. For the full development workflow, change boundaries, version discipline and release procedure, read [DEVELOPMENT.md](DEVELOPMENT.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the [Release Checklist](framework-dev/RELEASE-CHECKLIST.md).

## 📚 Documentation

The README is the entry point; the documents below provide deeper guidance. You do not need to read everything before trying PBF.

| Document | What it covers | Best for |
|---|---|---|
| [Quick Start](release-assets/QUICKSTART.md) | Download integrity and recommended Agent-First setup | First-time users |
| [Project Overview and Method](release-assets/docs/PBF-Project-Overview-and-Method.md) | Purpose, problem addressed, intended users, collaboration model, use cases, lifecycle, approvals and limitations | Prospective users, project owners and decision-makers |
| [User Guide](release-assets/docs/PBF-User-Guide.md) | Agent-assisted setup, manual CLI alternative, P0, everyday operation, continuity, approvals, backups and troubleshooting | Project owners and everyday users |
| [Architecture and Technical Reference](release-assets/docs/PBF-Architecture-and-Technical-Reference.md) | System boundaries, source/workspace separation, workspace architecture, agent contract, bootstrap, CLI, validation and compatibility | Technical users, architects and developers |
| [Quality Assurance and Review Policy](release-assets/docs/PBF-Quality-Assurance-and-Review-Policy.md) | Validation layers, quality policy, bootstrap acceptance and review expectations | Reviewers and technical decision-makers |
| [Release Notes and Verification](release-assets/docs/PBF-Release-Notes-and-Verification.md) | Release identity, distribution contents, build evidence, smoke checks and compatibility limitations | Users and reviewers checking release claims |
| [Maintainer Handbook](release-assets/docs/PBF-Maintainer-Handbook.md) | Source structure, development environment, testing, build, bootstrap maintenance and release procedures | Framework maintainers and contributors |
| [Development Guide](DEVELOPMENT.md) | Developer environment, repository structure, verification scopes, build commands and version/release discipline | Developers and maintainers |
| [Contributing Guide](CONTRIBUTING.md) | Change expectations, test requirements, documentation rules and pull-request guidance | Contributors |
| [Framework Development References](framework-dev/README.md) | Maintainer architecture, test suite, source manifest, changelog and release checklist | Framework maintainers |
| [Workspace Architecture Specification](framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md) | Accepted v3.0.0 workspace architecture and its design constraints | Architecture-level contributors |

For the complete product-document index, see [release-assets/docs/README.md](release-assets/docs/README.md). The Agent-First Release also includes its own user documentation and agent operating instructions.

## 🔐 Trust, safety and security

PBF is designed to make project information and changes more traceable; its checks and instructions have specific limits:

- **The human owner remains in control.** The owner supplies project intent and domain knowledge and retains authority over consequential decisions and approvals.
- **Setup requires real capabilities.** An agent must actually have persistent destination access, write permission and Python 3.11+ execution. PBF instructions cannot grant missing permissions or turn temporary storage into persistent storage.
- **Approval is explicit.** The agent must confirm the project name and exact destination before creating a workspace, and must not begin P0 discovery until the owner confirms.
- **Workspace creation is intentionally limited.** It does not initialize Git, install system software or make network requests.
- **Validation has a defined scope.** Strict checks, index validation and state audits can detect structural and consistency problems; they do not prove that project decisions, engineering designs or AI-generated content are correct.
- **PBF is not a sandbox.** It does not constrain unrelated tools used by an agent or provide an operating-system security boundary. Actual permissions and isolation depend on the environment in which the agent runs.
- **Use appropriate human and specialist review.** Consequential engineering, scientific, safety, security, legal and regulatory decisions require qualified review where applicable.
- **Protect sensitive information.** Do not place credentials, secrets or sensitive personal information in project documents unless the workspace and AI environment have been assessed for that use.

For vulnerability reporting, see [SECURITY.md](SECURITY.md). For community expectations, see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## 🤝 Contributing

Issues, documentation improvements and pull requests are welcome. If you are new to the project, start with [DEVELOPMENT.md](DEVELOPMENT.md) and the [Framework Development References](framework-dev/README.md) to understand the source layout and accepted architecture.

Before submitting a change:

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) and identify the part of the repository that owns the behavior you intend to change.
2. For runtime or workspace changes, read the [Workspace Architecture Specification](framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md) first.
3. Keep changes focused and preserve PBF's domain-adaptive approach, explicit owner approvals and separation between developer source and generated workspaces.
4. Add or update regression tests for behavior changes and run the relevant verification commands.
5. Update affected user documentation, maintainer records and release inputs where appropriate. Report exactly what you tested; do not claim platforms or Python versions you did not verify.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security vulnerabilities privately through the process in [SECURITY.md](SECURITY.md), rather than opening a public issue.

## 📄 License

PBF is distributed under the [Apache License, Version 2.0](LICENSE) (`Apache-2.0`). The license covers PBF-provided framework components. A generated workspace includes [`PBF-LICENSE-SCOPE.md`](starter/PBF-LICENSE-SCOPE.md), which clarifies that the PBF license does not automatically relicense owner-authored project material or third-party content later added to that workspace.

---

<p align="center">
  <strong>Start with your project idea. Let the blueprint evolve with the project.</strong><br />
  <a href="https://github.com/DiscardedOne/pbf/releases">Get PBF</a> ·
  <a href="release-assets/QUICKSTART.md">Quick Start</a> ·
  <a href="release-assets/docs/PBF-Project-Overview-and-Method.md">Explore the methodology</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>
