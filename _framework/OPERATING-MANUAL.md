# Operating Manual — Product Discovery and Documentation Stewardship

## 1. Purpose

This manual governs the use of the framework to transform an evolving idea into a traceable, testable, internally consistent planning baseline. It intentionally separates the *project methodology* from the *project's own requirements*. Customize the latter, not the general rules, unless a formal framework replan is agreed and recorded.

## 2. Mandatory adaptive documentation architecture (Phase 0)

The default catalog is a candidate inventory, not a required final directory tree. Before broad project-document scaffolding, use `_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md` to design and conversationally review the project's own document groups, granularity, sources of truth, dependencies, diagrams, quality coverage and phase fit.

- Start with a useful vision playback (`D0.01`). Do not delay it while asking a large set of questions.
- Once there is enough signal, propose a provisional structure in `D0.02` using `_framework/templates/adaptive-document-architecture.md`.
- Review the structure with the owner. Explain key choices, conditional groups, omissions and what future evidence may change the proposal.
- Before ordinary scaffolding, `D0.02` must have explicit owner approval as a **provisional baseline**. This is acceptance of a provisional direction/structure, not a promise that the structure never changes; it does not by itself approve every document in that structure.
- The only default bootstrap documents before that approval are `D0.01` and `D0.02`. Use `--override-architecture-gate --override-reason "<reason>"` only when there is a recorded reason to work ahead of the proposed structure.
- When new learning changes the structure, update `D0.02`, `_control/registry/MANIFEST.md`, `_framework/DOC-CATALOG.md`, dependencies, links, phase mappings, validation assumptions and state as applicable. Preserve stable IDs and historical decisions.

A structure review is intentionally lightweight: it defines the shape and coverage of the documentation, not every future document's contents. Product discovery and low-level design remain conversational and incremental.

## 3. Evidence and certainty taxonomy

Use labels whenever a reader could confuse interpretation with fact:

- **STATED** — explicitly provided by the owner.
- **OBSERVED** — directly present in a supplied artifact or verified system output.
- **CONFIRMED** — owner has reviewed and accepted it.
- **INFERRED** — a reasoned interpretation, not explicitly stated.
- **PROPOSED** — a recommendation awaiting owner approval.
- **ASSUMED** — temporarily treated as true, with an owner and validation plan in `_control/registry/ASSUMPTIONS.md`.
- **OPEN** — unresolved, recorded in `_control/registry/QUESTIONS.md`; use `[TBD:Q-nnn]` only where it materially blocks an answer.
- **DEFERRED** — deliberately postponed with rationale, owner, and revisit trigger.
- **REJECTED** — considered but not selected; preserve rationale for consequential options.

Do not convert a proposal or inference into a confirmed fact without approval or documented evidence. A phase may proceed with non-blocking open questions only when their deferral is explicit.

## 4. Discovery and interview behavior

**Work conversationally and incrementally.** The owner is not responsible for arriving with a complete specification. Do not make full discovery completion a precondition for drafting useful documentation. Begin with the information already available, record provisional interpretations honestly, and use feedback to deepen the work over multiple turns. Follow `_framework/CONVERSATIONAL-WORKFLOW.md` as the primary collaboration pattern.

- Let the owner explain the vision without interruption at the start of discovery.
- Play it back in a compact, structured form before detailed questions. Invite corrections.
- Default to one direct, high-impact question at a time. Ask 2–3 related questions together only when doing so clearly helps; seven is an upper bound for a purposeful workshop, not a normal target. Prioritize by product impact and dependency.
- For closed decisions, offer two to four options and a recommendation only when it helps; state the trade-offs and keep the final choice with the owner.
- Explain why a question matters when the consequence is not obvious.
- Do not ask for information already confirmed in canonical project files.
- Capture questions, answers (near-verbatim where possible), interpretations, resulting document changes, and new register items in interview logs.
- When the owner does not know, propose a sensible default and log it as an assumption, research it, create a validation spike, or defer it if non-blocking. Do not quietly guess.
- After enough information is available to state a meaningful slice, create or revise that slice now. Do not ask every remaining question before writing.
- Review and improve documents section-by-section. A section can be provisionally accepted while the whole document remains in `drafting`; full `approved` status means the owner explicitly accepted the current whole-document version at its intended maturity; it is not a permanent freeze. Material edits require the normal revision, impact review and reapproval cycle.
- The conversation may revisit earlier phases at any time. Preserve confirmed history, distinguish new proposals from accepted facts, and run change-impact analysis when meaning changes.

## 5. Document authoring rules

