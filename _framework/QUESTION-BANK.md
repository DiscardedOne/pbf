# QUESTION-BANK.md — Probing questions by phase

Use this as a prompt bank, not a script. Check the documentation and registries before asking. Ask only questions appropriate to the current uncertainty; default to conversational clarification. For any consequential topic, consider: “What would make this fail?”, “What happens in the empty or exceptional case?”, and “What am I not asking?”

## P0 — Vision capture and setup
- In your own words, what are you building, for whom and why now?
- What happens today without it? What do users do instead?
- What does success look like six months after launch?
- Who will use the documentation: you, developers, a team, coding agents, operators?
- What's already decided (platform, tech, budget, deadline, business model), and what's uncertain?
- What must it never do? What would make you abandon the idea?
- Would Lite, Standard or Exhaustive detail best suit your risk and implementation needs?
- Do you prefer review digests, in-file edits, or both? Which tools may be used for research and validation?

## P1 — Discovery and business framing
**Problem/users:** Who has the problem? How often and how severely? What is the current workaround and its cost? Who decides, pays, operates or is accountable? Who is not the target?
**Goals/metrics:** What are the top outcomes? What is a baseline and target? How can success be measured, by whom, and when? What would be a misleading/vanity metric?
**Scope:** What is the smallest version that delivers value? What is explicitly out of scope? Who may change scope and how?
**Constraints:** Budget to build/run? Deadline and why? Team skills/time? Mandatory platform/vendor? Portability/lock-in needs? Licensing/IP constraints?
**Business/market:** Is this personal use, funded, commercial, open source, internal? What alternatives exist, including “do nothing”? What makes it different, and what evidence supports the difference?
**Risk/legal:** What could kill the idea? What data is sensitive? Which jurisdictions, contracts, compliance or accessibility obligations might apply?

## P2 — Product definition and requirements
**Journeys:** Walk through a typical use from trigger to outcome. Where does the user get stuck? How do experts and novices differ?
**Features:** Which problem does each feature solve, for whom, and which goal does it support? Must/should/could/won't? What depends on what?
**Use cases:** What triggers the action? Preconditions, postconditions and permissions? What if input is invalid, missing, too large, duplicated or concurrent? What if offline or unauthorized? What's the empty state?
**Requirements:** How will each behavior be accepted/tested? Who may create/read/update/delete which data? Is audit/history required? What happens when data is deleted?
**Quality:** Expected users/data/requests now and later? Peak vs average? Latency budget per action? Availability/downtime tolerance? Supported devices, browsers, languages and accessibility needs? Security/privacy retention?
**UX:** What should the experience feel like? Which products are reference points? Key screens, navigation and content tone?

## P3 — Domain, data and integrations
- What are the key business nouns and terms? Which synonyms create ambiguity?
- What are the entities, relationships, lifecycle states and invariants?
- Who owns each field/domain object and what is the source of truth?
- How is data collected, used, shared, corrected, exported, deleted, archived and recovered?
- What sensitivity/classification applies, and how long may data be retained?
- What external systems are involved, who owns them, and what are their contracts, auth, cost, quotas and outage behaviors?
- Is communication synchronous, event-driven, batch, scheduled or webhook-based? What ordering/consistency is required?

## P4 — High-level architecture
- Which functional/quality requirements are hardest to satisfy or non-negotiable?
- What are you optimizing: time-to-build, simplicity, cost, performance, availability, flexibility, learning or portability? Rank trade-offs.
- Single deployable or multiple? Real-time/offline/multi-tenant/multi-region/mobile/desktop/extension/web needs?
- Which candidate architectures fit the drivers? What would each make easier or harder?
- Which technology versions, license, support, cost and vendor terms need current research?
- What are the system and trust boundaries? Who can cross them? What assets need protection?
- What should be prototyped first to remove high-risk uncertainty?
- If AI/LLMs are involved: what tasks require models; what quality, latency, privacy and cost limits apply; how is output evaluated and what is the fallback?

## P5 — Detailed technical design
- For each critical component, what does it own and explicitly not own?
- What are exact input/output schemas, validation, status/errors, auth, timeouts and versioning?
- What happens on retries, duplicate delivery, concurrency, partial failure or stale state?
- Database keys, indexes, constraints, transaction boundaries, migrations, delete semantics and audit trail?
- UI states: loading, empty, success, partial, error, offline, disabled and unauthorized?
- Algorithms: work through normal, boundary and failure examples. What is the expected result?
- What config differs by environment? How are secrets stored/rotated, without putting values in docs?
- For background jobs/events: idempotency, order, scheduling, retries, dead-lettering and replay?
- For AI: prompt versioning, input/output validation, evaluation set, guardrails, model fallback and cost controls?

## P6 — Quality, security and operations
- What test levels and automation give confidence? What is the definition of done?
- What are the worst impacts from data loss, money, privacy or reputation? How are they detected?
- How is service health observed? What are the alert thresholds, severity and owner?
- How are releases verified and rolled back? What downtime is acceptable?
- What recovery point and recovery time objectives are required? How often are restores tested?
- What load scenarios and performance budgets matter? When should capacity scale?
- What compliance evidence or data-subject handling is necessary?
- Who supports the system and handles incidents when the owner is unavailable?

## P7 — Delivery planning
- What is the earliest end-to-end walking skeleton that proves the architecture?
- Which dependencies or high-risk uncertainties should be addressed first?
- What can be parallelized safely? What is on the critical path?
- Who builds/reviews what, and what is the acceptance/definition-of-done?
- How will docs, contracts, tests and code remain synchronized?
- What can be cut if time/cost slips without breaking the core value proposition?
- What does launch monitoring and post-launch feedback look like?

## P8 — Coherence and sign-off
- What is still unproven, contradicted, unowned, or likely to change?
- Which goals/requirements/components/tests have no incoming or outgoing trace?
- Which approved decisions rely on assumptions that have not been validated?
- Do diagrams tell the same story as contracts and prose?
- Which residual risks are being accepted, by whom, and until what trigger?
- Could a new developer build the system without private conversation or hidden knowledge?
