# Project Blueprint Framework — Project Overview and Method

A readable, product-level explanation of PBF: why it exists, who it serves, how people and agents collaborate, and what the method is designed to produce. This reference is intended for owners, decision-makers and prospective users; it is not a technical installation manual.


---

## Project Blueprint Framework — project overview

### 1. Executive summary

Project Blueprint Framework (PBF) is a reusable way for a person and an AI agent to work together to turn an evolving project idea into a structured, reviewable and implementation-oriented documentation baseline.

It addresses a recurring problem: important project decisions are often scattered across conversations, informal notes, personal memory and disconnected documents. As the project develops, people can lose track of what is confirmed, what is merely proposed, what assumptions were made, why an architecture decision was selected and what remains unresolved. A new developer or AI session may then have to rediscover context or make guesses.

PBF provides a disciplined but adaptive way to capture this knowledge in a persistent Markdown workspace. It is designed to start from an incomplete idea, not a finished specification. The owner supplies intent and decisions; an AI agent helps discover implications, structure the information and maintain the documentation; the framework provides the rules, records and deterministic tools that help preserve consistency.

### 2. The central idea

The owner should be able to begin with an ordinary explanation such as:

> I want to build a service that helps a particular group of people solve a problem. I have a rough idea of how it should work, but I have not decided all the features, architecture or technical details.

The agent should not respond with an exhaustive questionnaire or a complete tree of empty templates. It should first explain what it understood, identify the most consequential uncertainties, ask focused questions and create a small useful first document. As the owner reacts and the project becomes clearer, the agent expands the documentation in reviewable increments.

The framework makes this process repeatable and persistent. It encourages a single canonical home for each important fact or decision and gives a new session an explicit way to reconstruct the current project state.

### 3. What is delivered

The framework delivers three cooperating things:

1. **A method:** a set of operating principles and workflows for discovery, documentation, review, change control and continuity.
2. **A workspace:** a project-specific directory containing Markdown documents, registers, approvals, state and a reusable runtime.
3. **A helper:** a Python command-line tool that performs selected deterministic operations such as workspace checks, metadata updates, indexes, approval fingerprints and state reconciliation.

The AI model and agent runtime are supplied separately by the user. PBF is not an AI product by itself.

### 4. What success looks like

A well-operated PBF workspace should help an owner and downstream implementer answer:

- What problem are we solving and for whom?
- What is the project intended to achieve?
- What is in scope, out of scope, conditional or deferred?
- What behavior and quality requirements have been established?
- What concepts, data, integrations and boundaries matter?
- What architecture has been proposed and why?
- Which choices are accepted and which are still proposals?
- What assumptions and risks need validation?
- What remains unresolved?
- What should the next person or session do next?

The purpose is to reduce avoidable guesswork and repeated discovery. It does not eliminate uncertainty or replace engineering judgment.

### 5. Design principles

- **Adaptive:** the documentation structure follows the project, not the other way around.
- **Conversational:** the owner can explain ideas naturally; questions are focused and purposeful.
- **Incremental:** useful work is produced in small slices rather than in one large generation.
- **Persistent:** canonical files, not chat history or model memory, are the durable project record.
- **Traceable:** decisions, assumptions, questions, risks and approvals have identifiable homes.
- **Human-governed:** the owner retains authority over direction, scope and approval.
- **Agent-assisted:** the agent performs analysis and documentation work but must verify consequential changes.
- **Harness-neutral by design:** the portable contract is explicit file-based bootstrap; native agent discovery is optional.
- **Proportionate:** the framework should be lightweight for simple projects and allow deeper structure when complexity warrants it.

### 6. Intended users

PBF is intended for people who own or lead projects and want an AI agent to help create and maintain a durable specification. Typical users include product owners, founders, developers, technical leads, architects and small teams. It can also help an implementation team receive a structured project handoff.

### 7. Scope and non-goals

PBF is strongest for greenfield discovery and planning. It can support change control while implementation progresses, but it is not a repository reverse-engineering product, source-code generator, project tracker, wiki server or automated code/documentation synchronizer.

