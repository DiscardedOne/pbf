# CONVENTIONS.md — File, ID, status and writing conventions

## 1. Files and folders

- UTF-8 Markdown with LF line endings. File names use lowercase kebab-case; ADRs use `ADR-001-short-title.md`.
- Project deliverables live under `docs/`; framework instructions live under `_framework/`; authoritative registers live under `_control/registry/`; chronology lives under `_control/logs/`.
- Use relative links. Avoid local absolute paths; URLs belong in research/reference sections.
- Split a document when it becomes difficult to review, typically around 600 lines or when it covers unrelated concerns. Preserve a stable parent index and update the manifest.
- Do not create empty documents merely to fill a folder. `scaffold` should run only after Phase 0 scope tailoring.
- The `_control/STATE.md` progress dashboard between its markers is generated; do not hand-edit the block.

## 2. Front matter

Every manifest-backed document begins with:

```yaml
---
doc_id: D2.04
title: Functional requirements
phase: 2
status: drafting
maturity: outline
version: 0.1
last_updated: 2026-10-20
applicability: active
applicability_rationale: ""
profile_tier: standard
depends_on: [D2.02, D2.03]
summary: Defines atomic, testable functional obligations and their sources.
---
```

- `doc_id`, `title`, `phase`, `status`, `maturity`, `version`, `last_updated`, `applicability`, `profile_tier` and `depends_on` must agree with the matching manifest row (`applicability_rationale` is required only for conditional, deferred and excluded documents, and must match when present). The checker reports mismatches as errors. Maturity is `outline`, `working`, or `detailed`; applicability, profile tier, maturity and workflow status are independent dimensions. Approval fingerprints bind content plus meaning-bearing metadata, but exclude `maturity` and `last_updated`.
- `summary` is an informative 1–2 sentence result summary; keep current so a fresh session can determine if the full document needs to be read.
- Use `0.x` versions while drafting; `1.0` at first approval; increment for meaning-changing updates according to project version policy.
- Workflow `status` is changed with `set-status` and reaches `approved` only through `approve` (see `_control/registry/APPROVALS.md`); approved document bodies are hash-locked.
- One owner document defines each stable ID. Configured index files (`_control/registry/DECISIONS.md`, `_control/registry/MANIFEST.md`, `_control/registry/APPROVALS.md`, the generated `_control/registry/INDEX.md`, and the traceability document ID configured in `_control/WORKSPACE.json`) may list references without being treated as canonical definitions. Moving the traceability document requires updating its manifest path; the checker resolves index paths from that current location.

## 3. Document statuses and progress weights

| Status | Meaning | Progress weight |
|---|---|---:|
| `not-started` | Not begun | 0 |
| `interviewing` | Gathering information | 10 |
| `drafting` | Content being written | 40 |
| `needs-revision` | Previously drafted/reviewed/approved; upstream change requires revision | 50 |
| `in-review` | Self-review passed; awaiting owner review | 75 |
| `approved` | Explicitly approved by the owner | 100 |
| `superseded` | Replaced; historical record retained | excluded |
| `excluded` | Explicitly not needed; rationale recorded | excluded |
| `expanded` | Template row replaced by child document rows | excluded |

Allowed normal path: `not-started → interviewing → drafting → in-review → approved`. Changes may return `in-review → drafting`; upstream changes can set `approved/in-review → needs-revision → drafting`. Never mark `approved` without explicit owner approval.

The script weights by size (`S=1`, `M=2`, `L=3`) and workflow status. This measures workflow progress, not detail depth. The separate manifest `maturity` field tracks progressive elaboration; neither percentage nor maturity alone represents certainty, quality or effort.

## 4. Stable IDs

Format `PREFIX-NNN`, usually three digits; never reuse or renumber IDs. Retire IDs with a pointer to the successor.

