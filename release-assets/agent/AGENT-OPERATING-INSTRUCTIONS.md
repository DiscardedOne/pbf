# PBF v{{PBF_VERSION}} — Agent-assisted setup contract

**Purpose:** Guide an agentic AI through safe, owner-approved creation of a Project Blueprint Framework workspace from the supplied agent package.

**Framework version:** `{{PBF_VERSION}}`  
**Workspace architecture:** `1.3.4`  
**Minimum runtime:** Python `3.11`  
**Setup route:** Recommended; manual CLI setup remains supported in the release's user guide.

---

## 1. Authority and non-goals

You are the conversational coordinator. The Python bootstrap helper performs only deterministic package verification, extraction, workspace creation and validation.

The human owner retains control over project identity, workspace destination, consequential project decisions and approvals. Do not treat silence, ambiguity or a tool's success response as owner approval.

This package is not an AI model, agent runtime, credential bundle, hosted service or sandbox. It cannot grant you filesystem or terminal permissions. Do not claim compatibility with a harness until its required capabilities are available and the actual setup succeeds.

## 2. Required capabilities and stop conditions

Before attempting setup, determine whether your current environment provides all of the following:

- Read access to the complete release ZIP and its nested agent package.
- Permission to create and remove temporary files that you create.
- Read/write access to the owner-confirmed destination's parent directory.
- A terminal or execution tool able to invoke Python `3.11` or newer.
- A persistent destination visible to the user after this agent session ends.

Use the actual paths exposed by your environment. Do not assume a Windows host path is accessible from a Linux/container agent, or that a container's working directory is persistent.

If any required capability is missing, stop before creating the workspace. Explain the specific limitation and what capability/permission is required. Do not pretend to have installed PBF, and do not default to asking the owner to operate a terminal manually. The owner may choose the documented manual route instead.

Do not install Python, packages, system tools or dependencies. The bootstrap uses the Python standard library and the included PBF CLI. Do not make network requests or initialize Git.

## 3. Input package and integrity checks

The user should provide the **complete outer release ZIP**:

`PBF-v{{PBF_VERSION}}-Agent-First-Release.zip`

Do not ask the user to manually extract the nested package. You should:

1. Inspect the outer archive without modifying it.
2. Locate `agent-package/PBF-Agent-Package-v{{PBF_VERSION}}.zip`.
3. Read `RELEASE-MANIFEST.json` and `SHA256SUMS.txt`. Verify the checksum inventory covers exactly every outer payload except the checksum file itself, has no duplicate paths, and every listed payload hash matches. Cross-check the manifest-declared nested ZIP path and SHA-256 against the actual nested ZIP and the checksum inventory. Complete outer verification is mandatory, not optional.
4. Extract the nested agent ZIP into a new temporary directory that you created. Never extract over an existing directory.
5. Read `PACKAGE-MANIFEST.json` and `SHA256SUMS.txt` in that extracted package.
6. Verify the package inventory and every listed file hash. Reject missing, extra, changed or symbolic-link files.
7. Cross-check the outer manifest's `nested_package_contents` against the inner `PACKAGE-MANIFEST.json`: the package-manifest path must be `PACKAGE-MANIFEST.json`, and the bootstrap-runtime and workspace-starter paths and SHA-256 values must exactly match the inner manifest. Reject missing, extra or inconsistent references.
8. Read this document and `AGENT-STARTUP-PROMPT.md` before proceeding.

If the outer checksum file or package integrity is missing, malformed or inconsistent, stop and report the exact problem. Embedded checksums detect accidental corruption and changes relative to the supplied checksum file; they are not a digital signature or independent proof of publisher identity.

### 3.1 Safe extraction of the nested package

Do not extract the entire outer release ZIP. Read its root manifest/checksum file and the nested agent ZIP directly through a ZIP reader. Verify the nested ZIP's SHA-256 before writing it to a temporary location. Before extracting the inner ZIP, reject unsafe paths, backslashes, Windows-reserved/invalid path components, symlink entries, encryption, duplicate/case/Unicode-normalization collisions and unreasonable uncompressed sizes. Extract only into a newly created temporary directory. The bootstrap helper will independently verify the exact extracted agent-package inventory and hashes before using the runtime or workspace archive.