It does not guarantee that the AI's reasoning is correct, that research is complete, or that all semantic defects are detectable by scripts. Human review remains essential for consequential decisions.

### 8. Release identity

The stable v3 release is **{{PBF_VERSION}}**, based on accepted workspace architecture revision 1.3.4. The release is designed for adaptive project discovery and documentation. Evaluation-project decisions and documents are not part of the reusable framework behavior.


---

## Purpose and problem addressed

### 1. The problem

Early project knowledge is rarely complete. It is commonly formed through conversation, examples, partial requirements, research, diagrams and changing decisions. If that information is not captured in a deliberate way, several problems appear:

- The original intent becomes distorted as implementation details accumulate.
- Confirmed facts and speculative ideas are mixed together.
- The same questions are asked again in later conversations.
- Documents disagree about versions, scope, terminology or dependencies.
- Decisions lose their rationale and become difficult to revisit safely.
- An implementation agent has to infer missing requirements.
- New team members cannot tell which document is authoritative.
- A project appears complete because many files exist, even though key uncertainties remain.

Traditional templates can help organize mature information, but a rigid template-first workflow can burden owners who do not yet know what the project needs. A large upfront questionnaire also assumes the owner already knows which details matter.

### 2. PBF's response

PBF combines a conversational process with a persistent documentation workspace and deterministic support tools. Its response is not to automate all project thinking. It is to make the thinking explicit and preserve the results.

The method begins with the owner's current understanding. The agent reflects it, separates knowledge from uncertainty, asks only questions that matter to the next decision and creates a useful first document. It then proposes a tailored documentation architecture and obtains owner acceptance before expanding the workspace substantially.

As the project evolves, PBF encourages updates to canonical records, impact analysis, validation and session handoffs.

### 3. Intended benefits

The framework is designed to:

- reduce repeated explanation across sessions;
- make decisions and their rationale easier to find;
- expose unknowns before they become hidden implementation assumptions;
- maintain consistent document metadata and navigation;
- make approval status explicit and version-specific;
- help a future developer or agent understand the system without relying on the original conversation;
- scale documentation depth to project complexity;
- create a coherent handoff from discovery/planning into engineering.

These are intended benefits, not a measured guarantee for every project or AI model. Their realization depends on the quality of the owner's input, agent behavior, review discipline and the environment in which the workspace is used.

### 4. How PBF differs from a static template pack

A static template pack supplies blank forms. PBF includes a process for deciding which records are useful, when they should be created, how they depend on one another, who owns decisions, how documents mature and how a new session resumes work. The default catalog is a source of candidate document types, not a mandatory list.

### 5. How PBF differs from a chat-only approach

A chat-only approach may provide useful reasoning but can leave canonical information dispersed across conversation history. PBF treats workspace files as the durable project record. Conversations are an interaction surface; the workspace is the continuity mechanism.

### 6. How PBF differs from a conventional project-management system

PBF is concerned with project understanding and specification. It does not replace task boards, issue trackers, source control, build systems, CI/CD, design tools or production observability. It may produce documentation that informs those systems, but it does not operate them.

### 7. The intended boundary

PBF should help move a project from an incomplete idea toward a coherent planning baseline. It should not pretend that every engineering question can be settled before prototyping or that documentation alone proves a system is feasible, secure, usable or correct.


---

## People and responsibilities

### 1. The human owner

The owner is the source of project intent and retains authority over consequential choices. The owner is expected to provide:

- the initial idea, problem context and intended outcomes;
- relevant constraints, preferences, examples and priorities;
- corrections when the agent misunderstands the project;
- decisions about scope, trade-offs and acceptance;
- explicit review and approval of exact document versions;
- authorization for external or destructive actions when applicable.

The owner is not expected to know every technical detail upfront. The framework is intended to let the owner contribute progressively.

### 2. The AI agent

The agent performs the documentation and analytical work within the permissions it has been given:

- read the portable instructions and current workspace state;
- understand and reflect the owner's input;
- identify uncertainty, implications and relevant dependencies;
- ask focused questions;
- research external facts when needed and record sources/uncertainty;
- propose a suitable documentation architecture;
- draft and revise Markdown documents;
- maintain manifest/front matter and relevant registers using supported commands;
- assess impacts when decisions change;
- run checks and read back consequential changes;
- report actual outcomes accurately;
- prepare a clear session handoff.