- Markdown is canonical. Mermaid source belongs in Markdown files and should be readable in version control.
- Every manifest-backed project document under `docs/` has YAML front matter: `doc_id`, `title`, `phase`, `status`, `maturity`, `version`, `last_updated`, `depends_on`, `summary`.
- The manifest owns current ID/path/phase/status/detail maturity/dependencies; the document body owns the detailed content. Front matter status/dependencies/maturity must match the manifest.
- One canonical home for each fact, rule, metric and decision. Other docs link to the owner document.
- Use relative links and stable IDs; avoid copy-pasting the same decision into several places. Grow each document through outline → working → detailed maturity instead of forcing full detail in its first draft.
- Use active voice, concrete examples, explicit units and dates, and precise success/failure behavior.
- Replace vague quality adjectives with measurable targets or defined acceptance tests.
- Write requirements as atomic, observable statements with source, priority and acceptance criteria.
- Include validation, permissions, duplicates, concurrency, timeouts, dependency failures, recovery and audit behavior where applicable.
- Include non-functional/security/privacy/accessibility/operational concerns proportionate to project risk; explicit N/A is acceptable with rationale.
- Avoid giant monoliths. Split docs after roughly 600 lines or when they cover multiple independent concerns. Preserve a stable index path and update the manifest.
- Never store credentials, API tokens, private keys or other secret values. Document secret names, owners and secret-store references only.

## 6. Stable identifiers

Use permanent IDs; never reuse or renumber them. Suggested prefixes and canonical owners:

| Prefix | Meaning | Canonical owner |
|---|---|---|
| `G` / `SM` | Business goals / success metrics | Goals and metrics |
| `STK` / `PER` | Stakeholders / personas | Stakeholders and journeys |
| `CON` / `ASM` | Constraints / assumptions | Constraints and assumption registry |
| `FEAT` / `UC` / `US` | Features / use cases / user stories | Feature catalog / use cases |
| `FR` / `NFR` / `BR` | Functional / non-functional requirements / business rules | Requirement/rule documents |
| `ENT` | Domain entities or concepts | Domain model |
| `API` / `EVT` | API operations / event types | Interface/event contracts |
| `CMP` | Runtime or logical components | Architecture component catalog |
| `TC` | Test/acceptance case | Test strategy/catalog |
| `MS` / `EP` | Milestones / epics | Roadmap / work breakdown |
| `RSK` / `Q` / `ADR` | Risks / questions / decisions | Registries / ADRs |
| `D<phase>.<nn>` | Documentation records | Manifest |

The `D` IDs are documentation IDs, not product entities. Repeatable document IDs can use `D5.03.01`. Every business/entity/requirement ID should be defined once in its owner document and referenced elsewhere.

## 7. Requirement quality

A useful requirement includes:
- Stable ID, name, source, rationale, priority and status.
- An atomic statement with one primary behavior or quality obligation.
- Preconditions, inputs/outputs and business rules where relevant.
- Observable acceptance criteria, preferably Given/When/Then for complex behavior.
- Failure and edge cases, including validation, authorization, retries, duplicates, concurrency and dependency outages.
- Traceability to goal, use case, implementing component/interface, and verification method.
- An owner or next action for unresolved details.

For non-functional requirements, state the operating condition, metric, target/threshold and measurement method. If a numeric target cannot yet be chosen, log the question and the method for establishing it.

## 8. Architecture and design reasoning

- Begin with architectural drivers and quality-attribute scenarios, not technology preferences alone.
- Compare viable options; record material, expensive-to-reverse or cross-cutting choices in an ADR.
- Keep architecture views consistent: context, container, component, data flow, deployment, trust boundary and key sequence views.
- Specify data ownership, consistency, transaction boundaries, lifecycle, retention, errors, timeouts, retries, idempotency, observability and recovery.
- Research versions, licensing, pricing, API limits and regulation when they influence a consequential decision. Record source URL and access date in a research note.
- State assumptions and the validation/spike needed to resolve risky uncertainties.

## 9. Source-of-truth and state model

- `_control/STATE.md` is the session-resume checkpoint, not the canonical content of project requirements.
- `_control/registry/MANIFEST.md` is authoritative for document inventory/status/dependencies.
- `_control/registry/QUESTIONS.md`, `ASSUMPTIONS.md`, `RISKS.md`, `DECISIONS.md`, and `GLOSSARY.md` are canonical cross-document registries/indexes.
- Document content belongs under `docs/`; framework procedure belongs under `_framework/`.
- Session/interview/gate history belongs under `_control/logs/`.
- Never use assistant memory as the sole source of truth when files can be carried forward.

## 10. Review and approval

- A review can focus on a newly drafted slice; do not require the owner to review the whole package on each iteration.
- Record scope-limited provisional acceptances where useful. Do not treat these as whole-document or phase approval unless clearly stated.
- Phase gates control when a baseline is stable enough to rely on for downstream work; they do not ban exploratory conversation about future topics.

