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
summary: ""
---

> [[FILL: State the planning baseline version, review scope and owner-approved outcome.]]

# {{TITLE}}

## Baseline identity and scope
- **Baseline version:**
- **Profile:**
- **Scope covered:**
- **Owner / reviewers:**
- **Current baseline disposition:** provisional planning baseline / accepted current planning baseline / blocked

## Profile-specific quality evidence

Complete only the subsection matching the selected workspace profile. Mark the other two subsections `N/A: profile not selected` so readers can distinguish intentional omission from missing work.

### Lite — manual proportionate audit
Record the audit directly below. Check critical goals against requirements/deliverables, requirements against implementing components/interfaces, and requirements against verification tests. Identify orphaned goals, requirements, components and tests; record contradictions and explicit exceptions. Every accepted gap needs an owner, rationale and revisit trigger.

### Standard — linked traceability and coherence evidence
Reference the structured traceability fields in `D2.04` requirement entries and component specifications. Reference the findings, coverage review and disposition in `D8.01` without changing this document's manifest dependency on `D7.05`. Confirm that `D8.01` findings are resolved or explicitly accepted.

### Exhaustive — dedicated traceability evidence
Reference `D7.04` and the detailed coherence audit. Confirm that goal-to-requirement, requirement-to-component/interface and requirement-to-verification relationships have been examined, including orphan analysis and documented exceptions.

## Traceability and coherence review record
- **Requirement coverage evidence:**
- **Component/interface coverage evidence:**
- **Verification coverage evidence:**
- **Coherence audit evidence:**
- **Orphaned or contradictory items:**
- **Accepted exceptions (owner, rationale, revisit trigger):**

## Phase gate results
{{CHECKLIST}}

## Residual risks, assumptions and deferred work
- **Residual risks accepted:**
- **Assumptions requiring later validation:**
- **Deferred work and activation trigger:**

## Approval and reopening criteria
- **Owner approval evidence:**
- **Approval date:**
- **Accepted current version:**
- **Reopen when:** material requirement/architecture changes, traceability evidence becomes stale, a blocking assumption fails, or an accepted exception reaches its revisit trigger.

Approval means the owner accepted this document's current version and its recorded evidence. It does not mean the baseline can never change; material changes follow the normal needs-revision, impact-review and reapproval process.

## Change history

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | {{DATE}} | Initial scaffold | Phase work has not begun |
