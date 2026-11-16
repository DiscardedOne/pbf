# QUALITY-GATES.md — Document and phase acceptance checks

## 0. Automated/manual workspace checks

Run `python bp.py check --strict`. If Python is unavailable, inspect manually:

1. Each manifest-backed file exists for statuses other than `not-started`, `excluded`, `superseded` or `expanded`; no duplicate document IDs/paths.
2. Document front matter matches the manifest (ID, phase, status, dependencies, maturity, title and summary where required).
3. All local Markdown links resolve; external links are reviewed for relevance and availability where material.
4. Stable IDs are defined once; referenced IDs are defined or tracked; question placeholders map to registered open questions.
5. Approved docs contain no blocking TBDs, no unchecked checklists, no TODO guidance, no unfilled explicit template prompts (`[[FILL: ...]]`), no empty sections or fields, and every approved doc has a matching record and unchanged body-plus-critical-metadata SHA-256 approval fingerprint in `_control/registry/APPROVALS.md`.
6. Dependency graph has no cycles; dependency status is compatible with review/gate status.
7. Mermaid code fences are balanced and diagram structures have been linted; critical diagrams are rendered/visually inspected when possible.
8. STATE progress block is generated/current; state and latest handoff point to the same next task.
9. Risks, assumptions, decisions and glossary terms are registered; `_control/registry/INDEX.md` is current.
10. Repeatable component rows have been expanded before detailed design can pass its gate.

Automation does not establish the truth of requirements, diagram semantics, security adequacy, or external research.

The optional `python bp.py check --readiness` report surfaces mechanical incompleteness signals in scaffolded, active, in-profile documents in `drafting`, `interviewing` or `in-review`. It is advisory and does not alter the exit code. A clean result does not establish semantic completeness.

## 1. Document definition of done

- [ ] Catalog content checklist is complete or contains `N/A — reason`.
- [ ] Purpose, scope, source-of-truth ownership, inputs and summary are clear.
- [ ] Claims are labelled appropriately when they are facts, proposals, assumptions or open questions.
- [ ] Every requirement/rule/entity/interface/component has the relevant ID, source and acceptance/validation path.
- [ ] Relative links, IDs, status and front matter are consistent.
- [ ] Diagrams have captions/read guides and agree with the prose.
- [ ] Errors, exceptions, edge cases and security/privacy/operational concerns are addressed proportionately.
- [ ] Risks, assumptions, decisions, terminology and questions are registered.
- [ ] Detail maturity (`outline`, `working`, `detailed`) is honest and matches the manifest.
- [ ] Reviewer digest has been presented and owner approval recorded before status becomes approved.
- [ ] Incremental section feedback is distinguished from whole-document approval.

## 2. Phase gate checklists

Common to every gate:
- Strict tool check passes, or deviations are recorded.
- No unresolved ripple queue item invalidates current-phase docs.
- Open blocking questions are resolved or phase remains blocked.
- A phase report is written.
- The owner explicitly accepts or rejects the phase.

### G0 — Setup, vision capture, and adaptive documentation architecture
- [ ] Owner's initial vision has been played back and corrected without requiring an exhaustive upfront questionnaire.
- [ ] A useful `D0.01` vision slice was drafted and iterated early.
- [ ] `D0.02` contains a tailored document tree and a concise rationale for its groups and granularity; the default catalog has not been copied unchanged merely for completeness.
- [ ] Document inventory dispositions are explicit: core, conditional, new, merged, split, excluded, or deferred, with rationale/triggers for material choices.
- [ ] Source-of-truth ownership, stable-ID/manifest relationship, dependencies, diagram plan, quality coverage, and evolution triggers are documented.
- [ ] Phase sequence/gates are checked for fit; any needed adaptations are documented in `D0.02` and synchronized with tooling.
- [ ] Owner explicitly accepts the proposed architecture as a **provisional baseline**; this does not prohibit future change.
- [ ] The helper prevents scaffolding beyond `D0.01`/`D0.02` before that acceptance, except through a deliberate documented override.
- [ ] Only the selected next slice was scaffolded unless bulk generation was explicitly requested.
- [ ] Project type, document audience, planning depth, working mode, tool/review preferences and file carry-forward plan are recorded.
- [ ] Critical quality/security/privacy/testing/operations concerns have an identified canonical home or are tracked with rationale/trigger.
- [ ] State, questions, decisions, manifest and session handoff reflect the accepted structure.
- [ ] G0 does not force completion of the feature inventory, requirements, or low-level architecture.

### G1 — Discovery and business framing
- [ ] Problem statement names who experiences the problem and the context/current workaround.
- [ ] Stakeholders and target user segments are identified.
- [ ] Every important goal has at least one metric or an explicit metric-discovery action.
- [ ] MVP boundary, non-goals and hard constraints are recorded.
- [ ] Top assumptions and risks have validation/mitigation actions.
- [ ] Relevant business-model, market, legal/privacy screens are completed or explicitly excluded.

### G2 — Product definition and requirements
- [ ] In-scope features map to goals and use cases map to features.
- [ ] Critical use cases include success, alternate, exception and relevant misuse paths.
- [ ] Functional requirements are atomic, sourced, prioritized and testable.
- [ ] Quality requirements are quantified or explicitly marked unresolved/N/A with rationale.
- [ ] Business rules, UX and permissions are described where applicable.
- [ ] No major scope item has no owner or rationale.

### G3 — Domain, data and integrations
- [ ] Key domain terms, entity relationships, invariants and lifecycles are described.
- [ ] Data sources of truth, owners, classification, retention, deletion and recovery needs are explicit.
- [ ] Integration catalog includes interface, data, auth, terms/limits, failure expectations and ownership.
- [ ] Asynchronous/event boundaries and consistency needs are explicit where relevant.
- [ ] Models and diagrams match use cases and business rules.

