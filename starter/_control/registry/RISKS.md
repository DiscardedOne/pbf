# RISKS.md — Canonical risk register

Likelihood/impact use `Low`, `Medium`, `High`, or `Critical`. Status: `open`, `mitigating`, `accepted`, `closed`. Closed risks retain the resolution evidence.

| ID | Risk | Cause | Likelihood | Impact | Mitigation | Trigger / contingency | Owner | Status | Docs |
|---|---|---|---|---|---|---|---|---|---|
| RSK-001 | Session continuity can fail if the latest project bundle or state checkpoint is not carried forward. | Work is spread across chats and files. | Medium | High | Package the full workspace at handoff; record exact next action and dirty work. | If state is stale, reconstruct from canonical files and logs before editing. | Documentation steward | open | `_control/STATE.md`, `_framework/PROTOCOLS.md` |
| RSK-002 | Premature architecture may constrain product discovery. | Technology decisions are made before needs and quality drivers are understood. | Medium | High | Enforce phase gates; put later-phase ideas in the parking lot. | Reopen earlier phases if core assumptions fail. | Product owner | open | `_framework/WORKFLOW-PLAN.md` |
