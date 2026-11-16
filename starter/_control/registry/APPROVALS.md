# APPROVALS.md — Owner approval records

Written only by `python bp.py approve DOC_ID --evidence "..."`. One row per approval; the latest row for a document is authoritative. `check`, the adaptive-architecture gate, scaffolding beyond bootstrap and approval of downstream documents verify both the version and the approval fingerprint.

The column is historically named **Content hash**, but it stores a full SHA-256 approval fingerprint of the normalized Markdown body and meaning-bearing metadata from both manifest and front matter: document ID, title, phase, summary, content dependencies, applicability and rationale, profile tier, and canonical manifest path. This prevents a title/summary/scope/path/dependency edit from silently retaining approval. CRLF/LF line endings and trailing whitespace are normalized. `maturity` and `last_updated` are lifecycle-only metadata and do not invalidate approval; status/version are validated separately. Missing/legacy short hashes are rejected and require re-review/re-approval.

**Evidence** records where the owner's approval can be verified: their words (for example, “approved — lock it”), a session-log reference, or a review-round log. The tool cannot authenticate the owner or independently know whether the evidence is genuine. Never record approval the owner did not give.

| Doc ID | Version | Date | Approved by | Evidence | Content hash |
|---|---|---|---|---|---|