### G4 — High-level architecture
- [ ] Architecturally significant requirements are addressed by components, design choices or a documented spike.
- [ ] System context, container/component and deployment/trust-boundary views agree.
- [ ] Every main component has a responsibility, interface summary, dependency direction and data ownership.
- [ ] Material technology choices include alternatives, verified facts, rationale and ADRs.
- [ ] Security, data, deployment and integration architecture do not contradict each other.
- [ ] Cost, scalability, operations and lock-in considerations match requirements.

### G5 — Detailed technical design
- [ ] Each real component has a component spec or an explicit N/A rationale.
- [ ] Critical use cases map to sequence/state designs and tests.
- [ ] Data schemas support entities, queries, APIs and retention/deletion rules.
- [ ] Interface contracts include auth, validation, errors, versioning and idempotency/concurrency where relevant.
- [ ] Retry, timeout, dead-letter, recovery and compensating actions are defined where relevant.
- [ ] Config and secrets are specified without exposing actual secret values.
- [ ] No detail contradicts accepted requirements or ADRs.

### G6 — Quality, security and operations
- [ ] Every important FR/NFR has a verification method.
- [ ] Threat model covers trust boundaries and abuse cases; mitigations link to design and tests.
- [ ] CI/CD, environments, rollback, observability, alert thresholds and ownership are defined.
- [ ] Performance/capacity, backup/restore, compliance and rollout items are complete or N/A with reasons.
- [ ] Residual security/privacy/continuity risks are explicitly accepted or block progression.

### G7 — Delivery planning
- [ ] Roadmap includes dependencies, milestone criteria, risky spikes and a walking skeleton.
- [ ] Work packages map to requirements/components and have acceptance criteria.
- [ ] Build guide explains setup, order, tests, review rules and safety limits.
- [ ] **Lite:** Critical goals, requirements/deliverables, components/interfaces and verification tests are identifiable well enough for the final manual traceability audit at G8; gaps and candidate orphans are tracked for review. Record the completed audit and any accepted exceptions in D8.02 during P8.
- [ ] **Standard:** D2.04 requirement entries use populated `Goals`, `Use cases`, `Design component/interface` and `Acceptance tests` traceability fields (or `N/A: reason`); component specs list requirement drivers and `Verification (TC-)` IDs. Track gaps for the D8.01 coherence/coverage audit at G8, and reference its evidence in D8.02.
- [ ] **Exhaustive:** D7.04 is maintained with goal-to-requirement-to-use-case, requirement-to-component/interface and requirement-to-test links; record candidate orphans and gaps for final reconciliation during G8.
- [ ] Documentation maintenance and code/spec change control are defined.

### G8 — Coherence and sign-off
- [ ] Complete the profile-appropriate traceability and coherence audit: Lite records the manual audit in D8.02; Standard completes D8.01 and references its evidence in D8.02; Exhaustive reconciles D7.04 with the detailed coherence/orphan review. D8.02 retains only its existing D7.05 machine dependency; the D8.01 evidence relationship is a gate/procedure requirement, not a manifest dependency.
- [ ] Goals → features/use cases → requirements → domain/data → components/interfaces → tests traceability has been audited at the selected profile's required depth.
- [ ] No duplicate/contradictory source-of-truth facts remain.
- [ ] IDs, terms, numbers/units, versions, configuration and scope match across docs.
- [ ] Diagrams are structurally valid and semantically consistent with prose.
- [ ] ADRs, assumptions, risks and open/deferred questions are reconciled.
- [ ] All links, manifest, state, change log and latest handoff are current.
- [ ] Residual exceptions have an owner, rationale and revisit trigger.
- [ ] Owner explicitly approves the planning baseline version. “Approved” means this document version was accepted; it does not mean the baseline is permanently frozen.

## 3. Consistency audit process

1. Automated structural checks: `check --strict` and `check --gate N`.
2. Terminology check: verify glossary terms and alias consistency.
3. Numeric consistency: values repeated across documents must link to their canonical value; check units, currencies and time zones.
4. ID integrity: find orphan goals, features, use cases, requirements, components/interfaces and tests.
5. Decision alignment: accepted ADR decisions and consequences must be reflected in dependent docs.
6. Diagram/text consistency: validate nodes, direction, names, interfaces, boundaries and failure paths against the source documents.
7. Scope fidelity: new features/components outside approved scope require a change request.
8. Assumption hygiene: assumptions have validation plans/status; invalidated assumptions have been propagated.
9. Open questions: blocking items are resolved or block approval; non-blocking deferrals need rationale, owner and revisit trigger.
10. Readability: a cold reader can understand product goals and build order without private conversation.
11. Findings are fixed and rechecked, or explicitly accepted by the owner with a documented rationale.


## Phase 5 integrity checks

- For a validly approved adaptive architecture document, `check --strict` verifies that its explicit document-inventory dispositions conform to manifest applicability. Draft/in-review architecture drift is advisory.
- Active consumers may not depend on conditional, deferred or excluded targets unless a future explicit, validated exception mechanism is defined. Non-active consumers may retain planning references.
- `python bp.py audit-state` is a read-only reconciliation of explicit STATE identity/version/status claims, session/checkpoint references, accepted decisions, exact-version approval statements, scoped control-record links and generated INDEX/progress freshness. It does not infer free-form task semantics, repair prose or make owner decisions. `--strict` returns nonzero when any drift finding is reported.
- For consequential multi-file changes, agents use the defined outcome vocabulary (planned, attempted, completed, verified, partial, failed, blocked), read back all target files, reconcile canonical/derived records and run relevant validation before claiming `Verified`. A command exit alone is insufficient. Approval remains a separate owner-controlled state.