The agent must not fabricate facts, owner decisions, approvals, test results or tool outcomes. Tool success is not proof that a file changed. Technical completion and owner approval are separate dimensions.

### 3. The framework

The framework supplies stable instructions and deterministic support:

- conversational and adaptive workflow;
- candidate document catalog and templates;
- quality gates, writing conventions and protocols;
- workspace layout and file ownership rules;
- manifest and project state model;
- approval fingerprinting and transition constraints;
- validation, linting, indexes, progress and state-audit commands;
- source packaging and workspace creation lifecycle.

The framework does not supply domain knowledge, decide whether the product should exist, authenticate the owner's identity or guarantee the correctness of AI-produced content.

### 4. Responsibility matrix

| Activity | Owner | Agent | Framework/tooling |
|---|---|---|---|
| Explain project intent | Accountable | Listens and reflects | Provides method |
| Identify missing information | Reviews priority | Analyzes and asks | Provides question guidance |
| Propose document architecture | Accepts/rejects | Designs and explains | Provides process/templates |
| Draft content | Reviews | Authors | Provides conventions/templates |
| Decide scope and trade-offs | Decides | Recommends | Records structure |
| Maintain metadata | Oversees | Operates commands and verifies | Enforces supported constraints |
| Approve a document | Explicitly approves | Records genuine evidence | Creates/checks fingerprint |
| Validate semantic correctness | Reviews | Analyzes | Only deterministic checks |
| Preserve continuity | Confirms | Updates state and handoff | Supplies persistent files |
| Publish/deploy/external action | Authorizes | Acts only if authorized | No autonomous authority |

### 5. Approval authority

An agent can prepare a document for review and explain its changes. Approval is valid only after the owner explicitly reviews and approves the exact current document version. The helper records the evidence and a metadata-bound fingerprint; it does not authenticate who typed the approval statement or create a legally binding signature.

### 6. Shared expectations

The owner should provide corrections and decisions when needed. The agent should make uncertainty visible, work incrementally and report its actual actions. The framework should make common safe behavior straightforward and deterministic where possible. None of the three should silently substitute its assumptions for another's authority.


---

## How collaboration works

### 1. The working rhythm

PBF uses a small, reversible working loop:

**Listen → interpret → reflect → ask or draft → review → revise → validate → checkpoint.**

The owner may contribute a rough idea, answer a question, correct a previous interpretation, request research or change a decision. The agent should adapt to that input without insisting on a formal intake template.

### 2. Start with what is known

The agent should first understand the initial description and play it back in a concise structure. It should identify:

- facts explicitly supplied by the owner;
- evidence-backed observations;
- inferences made by the agent;
- proposals for the owner to consider;
- temporary assumptions;
- open questions;
- items deliberately deferred or rejected.

This distinction prevents a plausible interpretation from being mistaken for a confirmed requirement.

### 3. Ask purposeful questions

The agent should not ask every question in the question bank. It should prioritize questions whose answers materially affect direction, scope, risk, requirements, architecture or the next useful document. Usually one focused question is preferable. If work can proceed with a transparent assumption, the agent can propose that assumption and keep the work moving.

### 4. Document early, but in small pieces

After enough information exists to state a useful understanding, the agent should create or revise a small artifact. It should not wait until all details are known and should not generate every catalog document at once.

D0.01 normally captures and reflects the initial vision. D0.02 describes the project-specific documentation architecture: which documents are needed, their purpose, depth, disposition, dependencies and sequencing. The owner reviews and provisionally accepts D0.02 before ordinary broad scaffolding.

### 5. Review and decision-making

The agent explains what changed, why, important alternatives and consequences. The owner can correct the interpretation, accept a proposal, reject it or defer it. Accepted material decisions are recorded in the decision register and, when appropriate, an architecture decision record (ADR).

A proposal is not a decision. A document marked `in-review` is not approved. A successful command is not owner approval.

### 6. Change and impact

