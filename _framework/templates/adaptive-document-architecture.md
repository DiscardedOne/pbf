---
doc_id: {{DOC_ID}}
title: {{TITLE}}
phase: {{PHASE}}
status: {{STATUS}}
maturity: {{MATURITY}}
applicability: {{APPLICABILITY}}
applicability_rationale: "{{APPLICABILITY_RATIONALE}}"
profile_tier: {{PROFILE_TIER}}
version: {{VERSION}}
last_updated: {{DATE}}
depends_on: [{{DEPENDS}}]
summary: "Provisional project-specific documentation architecture, scope, and evolution rules."
---

# {{TITLE}}

> **Purpose:** Define a documentation structure that fits this project. This is a living architecture, not a permanent contract. Its acceptance approves the current starting structure; future learning may change it through impact-controlled revisions.

## Project profile and documentation drivers

- **Project/system type:** [[FILL: Describe what is known; avoid forcing a single label if hybrid]]
- **Intended readers:** [[FILL: Name the intended readers]]
- **Planning depth:** [[FILL: Select a planning depth and explain why]]
- **Primary documentation outcomes:** [[FILL: State what the documentation must enable]]
- **Complexity/risk signals:** [[FILL: Describe the important complexity and risk signals]]
- **Known constraints:** [[FILL: Record known constraints and link to canonical sources]]

## Documentation principles and constraints

- Canonical format and tooling:
- Source-of-truth approach:
- Stable ID / naming approach:
- Granularity preference:
- Visual/diagram conventions:
- Session carry-forward mode:
- Review and approval preferences:

## Proposed document architecture

Describe why this structure fits the project and which concerns belong together. A concise tree is enough at first; it may be expanded later.

```text
project-docs/
├── 00-overview/
│   ├── vision-capture.md
│   └── documentation-scope.md
└── [[FILL: Add only currently justified groups]]
```

| Group / path | Purpose and canonical concerns | Intended readers | Initial documents | Status / rationale |
|---|---|---|---|---|
| `00-overview/` | Vision, scope, operating agreements | All readers | D0.01, D0.02 | Core bootstrap group |

## Document inventory and applicability

Use the catalog as a candidate inventory, not a rigid list. Record only currently supported decisions; revisit conditional areas when their trigger is met.

| Catalog item / concern | Disposition (core / core-light / conditional / deferred / merged / split / new / excluded) | Proposed canonical document(s) | Rationale / activation trigger | Decision status |
|---|---|---|---|---|
| Product vision and problem | Core | D0.01 and later product discovery documents as appropriate | Needed to align all future work | Proposed |
| Documentation architecture | Core | D0.02 | Defines this project-specific structure | Proposed |

Use one explicit disposition per inventory concern. The operational mapping is: `Core` and `Core-light` → manifest applicability `active`; `Conditional` → `conditional`; `Deferred` → `deferred`; `Excluded` → `excluded`. For `Merged`, retain the source document ID as `excluded` and identify the active host document in both the canonical mapping and applicability rationale. For `Split`, identify the resulting child document IDs explicitly and record each child's applicability in the manifest; retain the former ID as excluded/superseded when it is no longer a canonical document. For `New`, assign explicit new document IDs and record each ID's applicability in the manifest. Do not infer a missing ID or disposition. Once this architecture is approved with a valid approval record, `python bp.py check --strict` enforces the explicit inventory-to-manifest mapping; while it is draft or in review, discrepancies are advisory. The validator reports differences and never rewrites owner decisions or manifest rows.

For exclusions, state where the concern is covered instead or why it does not apply. Do not silently drop quality, security, privacy, risk, testing, operational or delivery concerns.

## Phase and sequencing adaptations

| Framework phase / activity | Keep, tailor, merge, supplement or defer | Project-specific treatment | Gate / evidence needed |
|---|---|---|---|
| P0 — Setup and vision capture | Keep | Capture vision, agree on a provisional document architecture, and scaffold only a small useful slice | D0.01 playback and D0.02 architecture accepted provisionally |
| P1–P8 | Review against project needs | Record relevant changes, specialist phases, and dependency constraints here | Define per phase as evidence becomes available |

