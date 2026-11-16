# PBF v{{PBF_VERSION}} — Quality Assurance and Independent Review Policy

This document describes how to interpret PBF quality claims, how validation is layered and what an independent assessment should examine. It complements the implementation-specific checks in the technical reference and the release-specific evidence in `PBF-Release-Notes-and-Verification.md`.

## 1. Quality objectives

PBF quality is not measured by the number of documents generated. The objectives are:

- project documentation is proportionate to the project's needs;
- facts, assumptions, proposals, open questions, decisions and approvals remain distinguishable;
- canonical ownership and document relationships are explicit;
- owner approval is required for consequential decisions;
- the workspace remains usable across sessions through persistent files;
- deterministic tooling reports the specific conditions it understands;
- agents report actual completion and verification without overstating results;
- package creation and release claims are reproducible within the stated environment.

## 2. Validation layers

PBF validation has several distinct layers:

1. **Package integrity:** manifests and SHA-256 checksums detect missing or changed package files relative to the supplied checksum inventory.
2. **Archive safety:** path and member validation rejects unsafe paths, links, duplicate/case-colliding names and excessive archive sizes.
3. **Source verification:** checks source structure and static invariants; `verify --tests` additionally runs active source tests.
4. **Workspace validation:** `check --strict` checks supported structure, links, metadata, manifest/catalog/dependency/approval constraints and lint conditions.
5. **Index freshness:** `index --check` confirms generated navigation/index data is current.
6. **State reconciliation:** `audit-state --strict` performs a read-only comparison of explicit state, session, approval and index relationships.
7. **Semantic review:** a human or capable agent evaluates meaning, completeness, correctness, suitability, risk and domain assumptions. This cannot be replaced by a green deterministic check.
8. **Independent assessment:** a reviewer examines the actual released package, source, workspace, bootstrap process, evidence, claims and documentation from a skeptical perspective.

No layer should be represented as proving a stronger property than it actually checks.

## 3. Agent-assisted setup acceptance criteria

A release candidate's agent-assisted setup must be tested against these criteria before claiming successful onboarding:

- The agent identifies the single outer release and locates the nested agent package without asking the user to extract it manually.
- It verifies the outer listed nested-package hash and the inner package manifest/checksum inventory.
- It checks persistent filesystem access, write permission, Python 3.11+ and terminal capability before modifying the workspace destination.
- It proposes a destination and confirms the exact project name/path with the owner.
- It never chooses, overwrites, merges or deletes an existing destination.
- The helper verifies the package and curated bootstrap runtime, invokes the existing `bp.py new` command and verifies the generated workspace.
- It preserves a created destination if a later validation fails and reports the actual state.
- It removes only temporary files/directories it created.
- It does not install software, make network calls, initialize Git or start P0 without the separate owner confirmation.
- It gives a truthful completion report containing exact path and checks.
- It offers manual CLI setup as an alternative without presenting it as mandatory.

Unit tests of the helper are necessary but insufficient. At least one end-to-end agent/harness evaluation is required before claiming agent-assisted onboarding works in that environment. Cross-harness compatibility must not be claimed without additional evaluation.

## 4. Security and approval principles

- The agent's operating instructions do not create an OS-level sandbox. The host/harness and filesystem permissions define the actual security boundary.
- A checksum file is not a publisher signature. It verifies file consistency relative to the checksum list supplied alongside it.
- The bootstrap helper's repeated approved-destination argument is a mismatch guard, not independent evidence of user consent.
- The explicit owner confirmation in the agent conversation and any host permission prompt remain the actual approval boundary.
- Existing destinations must never be overwritten or merged by the bootstrap process.
- Temporary cleanup is limited to artifacts the agent/helper created during the current setup.
- No software installation, network operation, Git initialization or external publication is implicit in setup.
- Approval fingerprints in PBF are integrity/consistency mechanisms, not identity signatures.

## 5. Regression and release verification policy

For source/runtime changes, use the maintainer procedure: source static verification, full active test suite, default build, clean extraction of the exact output, workspace creation, `check --strict`, `index --check`, `audit-state --strict`, archive integrity checks and fresh hashes.

For bootstrap changes, run the focused helper tests and an end-to-end setup with the exact source/workspace archives. Test negative paths including checksum mismatch, unsafe ZIP entry, malformed/missing manifest, path mismatch, existing destination, unavailable parent, unsupported Python and a post-creation validation failure. Confirm that no pre-existing destination is altered and that temporary cleanup is scoped correctly.

For documentation-only changes, verify that filenames, links, commands, package layout, capability prerequisites, release claims and limitations are accurate. Do not claim source tests were rerun when only documentation was changed.

## 6. Independent assessment considerations

The reviewer should independently inspect and, where practical, reproduce:

- product definition, intended user and methodology fit;
- accepted architecture revision 1.3.4 and source/workspace/live-workspace separation;
- source implementation and maintained source and bootstrap test suites;
- exact source/workspace archive identity and creation behavior;
- agent package structure, manifest/checksums and extraction safety;
- bootstrap helper safety, failure handling, cleanup and exact-path approval guard;
- real agent onboarding behavior, capability detection and conversational destination confirmation;
- required separate confirmation before P0;
- manual CLI method remains complete and usable;
- documentation completeness, terminology and consistency;
- all compatibility, license, security and release non-claims.

Review must use disposable copies. The reviewer must not modify the supplied artifacts, publish a repository, make external changes or access private accounts. The PBF distribution is licensed under Apache License 2.0 (`Apache-2.0`); reviewers must retain the included `LICENSE` when redistributing copies.

## 7. Finding classification

Use severity proportionately:

- **Critical:** exploitable or destructive defect that makes adoption unsafe or invalidates fundamental release integrity.
- **High:** material defect in a core workflow, data integrity, approval boundary or central release claim.
- **Medium:** meaningful reliability/usability/documentation gap with a feasible workaround.
- **Low:** limited defect, minor inconsistency or improvement that does not materially prevent use.
- **Observation:** non-defect context, trade-off or optional enhancement.

Each finding should include evidence, reproduction steps, impact, affected artifact/version, severity rationale and a recommended disposition. Distinguish a reproduced defect from an unverified concern or design preference.

## 8. Release acceptance evidence

The release evidence should record:

1. Executive assessment and release recommendation.
2. Product/methodology assessment.
3. Architecture and implementation assessment.
4. Bootstrap and onboarding assessment, including actual harness/environment.
5. Independent verification table with commands, exit codes and results.
6. Documentation and compatibility assessment.
7. Findings register with precise evidence references.
8. Tests not run and reasons.
9. Security/safety concerns and limitations.
10. Prioritized next steps.

No finding should be based solely on an assumption about intended behavior where the supplied instructions or code can be inspected. Equally, the reviewer should not treat supplied claims as proof.