- A review can focus on a newly drafted slice; do not require the owner to review the whole package on each iteration.
- Record scope-limited provisional acceptances where useful. Do not treat these as whole-document or phase approval unless clearly stated.
- Phase gates control when a baseline is stable enough to rely on for downstream work; they do not ban exploratory conversation about future topics.

- Drafts are presented with a review digest: purpose, key decisions, main diagram, assumptions, open questions, and the areas most needing scrutiny.
- A document is approved only when the owner explicitly approves it. Silence is not approval.
- A phase gate is a separate decision from document review. The gate report lists documents, status, checks, decisions, deferred items, risks and recommended outcome.
- `approved` means approved against the current upstream baseline, not eternal truth.
- Partial approval may be recorded in the document body, but the whole document stays `in-review` until its scope is accepted.
- Do not let a script approve a document or gate. The `approve` command only *records* an approval the owner has given: it requires `--evidence` (the owner's words or a session-log reference), refuses documents with unfilled template prompts, empty sections or fields, unticked checklist items, untagged TBDs or unapproved upstream dependencies, bumps the version, and stores a full SHA-256 fingerprint of the body plus approval-bearing metadata in `_control/registry/APPROVALS.md`; maturity and last-updated date are excluded, while title, summary, phase, path, dependencies, applicability/rationale and profile tier are included.
- Approved content is hash-locked. If an approved document's body changes, `check` fails until it is set to `needs-revision`, revised, and re-approved. This makes silent edits visible; it cannot prove the owner really approved, so the evidence must be honest.
- Move documents through the lifecycle with `set-status` (manifest and front matter change together); never hand-edit `Status` in only one place.

## 11. Change control and coherence

Any material change to an in-review/approved document, stable requirement, scope, domain invariant, metric or ADR must be classified:

1. **Clarification:** no change of meaning; correct and record.
2. **Amendment:** meaning changes within the source document; record version and rationale.
3. **Cascade:** downstream content may be invalidated; perform dependency and reference impact analysis.
4. **Pivot:** project vision/scope/operating model changes; pause downstream drafting and replan.

For amendment/cascade/pivot: identify dependents, notify the owner of the impact, update the source of truth first, put affected approved/in-review documents in `needs-revision`, add them to the ripple queue, repair dependent docs in dependency order, rerun checks, and reapprove affected documents. Preserve superseded history.

## 12. Quality gates and uncertainty

No gate is passed merely because files exist or progress reaches 100%. The checklist, automated checks (where available), risks, open questions, traceability and owner acceptance all matter. A high-risk uncertainty can require a prototype/spike or external research before architecture is accepted. State what was checked, what was not checked, and residual risk.

## 13. Session close

Before ending a session:
1. Save all agreed content.
2. Update manifest/front matter and all affected registries.
3. Run `check`; use strict mode at review and gates where feasible.
4. Update traceability where applicable.
5. Update `_control/STATE.md`, especially the next exact action, blockers, current document step, dirty files and ripple queue.
6. Create/update a session log with files changed and user decisions.
7. Record gate reports when a phase gate is reviewed.
8. Check relative links and Mermaid syntax as far as tooling permits.
9. Package the entire workspace ZIP when working in chat/sandbox mode; the next session needs the complete current bundle, not just changed files.
10. Tell the owner truthfully what was and was not validated.


## Phase 5 reliability additions — reconciliation and verified completion

### Read-only state audit

Run `python bp.py audit-state` when starting a session if the checkpoint appears stale, before a consequential handoff, or after a multi-document change. The command is read-only and compares explicit claims/records for: current document identity/version/status; stale version references in the current-document, document-step, awaiting-owner and next-action areas; latest handoff/session existence and numeric freshness; `Last updated` versus the stated clean checkpoint and available session logs; accepted ADR claims; exact-version approval contradictions; missing session/document/local-link references in STATE, session logs and the approval/decision registries; and generated INDEX/progress-block freshness. Use `--strict` when an automated workflow should return a nonzero exit code for any reported drift.

The audit deliberately does not infer arbitrary natural-language task logic. For STATE-004, when `Last updated` intentionally refers to an older session than the latest clean checkpoint or a newer available session, record a meaningful explanation inline, for example `session-014 (reason: STATE was intentionally unchanged in session-015)`. The exception is a reviewable explanation, not an automatic override of contradictory project facts. An absent/placeholder Next action or explicit incompatible status claims are reported for review; the command does not generate or repair actions. INDEX and STATE progress freshness are reported, but the audit never regenerates those blocks.

### Architecture/manifest conformance

When the configured adaptive-architecture document (normally D0.02) is validly approved, `check --strict` compares its explicit inventory dispositions with the operational manifest. Core and Core (light) map to `active`; Conditional maps to `conditional`; Excluded maps to `excluded`; Deferred maps to `deferred`; Merged source documents map to `excluded` and must identify their host in the mapping/rationale. New records require an explicit stable ID and valid manifest applicability. Split records require one original ID and at least two child IDs using `original → child1, child2`; every referenced ID must have explicit manifest applicability. Do not infer applicability or whether the original is retired from the disposition label. Before valid approval, the comparison remains advisory. The validator reports discrepancies and never edits the architecture, manifest or dependency graph.

### Verified completion reporting

Apply this contract to **consequential multi-file operations**: architecture/manifest changes, document version or status changes, dependency/registry cascades, approval-sensitive edits, session closeouts and other changes where individually successful writes can leave the workspace inconsistent. Do not turn trivial wording edits into a reporting ceremony.

#### Outcome vocabulary

| State | Meaning | Permitted claim |
|---|---|---|
| **Planned** | No operation has been invoked. | “Planned”; never “done”. |
| **Attempted** | A write/tool/command was invoked, but persistence or its full effect has not been established. | “Attempted; outcome not yet established.” |
| **Completed** | Every requested write is present at its intended path on immediate read-back, but relevant cross-file validation is not yet complete. | “Completed; verification pending.” |
| **Verified** | Read-back confirms every required postcondition and all relevant validation checks pass. | “Verified”, with the checks and observed result named. |
| **Partial** | Some requested changes persisted, but a required outcome is missing, inconsistent, or validation fails. | “Partially completed”; list persisted and outstanding parts. |
| **Failed** | The attempt produced none of the requested persisted result and no usable partial result remains. | “Failed”; identify the failed attempt and observed unchanged state. |
| **Blocked** | No attempt was made because authorization, access, a dependency, or a required capability was unavailable. | “Blocked”; identify the gate. |

`Planned` and `Attempted` describe progress before an outcome is established. A final operation disposition is normally `Completed`, `Verified`, `Partial`, `Failed` or `Blocked`. Do not use `Verified` as a synonym for “the command returned zero”.

#### Required verification sequence

1. **Define postconditions before writing.** For the consequential operation, identify the expected target paths and the meaningful result expected in each (for example, document ID/version/status, matching manifest row, registry entry, or generated index). Keep this compact; do not create a separate plan file for routine work.
2. **Perform the authorized writes.** Record which operations were actually invoked. Do not imply an unattempted step was performed.
3. **Read back the targets.** Re-open the actual files from the intended workspace and verify the expected values. Do not rely only on the write tool response, a diff preview, an in-memory object, or a success message.
4. **Reconcile cross-file ownership.** Check the canonical source and each affected derived/duplicated record: document front matter against manifest, approval record against the exact document version/fingerprint, dependency/decision/register entries, and generated views where relevant. Do not invent a missing owner decision to make the set consistent.
5. **Run relevant validation.** Use the applicable strict check, index check, state audit or focused command. Record the actual command, exit result and any errors/warnings. If a check was unavailable or not run, say so; do not label the operation `Verified`.
6. **Assign the final disposition.** If all required read-backs and relevant checks pass, use `Verified`. If every write is present but validation is still pending, use `Completed; verification pending`. If any required change is absent, inconsistent or fails validation, use `Partial`. Use `Failed` when no requested result persisted; use `Blocked` when no attempt was authorized/possible.
7. **Report actuals concisely.** Identify affected files and observed resulting IDs/versions/statuses; distinguish changed, unchanged and not-yet-checked files; state validation results and remaining work. Do not add per-edit hashes unless needed for an exact artifact/release or requested by the owner.

#### Approval is a separate dimension

Technical `Completed`/`Verified` status does not mean a document is owner-approved. Report its actual workflow status (for example, `in-review`) and approval state (for example, `awaiting owner review`) separately. Never create or infer approval evidence. A successful validation command, generated draft, or self-review cannot substitute for explicit owner approval of the exact version.

#### Contradictory tool result and read-back

If a tool or command reports success but read-back shows the requested file/version/metadata did not change, trust the read-back. Classify the operation as `Failed` if nothing persisted, or `Partial` if some related changes persisted. State that the operation was attempted and quote the observed contradiction. Never repeat the success claim from the tool output as the final result.

#### Concise reporting shape

For consequential work, use a small summary rather than a new mandatory register:

| Outcome | Affected files / observed values | Validation |
|---|---|---|
| `Verified` / `Partial` / `Failed` / `Blocked` / `Completed; verification pending` | Actual paths and resulting IDs, versions and statuses | Commands/checks actually run, exit result, warnings and not-run checks |

Then state the remaining work and approval state separately. Detailed chronology belongs in the existing session log when the operation merits a session record; do not duplicate every action in the user-facing response.
