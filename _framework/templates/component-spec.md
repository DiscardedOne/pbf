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

> [[FILL: Replace this prompt with the component purpose, boundaries and implementation context.]]

# {{TITLE}}

## Component identity

- **Component ID (`CMP-`):**
- **Container / runtime:**
- **Owner:**
- **Lifecycle / status:**
- **Requirement drivers (FR-/NFR-):**
- **Verification (TC-):**

## Responsibility and boundaries
What it owns, what it does not own, and why the boundary exists.

## Public contracts
Inputs, outputs, schemas, validation, authN/authZ, error taxonomy, versioning, timeouts, idempotency and concurrency.

## Internal design
Modules, algorithms, state, persistence, dependencies, invariants and patterns.

## Data ownership and lifecycle
Source of truth, transactions, consistency, retention/deletion, migrations and audit behavior.

## Runtime and failure behavior
Startup/shutdown, concurrency, retries, backoff, partial failure, recovery, compensation and degradation.

## Observability and operations
Logs, metrics, traces, alerts, health checks, configuration and runbooks.

## Security and privacy
Trust boundaries, sensitive data, authorization, abuse cases and mitigations.

## Diagrams
Use a class/component/state/sequence diagram where it clarifies interactions; include caption and reading guide.

## Verification
Unit, integration, contract, end-to-end, resilience, security and performance checks mapped to FR/NFR IDs and the stable `TC-` IDs listed in Component Identity. `FLD001` checks only that labelled fields are populated; it does not validate identifier existence or semantic correctness.

## Dependencies and trade-offs
## Open questions / assumptions / risks
## Catalog checklist

{{CHECKLIST}}

## Change history

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | {{DATE}} | Initial scaffold | Phase work has not begun |
