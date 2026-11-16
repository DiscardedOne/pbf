# MANIFEST.md — Document manifest

The manifest is the authoritative inventory of project-specific documentation. Each manifest row owns the document ID, project-relative path, phase, applicability (and rationale when not `active`), profile tier, effort weight, workflow status, content dependencies, title, maturity, version and last-updated date. For an existing manifest-backed Markdown file, front matter must match the manifest on every corresponding field. The helper also checks exact catalog path/title agreement and repeatable-family path containment.

## Separate metadata dimensions
- **Applicability**: `active`, `conditional`, `deferred`, `excluded`. This says whether the project needs this document now, may need it, needs it later, or has ruled it out. Excluded/deferred entries require a rationale.
- **Workflow status**: `not-started`, `interviewing`, `drafting`, `in-review`, `approved`, `needs-revision`, `superseded`, `expanded`. Applicability is not a workflow status.
- **Profile tier**: `lite`, `standard`, `exhaustive`; the selected profile includes documents whose tier is at or below it.
- **Detail maturity**: `outline`, `working`, `detailed`; independent of workflow status.

## Workflow status rules
- `not-started`: not begun.
- `interviewing`: clarifying questions are being explored.
- `drafting`: content is being written.
- `in-review`: self-review has passed and the owner is reviewing.
- `approved`: owner explicitly approved this document.
- `needs-revision`: an upstream change invalidated it.
- `superseded`: replaced by a new source; preserve history.
- `expanded`: a repeatable template row was replaced by child records.

In Phase 0, use `_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md` to design and conversationally review the project-specific structure. `D0.02` explains that architecture; this manifest is the operational source of truth for it. Use the separate `Applicability` field to mark items `conditional`, `deferred`, or `excluded`, and record the rationale/trigger in `docs/00-overview/documentation-scope.md`. Do not exclude a critical concern silently; it must be covered elsewhere, justified as N/A, or tracked as unresolved/deferred. Only `D0.01` and `D0.02` may be scaffolded before D0.02 is owner-approved unless an explicit override is recorded. Document content dependencies are recorded only when a document consumes information from another document. The adaptive architecture `D0.02` is a separate structural authority: structural-impact analysis reviews all active/in-profile project documents as candidates without falsely representing them as content dependents. Use `python bp.py impact D0.02` to see both relationship types.

**Repeatable component specifications:** At Phase 5, change `D5.03` to `expanded` and replace its folder row with one row per real component, using IDs `D5.03.01`, `D5.03.02`, …, `D5.03.100` and beyond as needed, and paths `05-design/components/<component-name>.md`. Each child row depends on `D4.03` (component architecture dependency) and is subject to structural-impact review when `D0.02` changes, and uses the mapped template/checklist in `_framework/DOC-CATALOG.md`. The 16/32/42 profile counts are starter-catalog record counts, not document limits; add records and child specs as the real project requires.

**Workflow progress:** computed from workflow status and size weights for active documents included in the selected profile. Conditional, deferred, excluded, out-of-profile, superseded and expanded entries do not contribute to the progress denominator. It measures workflow advancement, not detail maturity, business certainty, quality or effort.


## Detail maturity (independent of workflow status)

- `outline`: captures the current high-level understanding and explicitly shows unknowns.
- `working`: coherent first pass, ready for iterative discussion; some detail may remain open.
- `detailed`: expanded to the depth appropriate for its current purpose and review gate.

Use `python bp.py maturity D0.01 working` to change the manifest value and keep existing front matter synchronized. `D0.02` is the mandatory adaptive architecture artifact; do not scaffold other project documents until its manifest status is `approved`, unless a documented override is used. Do not raise maturity merely because a file was created. A document may remain `drafting` through many iterations as maturity increases.

## Project document manifest

