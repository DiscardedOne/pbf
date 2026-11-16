# PROTOCOLS.md — Operating procedures

Follow these procedures in order unless the owner explicitly changes the workflow and the change is recorded.

## 1. Session startup

1. Read `AGENTS.md`, `_control/STATE.md`, and the newest session log.
2. Read the relevant phase in `_framework/WORKFLOW-PLAN.md`, the manifest entry for the current document, and dependencies listed in that entry.
3. Review relevant questions, assumptions, risks, decisions and glossary entries.
4. Run `python bp.py check --strict` if available; use manual checks if not. Read `_control/registry/INDEX.md` before opening documents.
5. Reconcile the written state with current files. If a discrepancy exists, inspect canonical sources, repair the checkpoint, and report the correction.
6. Tell the owner the current phase, what happened last, what is open, and the planned next action. Do not re-ask previously answered questions.
7. Continue from the exact next action unless the owner has a different immediate request; if temporarily diverted, return to the plan afterwards.

## 2. Adaptive documentation architecture

Phase 0 must use `_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md`. Capture the vision in D0.01 first, then design and conversationally review a tailored document architecture in D0.02 once there is enough signal. Do not require exhaustive project discovery before proposing this architecture: identify unknowns, make conditional branches explicit, and keep the proposal provisional. Do not scaffold project docs beyond D0.01/D0.02 until D0.02 is owner-approved, unless a documented and explicit override is used.

The default catalog is advisory. When adapting the structure, record the rationale and update D0.02, manifest, catalog/template mappings, stable IDs, dependencies, phase/tool maps, indexes, state and validation expectations. Preserve IDs for documents that retain their identity; retire rather than reuse IDs. Check structural impact and run strict validation after the change. Structure approval is revisable if the project changes.

## 3. Work modes and carry-forward

At setup, record whether work uses: (A) local working files, (B) chat plus uploaded/downloaded ZIP, or (C) plain chat without file tools.
- Mode A: edit in place; if Git is used, commit with a clear message.
- Mode B: extract the latest full workspace, edit it, and package the full workspace at useful checkpoints as `<project>-docs-sNNN.zip`. In the next chat, upload that archive. A partial diff is not a substitute for the source bundle.
- Mode C: present each changed file in full with its path, and state that the owner must save it; put the state file last.
Never claim a change was saved or verified if it was not.

## 4. Checkpoint rules

Checkpoint after: interview answers are incorporated; a document section is drafted/revised; a decision is accepted/rejected; a review verdict arrives; a meaningful risk/assumption changes; roughly 30 minutes of work; or the owner may leave.

A checkpoint means:
1. Save content to canonical files.
2. Update manifest and front matter.
3. Update question, assumption, risk, decision and glossary registries as applicable.
4. Update traceability and the change log when applicable.
5. Update `_control/STATE.md`: current document/step, next action, blockers, awaiting-user items, dirty work and ripple queue.
6. Update session log.
7. Run relevant checks and record what did/did not run.

If work is partially saved, list the exact files/sections under “In progress / possibly dirty”.

## 5. Document cycle

**Use progressive elaboration:** the owner's first description can be incomplete. Do not wait for a full requirements interview before drafting. On each meaningful conversational turn, determine the smallest useful documentation change, apply it, show the delta, and invite feedback. The normal cadence is one topic/document slice at a time; a small set of dependent files may change together when coherence requires it. The full question bank is a resource, not an intake form.

### 5.1 Prepare
- Read the catalog row: the “must contain” list is the document definition of done.
- Read dependency summaries and only the necessary source sections.
- Check registries for prior answers.
- Select only the next decision-critical question(s) from `QUESTION-BANK.md`; normally one direct question, sometimes 2–3 closely related questions.
- Identify the smallest useful output that can be drafted now, including a provisional high-level section if details remain unknown.
- Set status to `interviewing` while exploring, then `drafting` as soon as a meaningful first pass exists.

### 5.2 Interview and playback
- Name the topic and why it matters.
- For early vision topics, let the owner speak freely before probing.
- Restate the relevant understanding in 3–6 lines when a meaningful new concept or correction appears; invite correction without restating the entire project every turn.
- Ask one question by default; ask 2–3 related questions only when easier for the owner. Seven is reserved for an explicitly useful workshop. For each question, explain why it matters when useful; suggest options/defaults only where helpful.
- Do not block a draft on non-blocking unknowns. Clearly mark open questions, assumptions and proposed defaults.
- Cover “what if it fails?”, empty/invalid states, abuse/misuse, ownership, frequency/volume and what success looks like when relevant.
- If the owner does not know, propose a clearly labeled assumption with validation, research the question, create a spike, or defer if non-blocking.

### 5.3 Capture
- Save an interview record using `_framework/templates/interview-round.md`.
- Answers, interpretations and resulting file changes must not live only in chat.
- Assign permanent `Q-` IDs to unresolved questions; assumptions and risks get their own IDs.
- Add new domain terms to the glossary.
- Keep the owner's phrasing when it carries nuance; do not turn interpretations into quoted facts.

