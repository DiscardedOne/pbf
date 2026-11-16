# Project Documentation

This directory contains project-specific documentation and supporting artifacts. The document inventory and lifecycle source of truth is [`_control/registry/MANIFEST.md`](../_control/registry/MANIFEST.md); generated navigation is available in [`_control/registry/INDEX.md`](../_control/registry/INDEX.md).

## Documentation groups

The initial layout is intentionally lightweight. Create project documents only after the owner and agent have agreed the adaptive document architecture in D0.02.

| Directory | Typical contents |
|---|---|
| `00-overview/` | Vision, scope and project context. |
| `01-discovery/` | Stakeholder, user, problem and research findings. |
| `02-product/` | Capabilities, workflows, requirements and business rules. |
| `03-domain/` | Domain concepts, lifecycle and data classification. |
| `04-architecture/` | Architecture decisions, system context, components and technical decisions. |
| `05-design/` | Detailed interface, component and interaction designs. |
| `06-quality-operations/` | Quality, security, testing and operational concerns. |
| `07-delivery/` | Roadmap, work breakdown and implementation guidance. |
| `08-acceptance/` | Coherence reviews and baseline acceptance evidence. |
| `99-appendix/` | Supporting research and reference material. |
| `_assets/` | Images, diagrams, attachments and machine-readable specifications. |

Not every project needs every group. The accepted D0.02 architecture determines the applicable structure. Keep application source code outside this documentation workspace.

## Project control registers

- [Document inventory](../_control/registry/MANIFEST.md)
- [Generated document index](../_control/registry/INDEX.md)
- [Decisions](../_control/registry/DECISIONS.md)
- [Assumptions](../_control/registry/ASSUMPTIONS.md)
- [Open questions](../_control/registry/QUESTIONS.md)
- [Risks](../_control/registry/RISKS.md)
- [Glossary](../_control/registry/GLOSSARY.md)
- [Approvals](../_control/registry/APPROVALS.md)
- [Project state](../_control/STATE.md)

For reusable methodology and templates, see the [framework guide](../_framework/GUIDE.md). These registers are maintained under `_control/`; do not create competing copies in `docs/`.