| Doc ID | Path | Phase | Applicability | Applicability rationale | Profile tier | Size | Status | Depends on | Title | Maturity | Version | Last updated |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D0.01 | 00-overview/vision-capture.md | 0 | active | - | lite | S | not-started | - | Vision capture and playback | outline | 0.1 | 2026-10-20 |
| D0.02 | 00-overview/documentation-scope.md | 0 | active | - | lite | M | not-started | D0.01 | Adaptive documentation architecture and scope | outline | 0.1 | 2026-10-20 |
| D1.01 | 01-discovery/vision-and-problem.md | 1 | active | - | standard | M | not-started | D0.01 | Vision and problem statement | outline | 0.1 | 2026-10-20 |
| D1.02 | 01-discovery/stakeholders-and-users.md | 1 | active | - | standard | M | not-started | D1.01 | Stakeholders and user segments | outline | 0.1 | 2026-10-20 |
| D1.03 | 01-discovery/goals-and-success-metrics.md | 1 | active | - | lite | M | not-started | D0.01 | Goals and success metrics | outline | 0.1 | 2026-10-20 |
| D1.04 | 01-discovery/constraints-and-assumptions.md | 1 | active | - | lite | M | not-started | D0.01 | Constraints, assumptions and initial risks | outline | 0.1 | 2026-10-20 |
| D1.05 | 01-discovery/market-and-alternatives.md | 1 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | standard | M | not-started | D1.01, D1.02 | Market and alternatives | outline | 0.1 | 2026-10-20 |
| D1.06 | 01-discovery/business-model-and-economics.md | 1 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | standard | M | not-started | D1.03, D1.04 | Business model and economics | outline | 0.1 | 2026-10-20 |
| D1.07 | 01-discovery/legal-privacy-compliance-screen.md | 1 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | standard | M | not-started | D1.02, D1.04 | Legal, privacy and compliance screening | outline | 0.1 | 2026-10-20 |
| D2.01 | 02-product/personas-and-journeys.md | 2 | active | - | exhaustive | M | not-started | D1.02, D1.03 | Personas and user journeys | outline | 0.1 | 2026-10-20 |
| D2.02 | 02-product/feature-catalog.md | 2 | active | - | lite | M | not-started | D1.03, D1.04 | Capability and feature catalog | outline | 0.1 | 2026-10-20 |
| D2.03 | 02-product/use-cases-and-workflows.md | 2 | active | - | lite | L | not-started | D2.02 | Use cases and workflows | outline | 0.1 | 2026-10-20 |
| D2.04 | 02-product/functional-requirements.md | 2 | active | - | lite | L | not-started | D2.02, D2.03 | Functional requirements | outline | 0.1 | 2026-10-20 |
| D2.05 | 02-product/quality-requirements.md | 2 | active | - | lite | M | not-started | D1.03, D1.04, D2.03 | Non-functional and quality requirements | outline | 0.1 | 2026-10-20 |
| D2.06 | 02-product/ux-and-information-architecture.md | 2 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | standard | M | not-started | D2.02 | UX principles and information architecture | outline | 0.1 | 2026-10-20 |
| D2.07 | 02-product/business-rules-and-policy.md | 2 | active | - | standard | M | not-started | D2.03, D2.04 | Business rules and policy | outline | 0.1 | 2026-10-20 |
| D3.01 | 03-domain/domain-model.md | 3 | active | - | lite | L | not-started | D2.03, D2.04 | Domain model and lifecycle | outline | 0.1 | 2026-10-20 |
| D3.02 | 03-domain/data-lifecycle-and-classification.md | 3 | active | - | exhaustive | M | not-started | D3.01 | Data lifecycle and classification | outline | 0.1 | 2026-10-20 |
| D3.03 | 03-domain/integration-catalog.md | 3 | active | - | standard | M | not-started | D2.04, D3.01 | Integration and external dependency catalog | outline | 0.1 | 2026-10-20 |
| D3.04 | 03-domain/events-and-domain-boundaries.md | 3 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D3.01, D3.03 | Domain events and bounded contexts | outline | 0.1 | 2026-10-20 |
| D4.01 | 04-architecture/architecture-drivers.md | 4 | active | - | lite | M | not-started | D2.04, D2.05, D3.01 | Architecture drivers and principles | outline | 0.1 | 2026-10-20 |
| D4.02 | 04-architecture/system-context.md | 4 | active | - | standard | S | not-started | D4.01 | System context and trust boundaries | outline | 0.1 | 2026-10-20 |
| D4.03 | 04-architecture/containers-and-components.md | 4 | active | - | lite | L | not-started | D4.01 | Containers and components | outline | 0.1 | 2026-10-20 |
| D4.04 | 04-architecture/technology-decisions.md | 4 | active | - | lite | M | not-started | D4.01, D4.03 | Technology stack and technology decisions | outline | 0.1 | 2026-10-20 |
| D4.05 | 04-architecture/security-architecture.md | 4 | active | - | standard | M | not-started | D4.03 | Security architecture | outline | 0.1 | 2026-10-20 |
| D4.06 | 04-architecture/deployment-and-networking.md | 4 | active | - | standard | M | not-started | D4.03, D4.04 | Deployment and infrastructure architecture | outline | 0.1 | 2026-10-20 |
| D4.07 | 04-architecture/data-and-integration-architecture.md | 4 | active | - | standard | M | not-started | D3.03, D4.03 | Data and integration architecture | outline | 0.1 | 2026-10-20 |
| D4.08 | 04-architecture/cross-cutting-concerns.md | 4 | active | - | exhaustive | M | not-started | D4.03, D4.05, D4.06 | Cross-cutting architecture concerns | outline | 0.1 | 2026-10-20 |
| D4.09 | 04-architecture/code-organization-and-patterns.md | 4 | active | - | standard | M | not-started | D4.04 | Repository organization and engineering patterns | outline | 0.1 | 2026-10-20 |
| D4.10 | 04-architecture/ai-and-model-architecture.md | 4 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D4.03, D4.05 | AI/LLM architecture | outline | 0.1 | 2026-10-20 |
| D5.01 | 05-design/data-model-and-schema.md | 5 | active | - | standard | L | not-started | D3.01, D4.07 | Physical data model and schema | outline | 0.1 | 2026-10-20 |
| D5.02 | 05-design/api-and-interface-specification.md | 5 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | standard | L | not-started | D3.03, D4.07, D5.01 | API and interface specifications | outline | 0.1 | 2026-10-20 |
| D5.03 | 05-design/components/ | 5 | active | - | standard | L | not-started | D4.03 | Component specifications (repeatable per component) | outline | 0.1 | 2026-10-20 |
| D5.04 | 05-design/key-flows-and-sequences.md | 5 | active | - | standard | M | not-started | D2.03, D4.03 | Key flows and sequence designs | outline | 0.1 | 2026-10-20 |
| D5.05 | 05-design/ui-and-ux-specification.md | 5 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | L | not-started | D2.06, D4.03 | UI and UX design specification | outline | 0.1 | 2026-10-20 |
| D5.06 | 05-design/algorithms-and-business-logic.md | 5 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D2.07, D3.01 | Algorithms and business logic | outline | 0.1 | 2026-10-20 |
| D5.07 | 05-design/error-handling-and-resilience.md | 5 | active | - | exhaustive | M | not-started | D4.08, D5.04 | Error handling and resilience design | outline | 0.1 | 2026-10-20 |
| D5.08 | 05-design/background-jobs-and-messaging.md | 5 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D3.04, D4.07 | Background jobs, events and messaging | outline | 0.1 | 2026-10-20 |
| D5.09 | 05-design/configuration-and-secrets.md | 5 | active | - | exhaustive | S | not-started | D4.05, D4.06, D4.08 | Configuration and secret management | outline | 0.1 | 2026-10-20 |
| D5.10 | 05-design/ai-prompts-and-evaluation.md | 5 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D4.10 | AI prompts and evaluation design | outline | 0.1 | 2026-10-20 |
| D6.01 | 06-quality-operations/test-strategy.md | 6 | active | - | lite | M | not-started | D2.04, D2.05, D4.03 | Test and verification strategy | outline | 0.1 | 2026-10-20 |
| D6.02 | 06-quality-operations/threat-model.md | 6 | active | - | standard | M | not-started | D4.05, D5.04 | Threat model and abuse cases | outline | 0.1 | 2026-10-20 |
| D6.03 | 06-quality-operations/ci-cd-and-environments.md | 6 | active | - | exhaustive | M | not-started | D4.06, D4.09 | CI/CD and environment strategy | outline | 0.1 | 2026-10-20 |
| D6.04 | 06-quality-operations/observability-and-operations.md | 6 | active | - | exhaustive | M | not-started | D4.06, D4.08 | Observability and operational readiness | outline | 0.1 | 2026-10-20 |
| D6.05 | 06-quality-operations/performance-and-capacity.md | 6 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D2.05, D4.06 | Performance and capacity plan | outline | 0.1 | 2026-10-20 |
| D6.06 | 06-quality-operations/backup-recovery-continuity.md | 6 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D3.02, D4.06 | Backup, recovery and continuity | outline | 0.1 | 2026-10-20 |
| D6.07 | 06-quality-operations/privacy-and-compliance-controls.md | 6 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D1.07, D3.02, D4.05 | Privacy and compliance implementation controls | outline | 0.1 | 2026-10-20 |
| D6.08 | 06-quality-operations/migration-and-rollout.md | 6 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D4.06, D5.01 | Migration and rollout plan | outline | 0.1 | 2026-10-20 |
| D7.01 | 07-delivery/implementation-roadmap.md | 7 | active | - | lite | M | not-started | D2.02, D4.03, D6.01 | Implementation roadmap | outline | 0.1 | 2026-10-20 |
| D7.02 | 07-delivery/work-breakdown-structure.md | 7 | active | - | standard | L | not-started | D7.01, D2.04, D5.03 | Work breakdown structure | outline | 0.1 | 2026-10-20 |
| D7.03 | 07-delivery/definition-of-done-and-engineering-standards.md | 7 | active | - | standard | S | not-started | D6.01, D4.09 | Definition of done and engineering standards | outline | 0.1 | 2026-10-20 |
| D7.04 | 07-delivery/traceability-matrix.md | 7 | active | - | exhaustive | M | not-started | D2.04, D4.03, D6.01 | Traceability matrix | outline | 0.1 | 2026-10-20 |
| D7.05 | 07-delivery/build-agent-guide.md | 7 | active | - | lite | M | not-started | D4.04, D6.01, D7.01 | Build guide for developers and coding agents | outline | 0.1 | 2026-10-20 |
| D7.06 | 07-delivery/documentation-maintenance.md | 7 | active | - | exhaustive | M | not-started | D7.03, D7.04 | Documentation maintenance during implementation | outline | 0.1 | 2026-10-20 |
| D7.07 | 07-delivery/release-and-post-launch-plan.md | 7 | conditional | Conditional: decide in D0.02; activate, defer or exclude with a reason. | exhaustive | M | not-started | D7.01, D6.04 | Release and post-launch plan | outline | 0.1 | 2026-10-20 |
| D7.08 | 07-delivery/documentation-index-and-executive-summary.md | 7 | active | - | exhaustive | S | not-started | D7.04 | Documentation index and executive summary | outline | 0.1 | 2026-10-20 |
| D8.01 | 08-acceptance/coherence-audit.md | 8 | active | - | standard | M | not-started | D7.05 | Cross-document coherence audit | outline | 0.1 | 2026-10-20 |
| D8.02 | 08-acceptance/planning-baseline-signoff.md | 8 | active | - | lite | S | not-started | D7.05 | Planning baseline and approval record | outline | 0.1 | 2026-10-20 |