### 5.4 Draft
- Work section-by-section and iteration-by-iteration. Outline breadth before expanding detail, but start drafting a useful slice as soon as possible instead of outlining every document in full.
- Increase the manifest `maturity` from `outline` to `working` to `detailed` only as the content actually deepens. Workflow status and detail maturity are independent.
- Do not scaffold all planned files unless the owner requests it. Prefer `scaffold --only D0.01`, a small comma-separated selection, or `scaffold --phase N` for an explicitly agreed phase. `scaffold --all` is an opt-in bulk operation.
- Use the canonical owner document for each fact.
- Allocate stable IDs and links as concepts are introduced.
- Complete every catalog checklist item or mark it `N/A — reason` / create a tracked question.
- Embed Mermaid source where helpful; include failure paths where relevant.
- When a repeating family of specs grows, split it into child documents and update the manifest.

### 5.5 Self-review
Before sending a draft:
- Run `check` (strict mode if IDs/requirements have stabilized).
- Walk the catalog checklist.
- Check definitions/references, relative links, glossary terms and dependencies.
- Confirm that every `[TBD:Q-nnn]` is registered and still open.
- Compare diagrams to text; do not claim rendered validation unless performed.
- Remove accidental duplicated facts and vague requirements.
- Set `in-review` only after self-review passes; fill accurate front-matter summary.

### 5.5.1 Consequential change completion and reporting

For a consequential multi-file operation, use the outcome vocabulary and verification sequence in `_framework/OPERATING-MANUAL.md` → “Verified completion reporting”. In particular:

1. State the expected postconditions and target paths before changing canonical records.
2. After writes, read the files back from the intended workspace; compare the actual IDs, versions, statuses and corresponding manifest/registry rows.
3. Run relevant validation (normally `check --strict`; also `index --check` and/or `audit-state --strict` when those records are affected).
4. Assign `Verified` only when read-back and relevant checks pass. Use `Completed; verification pending`, `Partial`, `Failed` or `Blocked` where appropriate.
5. If an operation changes only part of a multi-file set, preserve and identify the actual partial state; do not claim the intended set is complete or silently invent the missing record.
6. Keep document approval separate from technical completion. Only the existing explicit owner-approval process can establish approval of an exact version.

Do not create a separate completion register or hash every ordinary edit. Use a compact outcome/files/observed-values/validation summary in the response and the existing session log when warranted.

### 5.6 Present for owner review
Provide a compact change digest with the relevant purpose, what changed, consequential decisions, assumptions/open questions, and exact file path. Invite feedback in natural language. Request a formal approve / approve-with-notes / changes verdict only when the whole document is genuinely review-ready or a material decision needs explicit acceptance; do not turn every small iteration into a formal gate.
Apply changes and report the difference, not the entire content again, unless asked.

### 5.7 Approve

Explicit owner approval *of this document* is required. “Approved”, “lock this”, or an unambiguous equivalent counts; silence, general enthusiasm or the end of a session do not. Before asking for approval, finish self-review and run `python bp.py set-status DOC in-review`. After the owner approves, run:

```bash
python bp.py approve DOC_ID --evidence "Owner explicitly approved D1.03 during session-003-2026-10-23.md review"
```

The command verifies the adaptive-architecture gate and upstream approval integrity, refuses hollow content, updates status/version, and records a full SHA-256 fingerprint over the normalized body plus meaning-bearing metadata in `_control/registry/APPROVALS.md`. The same successful approval is also written as a `status_transition`-equivalent `approval` event to `_control/logs/status-transitions.jsonl`. Approval evidence is self-attested and cannot authenticate the human.

**Recommended evidence format:** include (1) the owner's genuine words or a faithful description of the explicit approval and (2) a reference to the actual `_control/logs/sessions/session-NNN-YYYY-MM-DD.md` record. The tool emits a soft warning when evidence is unusually short or has no recognizable session reference; this is guidance, not identity verification. Never invent evidence to silence the warning.

The event log is appended only after the manifest, front matter and approval registry write succeed. If the event-log append fails, the command returns an error and explicitly says the underlying approval may already have been applied; inspect the workspace, restore write access, reconcile the missing event, and run `check --strict` before proceeding.

To change an approved document: `set-status DOC needs-revision --reason "..."`, list affected dependents (`impact DOC`), revise, `set-status DOC in-review`, obtain approval again. The reason is persisted in the status event log. Scaffold creation, applicability, maturity, profile changes and architecture overrides are logged there as well. `check` validates JSONL structure and warns when the last recorded status differs from the manifest (manual edits may be legitimate, but must be reconciled).

See [`LINT-RULES.md`](LINT-RULES.md) for the canonical lint rule definitions, placeholder markers and suppression syntax. See [`GUIDE.md`](GUIDE.md) for the complete command/operating reference. Git tags are recommended for accepted project baselines/releases, not for every individual document approval.

### 5.8 Continue

