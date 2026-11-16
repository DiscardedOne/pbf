# _control/STATE.md — Live project checkpoint

> Keep this concise (≈150 lines max), current and sufficient for a fresh session to resume. Detailed history belongs in `_control/logs/`. If this file disagrees with `_control/registry/MANIFEST.md` or the documents, the files win — repair this file and say so.

| Field | Value |
|---|---|
| Framework version | See `_framework/FRAMEWORK-MANIFEST.json` |
| Workspace setup provenance | Pending — record setup date, method and verification result after creation |
| Project name | Not set |
| Project type | Not set |
| Documentation depth | Standard starter default — provisional; review during D0.02 |
| Working mode | Not set — local files / chat + ZIP / plain chat |
| Current phase | P0 — Framework setup & vision capture |
| Current document | D0.01 — Vision capture and playback |
| Document step | Awaiting the owner's vision; capture a small first slice, then play it back |
| Session count | 0 |
| Last clean checkpoint | Fresh starter workspace — no project work yet |
| Last updated | — |
| Latest handoff | — |

> `Last updated` records the session that last changed this checkpoint. `Last clean checkpoint` records the latest clean persisted workspace checkpoint. If the checkpoint intentionally remains unchanged after a later session, append a meaningful explanation to `Last updated`, for example `a prior session (reason: STATE was intentionally unchanged in this session)`. `python bp.py audit-state` reports unexplained differences; it never edits this file.

## Project in brief

_Not yet written. After the first vision playback is confirmed, replace this with 5–10 lines: what is being built, for whom, why, project type, and the few most important constraints and decisions. A new session should be able to orient from this section alone._

## Next action

Invite the owner to describe their idea freely (no questionnaire). Reflect it back briefly, create `D0.01` with `python bp.py scaffold --only D0.01`, then continue with `_framework/CONVERSATIONAL-WORKFLOW.md` and `_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md`.

## In progress / possibly dirty

- (none)

## Awaiting the owner

- (none)

## Ripple queue

_Documents set to `needs-revision` by a change, with the reason. Resolve upstream-first before the phase gate._

- (none)

## Progress dashboard

<!-- PROGRESS:START -->
_Selected profile: **Standard**. Only active, in-profile documents contribute._

| Phase | Name | Approved / total | Progress |
|---|---|---|---|
| 0 | Framework setup & vision capture | 0 / 2 | 0% |
| 1 | Discovery & business framing | 0 / 4 | 0% |
| 2 | Product definition & requirements | 0 / 5 | 0% |
| 3 | Domain, data & integrations | 0 / 2 | 0% |
| 4 | High-level architecture | 0 / 8 | 0% |
| 5 | Low-level technical design | 0 / 3 | 0% |
| 6 | Quality, security & operations | 0 / 2 | 0% |
| 7 | Delivery planning | 0 / 4 | 0% |
| 8 | Coherence audit & sign-off | 0 / 2 | 0% |
| **All** | | **0 / 32** | **0%** |

<!-- PROGRESS:END -->

_Starter baseline only: run `python bp.py status --write` after project architecture and applicability are tailored. The generated zero counts are not a project progress assessment._

## Gate history

| Gate | Date | Result | Report |
|---|---|---|---|
| None | | | |

## Key decisions

The source of truth is `_control/registry/DECISIONS.md` (architecture/design) and `_control/registry/APPROVALS.md` (owner approvals).

- (none yet)

## Resume checklist

1. Read `AGENTS.md`, this file, the newest session log and `_control/registry/INDEX.md`.
2. Run `python bp.py check --strict` (if you can execute code).
3. Continue from the exact next action above; load other framework documents on demand (see `AGENTS.md`).