The following Python standard-library example shows the required sequence. Replace `OUTER` with the actual path exposed by your harness; run it yourself in a temporary script/location, not in the user's project workspace. Keep the returned temporary directory until setup and read-back are complete.

```python
from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, stat, tempfile, unicodedata, zipfile

OUTER = Path("/path/to/PBF-v{{PBF_VERSION}}-Agent-First-Release.zip")
INNER = "agent-package/PBF-Agent-Package-v{{PBF_VERSION}}.zip"
MAX_MEMBERS, MAX_TOTAL, MAX_MEMBER, MAX_RATIO = 10_000, 100*1024*1024, 50*1024*1024, 500

def safe_name(name, is_dir=False):
    raw = name[:-1] if is_dir and name.endswith("/") else name
    if not raw or "\\" in raw or "\x00" in raw:
        raise ValueError(f"Unsafe ZIP path: {name!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe ZIP path: {name!r}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or (parts and re.match(r"^[A-Za-z]:", parts[0])):
        raise ValueError(f"Absolute/drive ZIP path: {name!r}")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}
    for part in pure.parts:
        if any(ord(c)<32 or c in '<>:"|?*' for c in part) or part.endswith(("."," ")) or part.split(".",1)[0].upper() in reserved:
            raise ValueError(f"Non-portable ZIP path: {name!r}")
    return Path(*pure.parts)

def validate_archive(zf):
    infos = zf.infolist()
    if not infos or len(infos) > MAX_MEMBERS:
        raise ValueError("Unexpected ZIP member count")
    seen, total = set(), 0
    component_spellings, node_types = {}, {}
    for info in infos:
        rel = safe_name(info.filename, info.is_dir())
        parts = rel.parts
        key = tuple(unicodedata.normalize("NFKC", part).casefold() for part in parts)
        if key in seen:
            raise ValueError(f"Duplicate/colliding ZIP member: {info.filename}")
        seen.add(key)
        for index, part in enumerate(parts):
            prefix_key = tuple(unicodedata.normalize("NFKC", item).casefold() for item in parts[:index + 1])
            spelling = tuple(parts[:index + 1])
            prior = component_spellings.get(prefix_key)
            if prior is not None and prior != spelling:
                raise ValueError(f"Parent-component case/Unicode collision: {prior!r} and {spelling!r}")
            component_spellings[prefix_key] = spelling
            if index < len(parts) - 1:
                if node_types.get(prefix_key) == "file":
                    raise ValueError(f"File/directory ancestor conflict: {'/'.join(parts[:index + 1])}")
                node_types[prefix_key] = "directory"
            else:
                expected_type = "directory" if info.is_dir() else "file"
                prior_type = node_types.get(prefix_key)
                if prior_type is not None and prior_type != expected_type:
                    raise ValueError(f"File/directory path conflict: {info.filename}")
                node_types[prefix_key] = expected_type
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode) or (info.flag_bits & 1):
            raise ValueError(f"Link/encrypted ZIP member: {info.filename}")
        if not info.is_dir():
            total += info.file_size
            if info.file_size > MAX_MEMBER or total > MAX_TOTAL:
                raise ValueError("ZIP uncompressed-size limit exceeded")
            if info.file_size and (not info.compress_size or info.file_size/info.compress_size > MAX_RATIO):
                raise ValueError("Suspicious ZIP compression ratio")
    return infos

with zipfile.ZipFile(OUTER) as outer:
    if outer.testzip() is not None:
        raise ValueError("Outer release ZIP CRC check failed")
    validate_archive(outer)
    release_manifest = json.loads(outer.read("RELEASE-MANIFEST.json"))
    sums = outer.read("SHA256SUMS.txt").decode("utf-8")
    parsed_rows = [re.fullmatch(r"([0-9a-f]{64})  (.+)", line) for line in sums.splitlines() if line.strip()]
    if not parsed_rows or any(row is None for row in parsed_rows):
        raise ValueError("Malformed outer checksum inventory")
    rows = [row.groups() for row in parsed_rows]
    checksum_map = {path: expected for expected, path in rows}
    if len(checksum_map) != len(rows):
        raise ValueError("Duplicate path in outer checksum inventory")
    outer_files = {info.filename for info in outer.infolist() if not info.is_dir() and info.filename != "SHA256SUMS.txt"}
    if set(checksum_map) != outer_files:
        raise ValueError("Outer checksum inventory does not cover exactly the release payload")
    for path, expected in checksum_map.items():
        digest = hashlib.sha256()
        with outer.open(path) as src:
            for chunk in iter(lambda: src.read(1024*1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError(f"Outer release checksum mismatch: {path}")
    if release_manifest["nested_agent_package"] != INNER:
        raise ValueError("Nested agent package path does not match release manifest")
    if checksum_map.get(INNER) != release_manifest["nested_agent_package_sha256"]:
        raise ValueError("Nested agent package manifest/checksum mismatch")
    temp_root = Path(tempfile.mkdtemp(prefix="pbf-agent-package-"))
    inner_zip = temp_root / "agent-package.zip"
    with outer.open(INNER) as src, inner_zip.open("xb") as dst:
        shutil.copyfileobj(src, dst)

agent_root = temp_root / "package"
agent_root.mkdir()
with zipfile.ZipFile(inner_zip) as inner:
    infos = validate_archive(inner)
    for info in infos:
        rel = safe_name(info.filename, info.is_dir())
        target = agent_root.joinpath(*rel.parts)
        if agent_root.resolve() not in (target.parent.resolve(), *target.parent.resolve().parents):
            raise ValueError(f"ZIP member escapes extraction root: {info.filename}")
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with inner.open(info) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
inner_manifest = json.loads((agent_root / "PACKAGE-MANIFEST.json").read_text(encoding="utf-8"))
expected_nested_contents = {
    "package_manifest": "PACKAGE-MANIFEST.json",
    "bootstrap_runtime": {
        "path": inner_manifest.get("bootstrap_runtime_archive"),
        "sha256": inner_manifest.get("bootstrap_runtime_sha256"),
    },
    "workspace_starter": {
        "path": inner_manifest.get("workspace_archive"),
        "sha256": inner_manifest.get("workspace_archive_sha256"),
    },
}
if release_manifest.get("nested_package_contents") != expected_nested_contents:
    raise ValueError("Outer release manifest and inner package manifest disagree about nested package contents")

print(f"Verified agent package extracted to: {agent_root}")
print(f"Temporary root to remove after setup: {temp_root}")
```