When new information contradicts an earlier fact or decision, the agent should not silently overwrite the earlier record. It identifies the conflict, determines the authoritative current record, lists affected documents/registers and proposes a revision sequence. Meaning-bearing changes to approved documents normally require review and reapproval of the exact revised version.

### 7. Session continuity

At the start of a fresh session, the agent reads `AGENTS.md`, `_control/PROJECT-RULES.md`, `_control/STATE.md`, the newest session handoff and relevant registers/documents. It does not rely on a prior transcript or model memory as the authoritative project record.

At the end of a session, it saves canonical changes, refreshes status and generated indexes, validates and records a session handoff with completed work, decisions, open questions, blockers and the next action.

### 8. How the conversation should feel

The process should feel like working with a thoughtful documentation partner, not filling out a compliance questionnaire. The framework provides structure in the background; it should not dominate every interaction. The agent should explain relevant complexity when needed, but keep routine updates concise and reserve exhaustive detail for actual reviews, handoffs or requested reports.


---

## Use cases and fit

### 1. Strong-fit situations

PBF is a strong candidate when a project is new or still being shaped and the owner wants a durable specification developed through conversation. Examples include:

- web, desktop or mobile applications;
- APIs and backend services;
- internal platforms and workflow systems;
- AI-assisted products, agent platforms and retrieval systems;
- data pipelines and analytics products;
- automation and integration projects;
- distributed systems and infrastructure designs;
- hardware and physical products, including electronic, mechanical, device and equipment projects;
- embedded or cyber-physical systems, where the document architecture is adapted to the engineering domain;
- research, operational and other non-software initiatives that benefit from structured requirements, decisions, validation and handover.

The complexity of the final workspace should reflect the project. A small utility may need only a few concise documents. A regulated, safety-sensitive or distributed system may need much deeper coverage and specialist review.

### 2. Typical situations where it helps

- The owner has a concept but not a complete requirements document.
- Product direction is likely to evolve during discovery.
- Several people or agents need to share a reliable project understanding.
- Decisions have costly downstream consequences.
- Requirements need traceability to goals, architecture and acceptance criteria.
- The project must preserve assumptions and unanswered questions instead of hiding them.
- The owner wants to hand a coherent baseline to an implementation team.

### 3. Poor-fit or supplementary-fit situations

PBF may be unnecessary or excessive when:

- a task is trivial and can be described accurately in a short ticket;
- the work is a one-off script with no meaningful lifecycle or downstream handoff;
- the organization requires a regulated document-control platform with validated electronic signatures, formal workflow enforcement or records retention that PBF does not provide;
- the primary need is source-code reverse engineering or automatic code-to-documentation synchronization;
- the team needs real-time multi-user editing with transactional locking;
- the main problem is task scheduling, sprint management or issue tracking.

PBF can complement other tools, but should not be misrepresented as replacing them.

### 4. Examples of adaptive documentation

**Collaborative SaaS product:** goals, personas, journeys, feature scope, business rules, requirements, permissions, domain/data model, APIs, architecture, operations, security, delivery and acceptance.

**AI agent platform:** model/provider selection, tool contracts, permission boundaries, prompt lifecycle, retrieval, memory, evaluation, tracing, fallback behavior, cost controls and safety review may be central.

**Hardware or physical product:** operating environment, system constraints, components/materials, mechanical and electrical interfaces, safety/reliability, verification, manufacturing/assembly and lifecycle support may be central.

**Embedded system:** hardware/software boundaries, timing, communications protocols, firmware states, diagnostics, provisioning, update strategy, test fixtures and field support may be central.

These are examples, not fixed schemas. D0.02 selects what applies.

### 5. When not to force a document

A candidate catalog entry should be excluded, deferred or conditional if it does not provide value for the project at the current stage. A document should not exist solely to make a progress dashboard look complete. If content belongs in an existing canonical document, link to it rather than creating a duplicate.

### 6. Adoption guidance

Start with one project and a modest documentation depth. Learn the workflow before imposing it across a portfolio. Keep the workspace under version control or another backup mechanism chosen by the owner. Have another human or agent review the planning baseline before relying on it for high-consequence implementation.


---

