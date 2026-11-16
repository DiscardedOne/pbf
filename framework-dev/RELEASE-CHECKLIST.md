# Agent-First Release Checklist

The standard release process produces one product artifact: `PBF-v<VERSION>-Agent-First-Release.zip`.

## Source readiness

- [ ] Root `VERSION` contains the intended semantic version.
- [ ] Accepted workspace architecture revision remains 1.3.4 unless a separate approved architecture revision exists.
- [ ] `python -B bp.py verify` passes.
- [ ] `python -B bp.py verify --tests` passes all maintained source and bootstrap tests.
- [ ] No credentials, secret values, private user data, machine-specific paths or unrelated artifacts are present.
- [ ] Developer documentation, release assets and links are current.

## Workspace starter

- [ ] `python -B bp.py build` succeeds using the maintained test gate.
- [ ] Workspace starter manifest and package checks pass.
- [ ] Fresh extraction passes workspace structural/strict/index/state checks.
- [ ] Git is not initialized by workspace creation.

## Bootstrap runtime and nested package

- [ ] Curated bootstrap runtime contains only verified workspace-creation inputs.
- [ ] `bp.py verify --scope bootstrap` passes from a fresh extraction of that runtime.
- [ ] Agent operating instructions and startup prompt accurately describe capability checks, destination confirmation, temporary extraction, cleanup and the separate P0 confirmation.
- [ ] Minimal setup provenance is recorded in an existing initial project-control record; no extra session log is introduced.
- [ ] Nested package manifest and exact checksum inventory are generated and verified.
- [ ] Unsafe paths, symlinks, duplicate/case/Unicode path aliases, file/directory conflicts and digest mismatches are rejected.

## Outer release

- [ ] Outer README, QUICKSTART and six consolidated references are copied from authored release assets.
- [ ] Product docs are flat under `docs/` and `docs/README.md` indexes them.
- [ ] Release evidence is concise, sanitized and generated from the current build; raw logs remain local under ignored `dist/`.
- [ ] Outer manifest and checksum inventory match every payload.
- [ ] Exactly one nested agent ZIP is present.
- [ ] No full maintainer source archive or maintainer-only test material is included.

## Final extracted-package acceptance

- [ ] Final outer ZIP passes CRC and complete checksum verification after extraction.
- [ ] Nested agent package passes its full manifest/checksum verification.
- [ ] Bootstrap is executed from the exact extracted nested package against a disposable new destination.
- [ ] The generated workspace passes `check --strict`, `index --check` and `audit-state --strict`.
- [ ] An existing destination is refused without modifying it.
- [ ] Only temporary files created by setup are removed.
- [ ] The agent reports the exact destination, results and limitations, and waits for explicit owner confirmation before P0.
- [ ] Final ZIP is copied to the release destination only after all gates pass.

## Publication discipline

- [ ] Final output is `dist/PBF-v<VERSION>-Agent-First-Release.zip`.
- [ ] Replacing an existing artifact requires an explicit `--force` invocation.
- [ ] Root `LICENSE` contains the Apache License 2.0 text; `starter/LICENSE` is byte-identical.
- [ ] Source verification checks the license files and release packaging propagates the license to the outer ZIP, nested package, bootstrap runtime and generated workspace.
- [ ] The workspace starter includes `PBF-LICENSE-SCOPE.md`, and the generated workspace preserves it to distinguish PBF-provided components from owner-authored project content and third-party material.
- [ ] Python/OS/harness claims are limited to evidence from the current or clearly identified historical test runs.
- [ ] Before the first public source-repository publication, `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` and `SECURITY.md` are present and internally consistent.
- [ ] Before announcing the repository, enable GitHub private vulnerability reporting and set a private maintainer contact method for Code of Conduct concerns.
- [ ] Publish the exact outer Agent-First ZIP SHA-256 in the official GitHub Release description and instruct users to compare their downloaded file with that value.
- [ ] State accurately that the GitHub account/repository is the publication trust source; the checksum detects mismatches but is not a detached digital signature.
