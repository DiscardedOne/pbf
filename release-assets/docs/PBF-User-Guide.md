# Project Blueprint Framework v{{PBF_VERSION}} — User Guide

This guide covers setup and day-to-day operation. **Agent-assisted setup is the recommended route**; manual CLI setup remains available for users who prefer direct control or whose agent environment lacks the required filesystem/terminal capabilities.

## 1. What you need

For the recommended route, download `PBF-v{{PBF_VERSION}}-Agent-First-Release.zip` from the [official PBF GitHub Releases page](https://github.com/DiscardedOne/pbf/releases) and use an agentic AI environment that can inspect the supplied ZIP, create temporary files, access a persistent user-visible destination, and execute Python 3.11 or newer. The [source repository](https://github.com/DiscardedOne/pbf) contains the maintained developer source. PBF does not include an AI model, agent runtime, credentials, provider connection or hosted service.

For the manual route, you need Python 3.11 or newer in the environment where workspace commands will run, a persistent destination, and the ability to extract ZIP archives and run the CLI.

## 2. Understand the release package

The outer release ZIP is the one download. It includes `README.md`, `QUICKSTART.md`, release information and checksums, the consolidated documentation in `docs/`, concise release evidence, and `agent-package/PBF-Agent-Package-v{{PBF_VERSION}}.zip`.

The nested agent package contains the startup prompt and operating instructions, a curated bootstrap runtime archive, the workspace starter and the bootstrap helper. It does not contain the full maintainer source repository or developer test suite. You do not need to extract the nested package manually for the recommended route; the agent should do that in a temporary location.

The **bootstrap runtime** contains only the verified PBF CLI/source inputs required to create a workspace. The **workspace starter** is a project-neutral input package, not a usable live workspace. The existing CLI `new` command materializes it into a live project workspace.

## 3. Recommended: agent-assisted setup

1. Attach the **complete outer release ZIP** to an agentic AI assistant with filesystem and terminal capabilities.
2. Use the included `AGENT-STARTUP-PROMPT.md` from the inner agent package, or tell the agent: “Prepare a PBF v{{PBF_VERSION}} workspace using the recommended agent-assisted setup. Confirm the project name and exact destination with me before creating anything. After setup, record minimal setup provenance in the existing initial project-control record, report actual results and ask before starting P0.”
3. The agent should inspect and verify the package, check whether its filesystem and Python capabilities are sufficient, and identify a persistent destination.
4. Review the exact project name and absolute destination proposed by the agent. Approve them explicitly before creation.
5. The agent runs the bootstrap helper, which verifies the package, safely extracts the curated runtime temporarily, runs `bp.py verify --scope bootstrap`, creates the workspace using the existing PBF CLI, and runs strict validation, index validation and the read-only state audit.
6. After successful checks, the agent records the setup date, method, framework version and verification result in the existing `_control/STATE.md` setup-provenance field, re-runs the state audit, and reports the actual destination and checks. It confirms temporary runtime/package files were removed and Git was not initialized.
7. The agent then asks whether you are ready to begin P0 discovery. **P0 begins only after you confirm.**

The agent must stop and explain the limitation if it cannot access a persistent destination or execute Python 3.11+. PBF instructions cannot grant missing filesystem or terminal permissions. The setup helper does not install software or make network calls.

## 4. Download integrity

The outer `SHA256SUMS.txt` lists hashes for files inside the release ZIP. After extracting the outer ZIP, verify the listed files from the release root using a SHA-256 tool available on your system. The nested agent package has its own `SHA256SUMS.txt`, which the agent verifies after extraction. For a public download, also compare the SHA-256 of the complete outer ZIP with the digest published in the [official GitHub Release](https://github.com/DiscardedOne/pbf/releases) description. This relies on trust in the PBF GitHub account/repository and detects a mismatched download; it is not a detached digital signature or independent authentication if the account or release is compromised.

## 5. Alternative: manual CLI setup

Use this route when you prefer to run the commands yourself or the agent environment cannot perform the recommended setup.

### 5.1 Extract the package layers

1. Extract `PBF-v{{PBF_VERSION}}-Agent-First-Release.zip` into a release directory.
2. Extract `agent-package/PBF-Agent-Package-v{{PBF_VERSION}}.zip` into a separate temporary/package directory.
3. Inside it, locate the two files under `archives/`:
   - `project-blueprint-framework-{{PBF_VERSION}}-bootstrap-runtime.zip`
   - `project-blueprint-workspace-{{PBF_VERSION}}.zip`
4. Before extracting either embedded archive for use, verify the nested package's own checksum inventory and its manifest-declared archive digests. This manual verification is separate from the bootstrap helper; the helper is not required for manual CLI setup.
5. Extract the bootstrap runtime ZIP into a clean tools directory. Keep it separate from your project workspace. The runtime archive is a deliberately limited setup runtime, not the full developer repository.

#### Verify the nested agent package manually

Save the following standard-library-only script as `verify_nested_package.py` in a temporary location **outside** the extracted agent-package directory. Run it with Python 3.11+ and pass the extracted agent-package root as its argument. It verifies the complete nested checksum inventory, both manifest-declared archive hashes and the CRC integrity of both embedded ZIP files.

```python
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import sys
import zipfile

root = Path(sys.argv[1]).resolve(strict=True)
manifest_path = root / "PACKAGE-MANIFEST.json"
sums_path = root / "SHA256SUMS.txt"
if not manifest_path.is_file() or not sums_path.is_file():
    raise SystemExit("Package manifest or checksum inventory is missing.")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
checksums = {}
for line_number, line in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), 1):
    if not line:
        continue
    match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
    if not match:
        raise SystemExit(f"Malformed checksum line {line_number}.")
    digest, name = match.groups()
    relative = PurePosixPath(name)
    if relative.is_absolute() or "\\" in name or any(part in ("", ".", "..") for part in relative.parts):
        raise SystemExit(f"Unsafe checksum path: {name}")
    if name in checksums:
        raise SystemExit(f"Duplicate checksum path: {name}")
    target = root.joinpath(*relative.parts)
    if target.is_symlink() or not target.is_file() or root not in target.resolve().parents:
        raise SystemExit(f"Missing or unsafe package file: {name}")
    checksums[name] = digest

actual = set()
for item in root.rglob("*"):
    if item.is_symlink():
        raise SystemExit(f"Symlink is not permitted: {item.relative_to(root)}")
    if item.is_file() and item.name != "SHA256SUMS.txt":
        actual.add(item.relative_to(root).as_posix())
if actual != set(checksums):
    raise SystemExit(f"Checksum inventory mismatch: missing={sorted(actual-set(checksums))}; extra={sorted(set(checksums)-actual)}")
for name, expected in checksums.items():
    actual_hash = hashlib.sha256((root / Path(*PurePosixPath(name).parts)).read_bytes()).hexdigest()
    if actual_hash != expected:
        raise SystemExit(f"SHA-256 mismatch: {name}")

for path_key, hash_key in (("bootstrap_runtime_archive", "bootstrap_runtime_sha256"), ("workspace_archive", "workspace_archive_sha256")):
    name = manifest.get(path_key)
    if not isinstance(name, str) or name not in checksums or manifest.get(hash_key) != checksums[name]:
        raise SystemExit(f"Manifest digest does not match the checksum inventory: {path_key}")
    archive_path = root / Path(*PurePosixPath(name).parts)
    with zipfile.ZipFile(archive_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise SystemExit(f"ZIP CRC failure in {name}: {bad_member}")

print("Nested package checksums, manifest archive digests and both ZIP CRC checks passed.")
```

Windows PowerShell:

```powershell
py -3.11 -B .\verify_nested_package.py "C:\PBF\Tools\PBF-Agent-Package"
```

Linux/WSL:

```bash
python3.11 -B ./verify_nested_package.py "$HOME/tools/PBF-Agent-Package"
```

Continue only if the script reports success. Keep the verifier script outside the package root so it does not appear as an unlisted file. Remove the script after completing manual setup if you created it solely for this check.

Example layout:

```text
C:\PBF\Tools\PBF-{{PBF_VERSION}}-bootstrap-runtime\   # extracted bootstrap runtime
C:\PBF\Workspaces\                         # persistent workspace parent
C:\PBF\Tools\PBF-Agent-Package\archives\  # workspace starter ZIP
```

Linux/WSL example:

```text
$HOME/tools/PBF-{{PBF_VERSION}}-bootstrap-runtime/   # extracted bootstrap runtime
$HOME/workspaces/                         # persistent workspace parent
$HOME/tools/PBF-Agent-Package/archives/   # workspace starter ZIP
```

### 5.2 Verify the extracted bootstrap runtime

Open a terminal in the root of the extracted bootstrap runtime directory. The runtime's `bp.py` launcher selects source mode from that directory. Verify the runtime before creating the workspace.

Windows PowerShell:

```powershell
Set-Location "C:\PBF\Tools\PBF-{{PBF_VERSION}}-bootstrap-runtime"
py -3.11 -B .\bp.py verify --scope bootstrap
```

Linux/WSL:

```bash
cd "$HOME/tools/PBF-{{PBF_VERSION}}-bootstrap-runtime"
python3.11 -B bp.py verify --scope bootstrap
```

The command must report bootstrap source verification passed. If it fails, stop and do not create the workspace.

### 5.3 Create a live workspace

Run the following command from the extracted bootstrap runtime directory. Supply the workspace starter ZIP using its actual absolute path; it remains separate from the runtime directory.

Windows PowerShell:

```powershell
py -3.11 .\bp.py new `
  --name "My Project" `
  --destination "C:\PBF\Workspaces\My-Project-Blueprint" `
  --package "C:\PBF\Tools\PBF-Agent-Package\archives\project-blueprint-workspace-{{PBF_VERSION}}.zip"
```

Linux/WSL:

```bash
python3.11 -B bp.py new \
  --name "My Project" \
  --destination "$HOME/workspaces/My-Project-Blueprint" \
  --package "$HOME/tools/PBF-Agent-Package/archives/project-blueprint-workspace-{{PBF_VERSION}}.zip"
```

The destination must not already exist. Choose a new path; `new` refuses to overwrite or merge an existing directory. It consumes the already-built workspace package and does not build implicitly. The manual `bp.py new` CLI may create missing ancestor directories for the destination path. Before running it, confirm that creating those exact parent directories is intended and permitted. The recommended agent bootstrap helper has a stricter boundary: it requires the destination's immediate parent to exist and refuses to create missing ancestors.

### 5.4 Review and validate the workspace

The generated workspace has this basic structure:

```text
My-Project-Blueprint/
├── README.md
├── AGENTS.md
├── bp.py
├── docs/
├── _framework/
└── _control/
```

Review `README.md`, `AGENTS.md`, `_control/PROJECT-RULES.md`, `_control/STATE.md`, `_control/PHASES.md` and `_control/registry/INDEX.md`. From the workspace root, run:

Windows:

```powershell
py -3.11 .\bp.py check --strict
py -3.11 .\bp.py index --check
py -3.11 .\bp.py audit-state --strict
```

Linux/WSL:

```bash
python3.11 -B bp.py check --strict
python3.11 -B bp.py index --check
python3.11 -B bp.py audit-state --strict
```

The checker validates local Markdown links and heading anchors. Local link targets are subject to a 2,048-character parsing limit; valid external URI targets, including long HTTP(S) URLs and embedded `data:` images, are treated as external references and are not fetched. Malformed external URI syntax and unterminated HTML comments are reported as validation errors with source-file and line context. An unterminated comment is an error because it would otherwise mask the remainder of that document from link validation.

After those checks pass, update the existing `Workspace setup provenance` field in `_control/STATE.md`, for example: `YYYY-MM-DD; manual CLI; PBF {{PBF_VERSION}}; Python 3.11.x; verified`. Record the actual date and interpreter version, not the example values. Then rerun `audit-state --strict` and confirm it reports no errors. Do not create a separate setup session log.

A fresh workspace should pass structural validation, index freshness and read-only state reconciliation. It is not expected to pass a later project-phase readiness gate before project content has been developed. The `docs/` folder is intentionally sparse; absence of detailed project documents is not a setup failure.

After all checks and the provenance update succeed, remove only the extracted agent-package/runtime directories and temporary `verify_nested_package.py` script that you created for this installation. Do not delete the original downloaded release ZIP, any pre-existing files, or the newly created live workspace. If cleanup fails, keep the workspace and report the exact temporary path that remains.

`new` does not initialize Git, scaffold every catalog document, migrate a v2.3.x workspace or configure an AI model. Do not place project-specific decisions in the maintainer source tree.

## 6. Connect an agent and begin P0

Manual workspace creation does not automatically begin P0. Begin discovery only when you choose to do so. Make the live workspace available to the agent with persistent read/write access and provide its absolute path. The agent must explicitly read `AGENTS.md` and `_control/PROJECT-RULES.md`, then inspect `STATE.md`, the current handoff if present, and the generated index. Do not assume every harness automatically discovers these files.

Begin with a natural-language explanation of the project. PBF is for discovery and specification, not immediate application implementation. The agent should reflect its understanding, ask focused questions, develop D0.01 and propose a tailored D0.02. It should explain the proposed document set and wait for your explicit acceptance of D0.02 before broad scaffolding.

## 7. Session startup and continuity

At the start of each substantive session, the agent should:

1. Confirm the absolute workspace root.
2. Read `AGENTS.md`, `_control/PROJECT-RULES.md` and `_control/STATE.md`.
3. Inspect the latest session handoff, if one exists.
4. Read `_control/registry/INDEX.md` and only the actual documents relevant to the task.
5. Inspect relevant questions, assumptions, decisions and risks.
6. Consult the relevant `_framework/` references.
7. Run baseline checks when Python 3.11+ is available.

The workspace files are the durable project record. Chat history and agent memory are not substitutes for reading them.

## 8. Discovery and document authoring

- Let the owner describe the problem and desired outcome in natural language.
- Reflect understanding before asking detailed questions.
- Separate facts, observations, inferences, proposals, assumptions and open questions.
- Ask one high-value question at a time by default.
- Draft a useful slice as soon as there is enough information.
- Keep one canonical location for each fact, rule and decision.
- Use stable IDs and keep front matter and manifest aligned.
- State uncertainty instead of filling gaps with guesses.
- Scaffold only documents needed next; do not create empty documents to fill a catalog.
- Keep secrets out of the workspace.

## 9. Status, maturity and applicability

These are separate concepts. Typical commands are:

```bash
python3.11 -B bp.py set-status D1.03 drafting
python3.11 -B bp.py maturity D1.03 working
python3.11 -B bp.py applicability D1.05 active --reason "..."
python3.11 -B bp.py profile standard
```

Use workflow status to describe progress, maturity to describe content depth, applicability to describe whether a record belongs in the project and profile to establish the default depth policy.

## 10. Validation rhythm

After meaningful metadata or structural changes:

```bash
python3.11 -B bp.py check --strict
python3.11 -B bp.py index --check
python3.11 -B bp.py audit-state --strict
```

For readiness, use the relevant commands such as `check --readiness` or `check --gate 2`. Read the actual output. A clean deterministic check is not proof of semantic correctness.

## 11. Owner review and approvals

1. Develop the document to the maturity needed for its purpose.
2. Set the status to `in-review`.
3. Confirm relevant dependencies and upstream approvals.
4. Present the exact current version to the owner.
5. Obtain explicit owner approval of that exact version.
6. Run `approve` with truthful evidence.
7. Read back the approval row and run relevant checks.

Never infer approval or edit approval records manually. The approval fingerprint is a consistency mechanism, not a cryptographic identity signature.

## 12. Change control

When a fact, requirement or decision changes, locate its canonical source, inspect dependencies and structural impact, identify affected documents/registers/phases, propose the revision order, revise only the authorized scope, reconcile metadata and obtain re-approval of meaning-bearing material where required. Do not silently overwrite accepted decisions.

## 13. Verified completion reporting

For consequential multi-file work, use these states precisely:

| State | Meaning |
|---|---|
| Planned | Not invoked |
| Attempted | Invoked; effect unknown |
| Completed | Intended writes are present on read-back; validation may be pending |
| Verified | Postconditions read back and relevant checks pass |
| Partial | Some intended results are missing or inconsistent |
| Failed | No intended change persisted |
| Blocked | Not attempted because authorization, access, dependency or capability prevented it |

The agent must read back target files. A success message or tool exit code alone is not proof. Report exact paths, values, checks, exit codes and remaining work. Approval remains separate from technical completion. Routine edits do not need a separate report file or per-edit hash.

## 14. Session close and owner shortcuts

At a substantive session close, update status, run strict/index/state checks, create a session handoff and update `STATE.md` with actual work, decisions, approvals, open questions, blockers and next action. The canonical files must describe what exists, not what the agent intended.

| Owner phrase | Expected behavior |
|---|---|
| `status` | Refresh/report current state and next action |
| `next` | Continue the next action in STATE.md |
| `checkpoint` | Save, validate, refresh state/index and prepare handoff |
| `gate` | Run relevant phase gate and report evidence/gaps |
| `audit` | Run coherence review using quality guidance |
| `park: <idea>` | Record the idea appropriately and continue |
| `revisit <doc/topic>` | Start change-impact review |
| `replan` | Revisit D0.02 with owner approval for material changes |
| `explain <x>` | Explain a term, decision or rationale |
| `wrap up` | Close session and prepare a complete handoff |

## 15. Git, backups and persistence

PBF does not host, back up or synchronize workspaces. The owner should choose a durable storage location and a backup/version-control strategy. Git is optional and must be initialized by the owner when desired; it is not initialized by `new`. Avoid simultaneous independent writers in one checkout unless a separate concurrency strategy exists.

For GitHub publishing, use the guide in the consolidated Git and publishing section below. Review what will be public. PBF-provided framework components are distributed under Apache License 2.0 (`Apache-2.0`); retain the included `LICENSE` when redistributing those components. In a generated workspace, read `PBF-LICENSE-SCOPE.md`: the PBF license does not automatically apply to owner-authored project documents, records, data, application code or third-party material.

## 16. Troubleshooting and capability limitations

### Agent cannot write files or run Python

The recommended workflow requires actual filesystem write access and Python 3.11+ terminal execution. Attachment inspection alone is insufficient. Ask the harness to grant the required workspace/terminal capabilities, use a compatible agent environment, or choose the manual CLI route.

### Destination already exists

Do not overwrite or merge. Select a new destination, or handle the existing directory separately after reviewing its contents. The bootstrap helper intentionally refuses an existing destination.

### Destination path not visible to the agent

Use the path actually mounted into the agent environment. A Windows host path may not map to the same path inside WSL, Docker or a cloud container. Confirm persistence before proceeding.

### Python version is too old

PBF declares Python 3.11 or newer. The bootstrap does not install Python or dependencies. Use an already installed supported interpreter or the manual method in a suitable environment.

### Package checksum or archive validation fails

Stop. Do not bypass the verification. Re-download or obtain a clean release from the trusted source, then retry with a fresh temporary extraction.

### Workspace validation fails after creation

Preserve the created workspace for inspection. Report the exact failing check and path. Do not automatically delete or overwrite it, and do not claim setup is verified.

### State audit or index check reports drift later

Read the findings; these commands are read-only diagnostics. Reconcile the canonical source records and regenerate derived records only through documented workspace operations. Do not silently edit owner decisions or approvals.

### Workspace appears empty

A new workspace is deliberately project-neutral. It contains the reusable runtime and initial control records, not a full specification. Start with P0 discovery and an owner-reviewed D0.02 document architecture.

### Agent or chat session changes

Provide access to the same persistent workspace, ask the new agent to follow the workspace bootstrap instructions and record the harness change. Do not assume automatic instruction discovery or cross-harness certification.

## 17. Publishing a developer repository

The maintainer source is the developer repository, not the Agent-First Release ZIP and not the generated workspace starter. The developer repository contains the full maintained source, tests, architecture and release builder. The release ZIP is its generated product output.

Before publishing a Git repository:

- Review the complete source tree, release assets, ZIP members and intended Git history for secrets, personal information, client-confidential material and unnecessary working history.
- Keep the initial repository history intentional; review every staged file for credentials, private data, machine-specific paths and generated artifacts.
- Ensure there is no accidental `dist/` or other generated binary output committed.
- Confirm that the public repository contains the Apache-2.0 `LICENSE`, Code of Conduct, contribution guide and security policy before publication.
- Before the first commit, configure and verify the intended Git author name and email. On GitHub, use the account-provided no-reply address when personal email privacy is desired; author metadata remains in commit history.
- Create the repository from the reviewed clean source tree. Do not import an unsanitized development history if it contains material that should not be public.
- Run `python -B bp.py verify --tests` and `python -B tools/release/build_release.py` from a clean checkout before publishing a release artifact.
- Review repository visibility, release files, support expectations and maintenance responsibilities before publishing.

The release builder produces `PBF-v<VERSION>-Agent-First-Release.zip` as its single product artifact.