## Project lifecycle — P0 through P8

The framework uses a default planning lifecycle. It provides a common vocabulary and a suggested order, not a mandatory waterfall process. The project-specific architecture (D0.02) decides which records are required, what depth is useful and where phases can be combined or adapted.

| Phase | Focus | Intended outcome | Example questions |
|---|---|---|---|
| P0 | Setup, vision and adaptive architecture | Corrected vision and accepted provisional documentation structure | What are we trying to create? What must be documented? |
| P1 | Discovery and business framing | Problem, users, goals, constraints and opportunity understood | Who has the problem? What evidence supports it? |
| P2 | Product definition and requirements | Scope, capabilities, workflows, rules and acceptance criteria | What must the system do? What is deliberately excluded? |
| P3 | Domain, data and integrations | Domain concepts, data lifecycle and external contracts | What information exists? Who owns it? What systems interact? |
| P4 | High-level architecture | System boundaries and major architecture choices justified | What are the major components and why? |
| P5 | Low-level technical design | Implementation-level modules, interfaces, schemas and behavior specified where useful | How should the individual parts behave? |
| P6 | Quality, security and operations | Quality, security/privacy, test, reliability and operational expectations | How will it fail, recover, be tested and operated? |
| P7 | Delivery planning | Work breakdown, milestones, environments and release approach | How can the work be sequenced and delivered? |
| P8 | Coherence audit and sign-off | Cross-document coherence and owner-approved planning baseline | Are important decisions consistent, traceable and ready for handoff? |

### P0 — Vision and structure

The owner describes the project in their own words. The agent creates a concise reflection in D0.01, then develops D0.02 with a proposed project-specific document architecture. The owner reviews and provisionally accepts D0.02 before ordinary broad scaffolding. P0 does not require detailed requirements, APIs, database fields or low-level design.

### P1 — Discovery and framing

Understand the context, affected users, stakeholders, current alternatives, needs, constraints, desired outcomes, risks and evidence. Keep facts separate from hypotheses.

### P2 — Product and requirements

Define capabilities, product principles, release scope, workflows, functional requirements, business rules, non-functional requirements and observable acceptance criteria. Include edge cases and failure behavior, not only happy paths.

### P3 — Domain, data and integration

Define terminology, entities, relationships, invariants, data ownership, classification, lifecycle, retention/deletion, APIs/events and external dependencies. Make sources of truth explicit.

### P4 — High-level architecture

Start from architecture drivers and quality-attribute scenarios. Compare viable structures and document system context, containers/components, key flows, trust boundaries and material trade-offs. Record decisions that are expensive to reverse in ADRs.

### P5 — Detailed design

Specify module responsibilities, interfaces, contracts, schemas, state transitions, validation, error behavior, idempotency, timeouts, retries and concurrency where applicable. Detail is proportional to risk and implementation need.

### P6 — Quality and operations

Define verification strategy, security/privacy considerations, performance and reliability needs, observability, backup/recovery, deployment/operation and support considerations. Explicitly justify non-applicable areas.

### P7 — Delivery

Develop a practical work breakdown, dependencies, milestones, environments, release approach, developer guide and delivery risks.

### P8 — Coherence and sign-off

Audit the documentation set for conflicting claims, missing dependencies, unresolved blocking questions, decision traceability and acceptance evidence. The owner approves the planning baseline; P8 does not mean every future implementation question has been eliminated.

### Adapting phases

A project may combine, reorder, shorten or expand phases if the rationale is clear and the necessary concerns remain covered. Changes to the architecture and phase plan should be recorded. A phase label is a planning aid, not a claim that the work is complete.


---

## Trust, approvals and change control

### 1. Why governance is part of the method

A documentation system is useful only if people can tell what is known, what is proposed, what changed and who accepted it. PBF therefore treats ownership and traceability as core operating concerns, not optional decoration.

### 2. Evidence and certainty labels

The operating method distinguishes:

