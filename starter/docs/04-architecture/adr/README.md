# Architecture Decision Records

Store accepted or proposed architecture decision records (ADRs) in this directory using a stable ADR identifier in each filename.

Use the reusable format in [`_framework/templates/adr.md`](../../../_framework/templates/adr.md). Keep the decision status explicit (proposed, accepted, superseded or rejected), record the context and alternatives, and explain consequences. An ADR is not accepted merely because an agent drafted it; record the owner's decision in [`_control/registry/DECISIONS.md`](../../../_control/registry/DECISIONS.md) and follow the approval procedure for governed documents.

Do not duplicate the full architecture. Link to the relevant canonical documents under `docs/` and keep each decision focused on one material choice. When an accepted decision is superseded, preserve the historical record and link to its replacement.