Continue from the owner's feedback and the next useful dependency, not from a rigid document queue alone. A document can be discussed and revised section-by-section while it remains `drafting`. Move focus when the owner is ready, when a dependency requires it, or when a short exploratory branch will clarify a current decision. Do not claim a phase is accepted until its explicit gate is passed. Future-topic discussion can be recorded as provisional/parked without prematurely approving downstream designs.

### 5.9 Incremental review and feedback

At the end of a meaningful documentation iteration, present only the relevant change digest:
- What was added or changed, with file paths.
- What was derived from the owner's input versus proposed by the collaborator.
- Any consequential trade-off, assumption, or unresolved question.
- What feedback is needed now (normally one focused question or a request to review the slice).

A scope-limited “yes, that section looks right” can be recorded as provisional acceptance of that section/decision. It is not whole-document approval unless the owner explicitly approves the whole document. Use `_framework/templates/iteration-review.md` for significant iterations; do not create review-log ceremony for trivial wording edits.

## 6. Material decisions and ADRs

Create an ADR when a decision is hard to reverse, affects multiple components, carries material cost/security/operational trade-offs, or the owner asks “why this, not that?”
1. State the decision question and its drivers/requirements.
2. Research facts that may have changed.
3. Compare 2–4 viable options including benefits, costs, risks, lock-in and unknowns.
4. Make a recommendation with rationale.
5. Record the owner's choice and consequences.
6. Add the ADR to `_control/registry/DECISIONS.md` and link it from affected docs.
7. Preserve superseded ADRs and their history.

## 7. Change control / ripple queue

Classify changes:
- **Clarification:** no meaning change; fix and log.
- **Amendment:** changes meaning within one source document.
- **Cascade:** invalidates downstream documents, IDs, diagrams, tests, or plans.
- **Pivot:** materially changes vision, audience, operating model or MVP boundary.

For amendment/cascade/pivot:
1. Identify the source-of-truth document and affected stable IDs.
2. Use `python bp.py impact D#.#` for dependency impact, and `impact FR-001` etc. for text references.
3. Explain the likely impact to the owner before changing approved material.
4. Apply the change to the canonical source first; update version and changelog.
5. Mark dependent approved/in-review documents `needs-revision`; add them to STATE's ripple queue with reason.
6. Repair dependencies upstream-first, then re-run checks and reapprove.
7. If a pivot invalidates broad scope, stop downstream drafting and agree a replan.

## 8. Research protocol

For external facts that influence decisions (versions, pricing, API behavior, availability, licensing, regulations, competing products), search current authoritative sources when available. Capture:
- question and relevance;
- source name, full URL and access date;
- important findings with claim-to-source links;
- source limitations, uncertainty and any conflicting data;
- conclusion and impacted documents/decisions.
If research is unavailable, record `[unverified]` and create a research question. Do not present marketing claims or one secondary source as definitive evidence.

## 9. Phase-gate protocol

1. Confirm all intended phase documents exist and statuses are current.
2. Run `python bp.py check --strict --gate N`; fix errors or disclose tool limitations. Use a manual gate checklist if execution is unavailable.
3. Walk `_framework/QUALITY-GATES.md` for that phase.
4. Resolve the ripple queue for the phase; no affected document may be silently treated as current.
5. Review blocking questions, assumptions, risks, ADRs, traceability and diagram/text consistency.
6. Create a phase report using `_framework/templates/phase-report.md`.
7. Present a digest and ask explicitly whether the owner accepts the phase and freezes its baseline.
8. If accepted, record the gate in STATE and the report; move to the next phase. If declined, capture the reasons and actions.

## 10. Recovery protocol

- **STATE is missing/stale:** reconstruct from manifest, project docs, latest session/interview/gate reports and registries. Tell the owner what was inferred; ask only about material uncertainty.
- **Docs conflict:** determine each fact's canonical owner. If evidence does not resolve the conflict, ask the owner; do not choose silently.
- **Vision pivot:** update D0.01 and scope, preserve prior versions/change record, identify affected docs, and agree which phases must reopen.
- **Scope explosion:** reassert MVP boundaries; move extras to the parking lot or a later release.
- **Lost terminology:** reconcile with GLOSSARY and update aliases consistently.
- **Tool unavailable:** do not block all progress; use manual checks and clearly state what's unverified.
- **Context or ZIP missing:** request the latest full bundle rather than reconstructing unseen content from memory.

## 11. Session close protocol

1. Finish or park the current step; mark dirty work exactly.
2. Update documents, manifest, registries, traceability and changelog.
3. Run the checker; fix low-cost errors and list remaining findings.
4. Update STATE's current phase/document, next action, blockers, awaiting-owner items, ripple queue and checkpoint.
5. Finish the session log with decisions, files changed, open items and exact next action.
6. Update docs map/links if files moved.
7. At phase gate, write the gate report.
8. In ZIP mode, package the full current workspace and tell the owner to upload it next time.
9. State honestly what was completed and what was not validated.