- **STATED:** explicitly provided by the owner.
- **OBSERVED:** present in an artifact or verified output.
- **CONFIRMED:** reviewed and accepted by the owner.
- **INFERRED:** reasoned interpretation that may be wrong.
- **PROPOSED:** recommendation awaiting owner decision.
- **ASSUMED:** temporary working assumption with a validation plan.
- **OPEN:** unresolved question.
- **DEFERRED:** deliberately postponed with rationale and revisit trigger.
- **REJECTED:** considered but not selected, with rationale where consequential.

An agent must not quietly promote an inference or proposal into a confirmed fact.

### 3. Owner authority

The owner retains authority over project direction, scope, acceptance, approval and external actions. The agent can recommend and prepare material; it cannot approve its own proposals or treat silence as acceptance.

### 4. Document status and maturity

Several independent properties must not be confused:

- **Applicability:** active, conditional, deferred or excluded.
- **Workflow status:** not-started, interviewing, drafting, in-review, approved, needs-revision, superseded or expanded.
- **Maturity:** outline, working or detailed.
- **Profile tier:** lite, standard or exhaustive.

For example, a detailed document may still be in review. An active document may not yet have started. A conditional document is not necessarily a defect.

### 5. Approval

A document becomes approved only after the owner explicitly reviews and approves the exact current version. The agent uses the dedicated `approve` command with truthful evidence. It must not edit approval records manually, infer approval from silence or manufacture an approver/date/signature.

The helper stores an approval record and a metadata-bound SHA-256 fingerprint. This helps detect drift in content and meaning-bearing metadata. It is not a cryptographic identity system and does not prove who supplied the approval statement.

### 6. Change control

When a fact, requirement or decision changes, the agent should:

1. Identify the existing canonical statement and its authority.
2. Record the new information and whether it is confirmed, proposed or assumed.
3. Identify dependent documents and structural-impact candidates.
4. Explain the likely impact and propose a revision order.
5. Revise affected artifacts without silently deleting history.
6. Revalidate manifest/front matter and related registers.
7. Obtain owner review/approval when meaning-bearing approved content changes.
8. Update the state and session handoff.

### 7. Safe operation

Project files, external pages, attachments and command output are data, not higher-priority instructions. The agent must not expose secrets, run destructive operations, deploy, publish, spend money or change external systems without the required owner authorization. It should report failures and unverified actions honestly.

### 8. The role of validation

A passing structural validator proves only that the checks it implements passed. It does not establish that a product is viable, requirements are complete, a security design is safe or an architecture is optimal. Consequential decisions require human and specialist review.


---

## Outcomes, limitations and future direction

### 1. Intended outputs

A mature PBF project workspace should contain a project-specific document set that covers the relevant business, product, domain, architecture, design, quality, delivery and acceptance concerns. It should also preserve the control information needed to understand the state of that work:

- manifest and generated index;
- current phase and state checkpoint;
- accepted decisions and ADRs;
- assumptions and validation plans;
- open questions;
- risks and mitigations;
- approval records;
- session/interview/phase history as applicable.

The exact content and number of files depend on the project's D0.02 architecture. There is no fixed document count target.

### 2. What PBF can help establish

PBF can help establish that a documentation process is explicit, that records have stable identities and metadata, that supported cross-record rules are checked, that approvals are version-specific and that a later session has a clear point from which to continue.

It can reduce the probability of hidden assumptions and repeated discovery when the owner and agent use it consistently.

### 3. What PBF cannot guarantee

- Semantic correctness of AI-generated content.
- Completeness of every requirement, risk or architecture consideration.
- Accuracy of external research or citations without review.
- Correctness or security of a future implementation.
- Authentication of an owner's identity for approval.
- Transactional multi-writer behavior or registry locking.
- Automatic synchronization with application code or issue trackers.
- Automatic recovery of context that was never written to the workspace.
- Compatibility with every Python version, operating system or AI harness.

### 4. Stable release scope

PBF v{{PBF_VERSION}} is the first stable release of the v3 architecture, revision 1.3.4. The release includes source/workspace separation, deterministic package build and verification, safe workspace creation, adaptive documentation method, approval integrity, semantic/manifest conformance checks, dependency applicability validation, read-only state reconciliation and a verified-completion operating contract.