Phases govern baseline approval, not which topics may be discussed. Future architecture topics can be explored early at a provisional level.

## Source-of-truth and dependency model

| Concern / information type | Canonical document or registry | Consumers / dependents | Notes |
|---|---|---|---|
| Current document inventory and workflow status | `_control/registry/MANIFEST.md` | Tooling, state dashboard, dependency graph | Operational source of truth |
| Reusable templates and scaffold checklists | `_framework/DOC-CATALOG.md` | Scaffold helper | Tailor mappings when catalog structure changes |
| Unresolved questions, assumptions, risks and decisions | Corresponding files under `_control/registry/` | Affected project documents | Use stable IDs |
| Project-specific documentation architecture | This document (`D0.02`) | Manifest, plan, indexes, helper maps | This document explains the structure; the manifest operationalizes it |

Add project-specific rows as the architecture develops. Dependencies should express real information flow, not simply mirror folder order.

## Diagrams and visual artifacts

| View / artifact | Include? | Question it should answer | Likely canonical location / stage |
|---|---|---|---|
| Documentation dependency graph | Yes | Which artifacts depend on which sources? | Generated from `_control/registry/MANIFEST.md` |
| Project-specific architecture or workflow diagrams | To be determined from the vision | Select diagrams only when they clarify a real decision or relationship | Define when relevant |

Potential views include product/user journeys, system context, containers/components, runtime/deployment, data flows, sequences, states, threat boundaries, hardware/software boundaries, pipelines, evaluations, and operational flows. Select by project need rather than trying to include them all.

## Quality coverage map

| Concern | Canonical home / treatment | Coverage status | Gaps / trigger |
|---|---|---|---|
| Goals and traceability | Product goals + traceability artifacts | Planned | Tailor to project |
| Security and privacy | Requirements/architecture/quality docs as appropriate | Planned | Assess data and trust boundaries |
| Verification and testing | Test/acceptance artifacts | Planned | Tailor test types and evidence |
| Delivery and operations | Delivery/operations artifacts if relevant | Planned | Assess release and support model |
| Risks, assumptions and decisions | `_control/registry/` files | Planned | Keep current throughout |

## Architecture evolution triggers

Revisit this structure if the project scope, main domain, system boundary, deployment model, risk/compliance profile, stakeholder audience, or document complexity changes materially. Structural changes must follow `_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md` and update the manifest, catalog mapping, dependencies, links and state.

| Trigger | What may change | Review / decision owner | Status |
|---|---|---|---|
| New material requirement or subsystem emerges | Add/split/merge document groups and revise dependencies | Project owner + documentation steward | Active rule |
| Existing document becomes too broad or duplicates another source | Split/merge/reassign canonical ownership | Project owner + documentation steward | Active rule |

## Owner review and current agreement

- **Proposed architecture version:** 0.1
- **Current disposition:** PROPOSED / PROVISIONALLY ACCEPTED / NEEDS REVISION
- **Owner feedback:**
- **Accepted structure and known exceptions:**
- **Still-open structural questions:**
- **Next architecture review trigger:**

Approval means the current structure is a sound starting point, not that future changes are forbidden. Record material changes and owner agreement in the session log / change history.

## Open questions and assumptions

| ID | Item | Impact | Owner / next action | Status |
|---|---|---|---|---|

## Catalog checklist

{{CHECKLIST}}

## References

- [`D0.01` — Vision capture and playback]({{VISION_LINK}})
- [`_control/registry/MANIFEST.md`]({{MANIFEST_LINK}})
- [`_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md`]({{ARCHITECTURE_PROTOCOL_LINK}})

## Change history

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | {{DATE}} | Initial tailored architecture scaffold | To be iterated with the owner |