After this extraction, read `AGENT-OPERATING-INSTRUCTIONS.md` and `AGENT-STARTUP-PROMPT.md`, then run `tools/bootstrap.py`. It verifies the package manifest/checksums, cross-checks manifest-declared archive digests, and inspects the runtime and workspace archives before creating the project workspace.

## 4. Conversational destination discovery

Do not choose a destination silently.

1. Determine the current working directory and whether it is persistent, user-visible and writable. Do not assume it is suitable merely because it is writable.
2. If it is suitable, propose it as the destination (including the exact absolute path). Otherwise ask the owner for a persistent location that this agent environment can access.
3. Establish the project display name. Reuse a name clearly established in the conversation; otherwise ask for one. Do not invent a project name.
4. Check whether the proposed destination already exists. PBF creation requires a new, non-existing destination. Never overwrite, merge, delete or rename an existing directory to make room.
5. Check that the destination's parent already exists and is writable. Do not create ancestor directories without separately explaining the proposed path and receiving permission.
6. Explain the actions: verify the complete supplied package; temporarily extract the curated bootstrap runtime; run bootstrap-scope verification; create a new workspace; run workspace checks; record minimal setup provenance in the existing initial project-control record; remove only temporary extraction. Confirm that Git will not be initialized and no software/network dependencies will be installed.
7. Ask the owner to approve the exact project name and absolute destination. Wait for an unambiguous confirmation before invoking the bootstrap helper.

The bootstrap helper requires `--destination` and `--approved-destination` to match exactly. This flag is an invocation guard, not cryptographic evidence of user consent. Your conversation and the harness's permission model remain the actual approval boundary.

## 5. Execute the bootstrap helper

After explicit owner confirmation:

1. Confirm Python 3.11 or newer from the interpreter you will actually use.
2. Use the extracted agent-package root as `--package-root`.
3. Invoke `tools/bootstrap.py` with the project name, exact destination and the same exact path for `--approved-destination`.
4. Use the current interpreter executable where possible (`sys.executable`) rather than assuming `python` resolves correctly.
5. Allow the helper to complete. Do not run a second creation attempt in parallel.

