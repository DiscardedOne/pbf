# PBF v{{PBF_VERSION}} — Quick Start

**Recommended setup: let a capable agent prepare the workspace.** You do not need to manually extract the nested package or operate the CLI.

## 1. Download and verify the complete release ZIP

Obtain `PBF-v{{PBF_VERSION}}-Agent-First-Release.zip` from the [official PBF GitHub Releases page](https://github.com/DiscardedOne/pbf/releases). The [source repository](https://github.com/DiscardedOne/pbf) contains the maintained developer source. Before attaching the ZIP to an agent, calculate the downloaded file's SHA-256 and compare it with the digest published in that release's description.

PowerShell:

```powershell
Get-FileHash .\PBF-v{{PBF_VERSION}}-Agent-First-Release.zip -Algorithm SHA256
```

Linux/macOS:

```bash
sha256sum PBF-v{{PBF_VERSION}}-Agent-First-Release.zip
```

Do not proceed if the digest differs. This check relies on trusting the project GitHub account/repository as the release source; it detects a mismatched download but is not a detached digital signature.

After verifying the digest, attach the complete ZIP to an agentic AI environment that can read and write files in a persistent location and execute Python 3.11 or newer in a terminal.

Send this instruction:

> Prepare a PBF v{{PBF_VERSION}} workspace using the recommended agent-assisted setup. Inspect and verify the complete release package, check your actual filesystem, persistence and Python capabilities, and propose a destination. Confirm the project name and exact absolute destination with me before creating anything. After setup, verify the workspace, record minimal setup provenance in the existing initial project-control record, report actual results and ask whether I am ready to begin P0 discovery. Do not begin P0 until I confirm.

The full operating contract and startup prompt are included in the nested agent package.

## 2. Confirm the destination

The agent must establish whether its working location is persistent and accessible after the session. It should propose an exact absolute destination and project name, check that the destination does not already exist, explain the planned operations and wait for your approval.

Do not approve an ephemeral or session-only location when you expect the workspace to persist on your machine. A path visible inside a container or cloud agent may not be the same as a path on your host computer.

## 3. Let the agent complete and verify setup

After approval, the agent verifies the outer release inventory, safely extracts the nested agent package into a temporary directory, verifies its manifest/checksums, and runs the bootstrap helper. The helper extracts only the curated bootstrap runtime temporarily, runs `bp.py verify --scope bootstrap`, uses the existing `bp.py new` command to create the workspace and runs:

- `check --strict`
- `index --check`
- `audit-state --strict`

After the successful checks, the agent reads the generated instructions and control records, writes concise setup provenance into the existing `_control/STATE.md` record, rechecks the state audit, then removes only temporary files it created. It does not initialize Git, install software or make network calls.

## 4. Confirm before starting P0

The agent reports the project name, exact workspace path, framework version, checks, provenance and cleanup result. It should then ask:

**“The PBF workspace is set up and verified. Would you like to begin P0 discovery now?”**

P0 begins only after you explicitly confirm. The workspace is intentionally sparse; P0 captures your vision and proposes an adaptive documentation architecture rather than generating every possible document immediately.

## Manual alternative

Agent-assisted setup is recommended, not mandatory. The complete manual CLI workflow is in [`docs/PBF-User-Guide.md`](docs/PBF-User-Guide.md), under “Alternative: manual CLI setup”.