| Prefix | Meaning | Canonical owner |
|---|---|---|
| `G`, `SM` | Goal, success metric | D1.03 |
| `STK`, `CON` | Stakeholder, constraint | D1.02 / D1.04 |
| `PER`, `FEAT` | Persona, feature | D2.01 / D2.02 |
| `UC`, `US` | Use case, user story | D2.03 |
| `FR`, `NFR`, `BR` | Functional requirement, quality requirement, business rule | D2.04 / D2.05 / D2.07 |
| `ENT` | Domain entity/concept | D3.01 |
| `API`, `EVT` | API operation, event/message type | D5.02 / D5.08 |
| `CMP` | Component | D4.03 |
| `TC` | Test/acceptance case | D6.01 |
| `MS`, `EP` | Milestone, epic/work package | D7.01 / D7.02 |
| `ASM`, `RSK`, `Q`, `ADR` | Assumption, risk, question, decision | Registries / ADR directory |
| `D<phase>.<nn>[.<nn>]` | Documentation record | Manifest |

ID definitions are headings or rows in the owner document. Do not define requirements inside a traceability table; that matrix references IDs. This convention allows automated linting to catch most accidental duplicates and missing references.

## 5. Inline markers

- `[TBD:Q-001]` — unresolved question relevant at this location. Must exist in `_control/registry/QUESTIONS.md`.
- `[ASM-001]` — this statement relies on a registered assumption.
- `[unverified]` — changing external fact not yet confirmed; also create a research action.
- `<!-- GUIDE: ... -->` — template guidance to remove before approval.
- `<!-- TODO: ... -->` — explicit work marker; not allowed in approved documents.
- `N/A — <reason>` — a checklist item is not applicable; include the reasoning and revisit trigger if needed.

Approved docs should not retain unresolved `[TBD]`, unchecked checklist items, or TODO comments. Some unresolved but non-blocking assumptions may remain if clearly visible and accepted.

## 6. Writing quality

1. One requirement per statement; one primary concern per document.
2. Requirements use `shall` for mandatory behavior, `should` for a strong preference, and `may` for optional behavior, with project vocabulary explained.
3. Quantify performance, availability, capacity, accessibility or retention requirements where meaningful: condition + threshold + measurement method.
4. Avoid ambiguous adjectives such as “fast”, “secure”, “easy”, “scalable”, “robust” or “intuitive” unless defined by measurable criteria.
5. State rationale for decisions and record materially rejected alternatives.
6. Use explicit units, currency codes, time zones, date formats, and boundary conditions.
7. Include examples for non-trivial rules, schemas, formulas and workflows.
8. Use active voice, short paragraphs and headings that reflect the question being answered.
9. Explicitly document success and failure behavior, not just ideal flows.
10. Include a short purpose, scope, inputs/dependencies, summary, open questions and references where appropriate.

## 7. Source-of-truth policy

- `_control/registry/MANIFEST.md`: document inventory/status/dependencies.
- `_control/registry/QUESTIONS.md`: unresolved questions and parking lot.
- `_control/registry/ASSUMPTIONS.md`: assumptions and validation plans.
- `_control/registry/RISKS.md`: risk register.
- `_control/registry/DECISIONS.md` + `docs/04-architecture/adr/`: decision index and decision records.
- `_control/registry/GLOSSARY.md`: canonical vocabulary.
- `_control/registry/CHANGELOG.md`: approved baseline change history.
- `_control/STATE.md`: current working position and exact resume instructions.
- `docs/`: project content.
- `_control/logs/`: session, interview and phase-gate history.

## 8. Mermaid conventions

Follow `_framework/DIAGRAMS.md`. Each diagram needs a purpose/caption and reading guide; names and IDs must agree with the text. The Python checker validates only a subset of structural syntax. Render/inspect critical diagrams and run the semantic consistency audit at gates.


## 9. Template prompts and lint suppressions

Shipped templates use only the explicit `[[FILL: ...]]` marker for unfinished template prompts. Replace every marker with actual project content before approval. Ordinary bracketed prose, citations, Markdown labels, inline code and escaped marker examples are not treated as unfilled prompts.

Rare literal-marker examples may use an escaped `\[[FILL: ...]]` spelling. If the marker must remain literally unescaped, use the narrowly scoped suppression syntax in `_framework/LINT-RULES.md`; suppression affects only TPL001 and requires a reason.