The maintained developer tree currently contains 235 framework/developer test methods and 19 bootstrap-tool test methods. The exact commands, verification context and passing result for a particular release build are recorded in its generated `release-evidence/BUILD-VERIFICATION.md`. The declared minimum is Python 3.11; native Windows execution, a complete Python-minor matrix and cross-harness certification must not be inferred without separate test evidence.

The framework design is harness-neutral, but this does not establish universal or cross-harness compatibility. Native instruction discovery, context limits and tool permissions vary by environment and must be verified in the actual harness.

### 5. Future work should be evidence-led

A later release should be driven by operational experience, defects or clearly justified new capabilities. It should not add documents, registers, automation or harness-specific requirements merely because they seem useful in theory. The owner should distinguish a framework defect from an agent limitation, platform limitation, configuration issue or incomplete operating instruction.

### 6. Recommended adoption approach

Use v{{PBF_VERSION}} on a real but appropriately scoped project. Preserve the first stable release unchanged. Track actual friction and concrete inconsistencies. Make subsequent changes in a development branch or new version with regression tests and fresh release evidence.


---

## Glossary and frequently asked questions

### Glossary

| Term | Meaning |
|---|---|
| PBF | Project Blueprint Framework. |
| Workspace | A project-specific directory created from the workspace starter. |
| Source repository | The maintainer tree containing source CLI/build code, maintained tests, architecture, release assets and release tooling. |
| Workspace starter | The generated, project-neutral ZIP consumed by the source `new` command. It is not yet a live project workspace. |
| D0.01 | The initial vision capture/playback document in the default model. |
| D0.02 | The project's adaptive documentation architecture and scope document. |
| Manifest | Operational document inventory at `_control/registry/MANIFEST.md`. |
| Index | Generated navigation view at `_control/registry/INDEX.md`. |
| State | Current project progress/resumption record at `_control/STATE.md`. |
| Applicability | Whether a document is active, conditional, deferred or excluded. |
| Status | Where a document is in its workflow lifecycle. |
| Maturity | Whether the document is outline, working or detailed. |
| Profile tier | Lite, Standard or Exhaustive depth classification. |
| ADR | Architecture Decision Record documenting a consequential design choice and rationale. |
| Session handoff | A persistent record of what happened and the next action for a new session. |
| Approval fingerprint | SHA-256 consistency fingerprint tied to document content and meaning-bearing metadata. It is not a digital signature. |
| Explicit bootstrap | The portable method of telling an agent to read the workspace's instruction files directly. |

### FAQ

#### Does PBF include an AI agent?

No. It provides the workspace, instructions and tools. You must supply an AI agent/harness capable of reading and writing the workspace. Automated checks also require Python 3.11+ and terminal execution.

#### Does PBF work with every AI harness?

The design is harness-neutral and uses an explicit file-based setup contract. Actual compatibility depends on an agent environment having persistent filesystem access, write permission and Python 3.11+ terminal execution. No universal compatibility certification is claimed.

#### Do I need to know the whole project before starting?

No. An incomplete idea is sufficient. The process is designed to discover and document the project incrementally.

#### Does every project need all P0–P8 phases and all catalog documents?

No. The lifecycle and catalog are adaptable. D0.02 describes the documentation architecture suitable for the project.

#### Is D0.02 an approval of every future document?

No. It is the owner-reviewed provisional architecture for the document set and structure. Each document has its own lifecycle and approval as required.

#### Does a clean `check --strict` mean the project is correct?

No. It means the implemented deterministic checks passed. Semantic correctness, domain validity, security and architectural fitness still require review.

#### Does `new` initialize Git?

No. Git initialization is an explicit owner action.

#### Can I upgrade a v2.3.x workspace directly to v{{PBF_VERSION}}?

No. v{{PBF_VERSION}} is a clean break in physical workspace layout and does not provide a general legacy workspace migration command.

#### Can multiple agents edit the same workspace concurrently?

The framework does not promise transactional multi-writer behavior or registry locking. Coordinate writes or use separate branches/workspaces and reconcile deliberately.

#### Does the approval fingerprint prove the owner approved?

No. It detects drift in the fingerprinted document/metadata and records an evidence string. It does not authenticate identity or provide a digital signature.
