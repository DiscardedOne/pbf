# Project Blueprint Framework v{{PBF_VERSION}}

**A reusable, adaptive project discovery and documentation framework for a human owner and an AI agent.**

PBF helps a project owner and an agent collaboratively develop and maintain a structured understanding of projects across domains, including software, hardware, embedded systems, research, products, operations and hybrid initiatives. It supports progressive elaboration from project context and objectives through domain-appropriate requirements, architecture, decisions, validation and implementation or execution planning.

PBF is not an AI model, an agent, a hosted service, an autonomous development environment or a security sandbox. The owner supplies domain knowledge, priorities, corrections and approvals. The agent performs discovery, research, analysis, documentation and validation within its actual capabilities and authorized permissions. PBF supplies the methodology, instructions, templates, state model, runtime tools and quality procedures.

## Project links

- **Source repository:** [https://github.com/DiscardedOne/pbf](https://github.com/DiscardedOne/pbf)
- **Official releases and downloads:** [https://github.com/DiscardedOne/pbf/releases](https://github.com/DiscardedOne/pbf/releases)

## Start here

1. Read [`QUICKSTART.md`](QUICKSTART.md).
2. Provide the **complete Agent-First Release ZIP** to an agentic AI environment with actual persistent filesystem access and Python 3.11+ terminal execution.
3. Let the agent propose a project name and destination. Confirm the exact path before anything is created.
4. The agent creates and verifies the workspace, reports the result, and asks separately whether you are ready to begin P0 discovery.

**Recommended:** agent-assisted setup. **Alternative:** manual CLI setup is fully documented in [`docs/PBF-User-Guide.md`](docs/PBF-User-Guide.md).

## What is included

- `QUICKSTART.md` — short instructions for the recommended setup.
- `agent-package/PBF-Agent-Package-v{{PBF_VERSION}}.zip` — nested agent package containing the agent contract, startup prompt, package integrity metadata, a curated bootstrap runtime, workspace starter and bootstrap helper.
- `docs/` — six consolidated references and a flat document index.
- `release-evidence/` — concise, generated verification evidence for this exact release build.
- `LICENSE` — Apache License 2.0 terms for PBF-provided components in this distribution.
- `RELEASE-MANIFEST.json` and `SHA256SUMS.txt` — release inventory and internal payload integrity information.

The bootstrap runtime is extracted temporarily by the helper. It is not copied into the generated project workspace. The generated workspace contains the accepted project-facing architecture and runtime; it does not contain the maintainer source tree or development history.

## Documentation map

The [`docs/README.md`](docs/README.md) index describes each document:

| Document | Purpose |
|---|---|
| [`PBF-Project-Overview-and-Method.md`](docs/PBF-Project-Overview-and-Method.md) | Product purpose, methodology and collaboration model |
| [`PBF-Architecture-and-Technical-Reference.md`](docs/PBF-Architecture-and-Technical-Reference.md) | Architecture, ownership, agent contract, CLI, runtime, validation and security |
| [`PBF-User-Guide.md`](docs/PBF-User-Guide.md) | Recommended setup, manual CLI alternative, P0 and day-to-day operation |
| [`PBF-Maintainer-Handbook.md`](docs/PBF-Maintainer-Handbook.md) | Source maintenance, tests, build and release procedures |
| [`PBF-Release-Notes-and-Verification.md`](docs/PBF-Release-Notes-and-Verification.md) | Release structure, current-build evidence, compatibility and limitations |
| [`PBF-Quality-Assurance-and-Review-Policy.md`](docs/PBF-Quality-Assurance-and-Review-Policy.md) | Validation layers, quality policy and release acceptance criteria |

## Requirements and limitations

- Python 3.11 or newer is the declared minimum.
- Agent-assisted setup requires actual filesystem access, terminal execution and a persistent user-visible destination. Attachment inspection alone is insufficient.
- The framework does not install Python, configure an AI model, supply credentials, make network calls, initialize Git or provide an OS-level sandbox.
- Agent-assisted onboarding is recommended, not certified for every AI harness. The agent must establish its real capabilities and stop honestly if a prerequisite is unavailable.
- Deterministic checks do not prove semantic correctness or replace owner/domain/security review.
- Native Windows, all supported Python minors, CI and universal cross-harness compatibility are not claimed without current evidence.
- PBF-provided components are licensed under Apache License 2.0 (`Apache-2.0`); the canonical license text is included at the archive root and in the nested runtime/workspace layers. The generated workspace also includes `PBF-LICENSE-SCOPE.md` to distinguish PBF components from owner-authored project content and third-party material.

## License and release integrity

PBF-provided components in this distribution are licensed under Apache License 2.0 (`Apache-2.0`). The license text is included at the archive root and in the nested agent/runtime/workspace distributions. The generated workspace contains `PBF-LICENSE-SCOPE.md` to clarify that its presence does not automatically license project-specific content added by the workspace owner or other contributors.

For a public download, obtain PBF from the [official GitHub Releases page](https://github.com/DiscardedOne/pbf/releases), calculate the SHA-256 of the outer ZIP and compare it with the digest published in that release description. The [source repository](https://github.com/DiscardedOne/pbf) contains the maintained developer source. The repository/account is the publication trust source; a checksum does not independently authenticate a publisher if that account or release is compromised.

## Release identity

- **Framework version:** `{{PBF_VERSION}}`
- **Accepted workspace architecture:** `1.3.4`
- **Distribution:** Agent-First Release

See [`docs/PBF-Release-Notes-and-Verification.md`](docs/PBF-Release-Notes-and-Verification.md) and the generated `release-evidence/BUILD-VERIFICATION.md` for this artifact's actual verification results.