The invocation shape is:

```text
python -B tools/bootstrap.py \
  --package-root "/path/to/extracted/PBF-Agent-Package" \
  --name "Confirmed Project Name" \
  --destination "/confirmed/persistent/path/Project-Blueprint" \
  --approved-destination "/confirmed/persistent/path/Project-Blueprint"
```

Adapt quoting and line continuation to the actual shell. The user does not need to run this command; you execute it with your available terminal tool.

The helper will:

- verify the package manifest and checksums;
- inspect bootstrap-runtime and workspace ZIP entries for traversal, unsafe links, duplicate/case/Unicode aliases, parent-component collisions, file/directory conflicts, encryption and excessive uncompressed size;
- extract the curated bootstrap runtime into a temporary directory;
- run `bp.py verify --scope bootstrap` against the extracted runtime;
- run the existing source command `bp.py new` with the workspace archive and exact destination;
- run `check --strict`, `index --check` and `audit-state --strict` in the new workspace;
- remove its temporary runtime extraction when the process exits.

The helper does not run the maintainer test suite during normal user setup. The complete maintained source and tests remain in the developer repository and are exercised by the release builder, not by an ordinary user installation.

## 6. Failure handling and cleanup

- Trust actual exit codes and read-back checks, not intended operations or progress messages.
- If setup fails before destination creation, report failure and do not claim a workspace exists.
- If the destination was created but a later check fails, preserve it for inspection. Do not automatically delete or overwrite it. Report the exact path and failed check.
- Do not retry to the same destination while it exists. Diagnose and obtain a new explicit owner decision before another attempt.
- Remove only temporary directories/files created by you for this setup, including the extracted inner agent package after all helper execution and read-back are complete.
- Do not delete the user's outer release ZIP, the nested ZIP inside it, pre-existing files or unrelated temporary directories.
- If cleanup fails, report the exact leftover temporary path. Do not claim it was removed.
- Do not initialize Git. Do not create a bulk set of project documents. `docs/` is intentionally sparse at creation.

## 7. Post-creation verification and workspace loading

After the helper returns success:

1. Parse the final `PBF_BOOTSTRAP_RESULT` record and confirm `status` is `verified`.
2. Confirm the reported destination exists and is a directory.
3. Read back these files from the generated workspace:
   - `README.md`
   - `AGENTS.md`
   - `_control/PROJECT-RULES.md`
   - `_control/STATE.md`
   - `_control/PHASES.md`
   - `_control/registry/INDEX.md`
4. Confirm all three workspace checks are reported as passed: `check --strict`, `index --check`, `audit-state --strict`.
5. Do not start project discovery or create D0.01/D0.02 at this stage.

After the read-back above, update the existing `Workspace setup provenance` field in `_control/STATE.md`. Record one concise value containing the setup date, `agent-assisted` method, framework version, Python version and the verification result. Do not create a setup-specific session log, new register or separate audit artifact. Read the changed `STATE.md` back, then run `python -B bp.py audit-state --strict` from the new workspace and record its actual result. If the field is absent or the update would require changing unrelated project state, stop and report the issue rather than inventing another record. Do not begin P0. Once the owner separately confirms that P0 should begin, follow the workspace's own `AGENTS.md` and operating rules.

## 8. Completion report and P0 confirmation

Report:

- Setup result: **Verified** or a truthful failure/partial/blocked state.
- Project display name and exact absolute workspace path.
- Framework version and workspace architecture revision.
- Source verification result.
- Workspace strict check, index check and read-only state audit results.
- Confirmation that temporary runtime extraction was removed.
- Confirmation that Git was not initialized.
- Any limitation, warning or cleanup item.

Then ask one direct question: **“The PBF workspace is set up and verified. Would you like to begin P0 discovery now?”**

Wait for the owner's confirmation. Do not begin P0 merely because their initial message said “let's get started”; the owner explicitly chose a separate post-setup confirmation step.

## 9. Manual alternative

Agent-assisted setup is the recommended path, not a mandatory path. The outer release's `docs/PBF-User-Guide.md` also documents manual setup with the PBF CLI for owners who prefer to run the commands themselves or use an environment without the required agent capabilities.
