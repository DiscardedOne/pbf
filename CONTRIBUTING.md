# Contributing to Project Blueprint Framework

Thank you for helping maintain PBF. Contributions should preserve the accepted architecture and improve observable framework behavior, correctness, documentation or release reliability.

## Before changing code

- Read `DEVELOPMENT.md`.
- Read `framework-dev/architecture/V3.0-WORKSPACE-ARCHITECTURE.md` for runtime/workspace changes.
- Identify whether a change belongs to `_framework/`, `starter/`, `src/`, `framework-dev/`, `release-assets/` or `tools/`.
- Keep maintainer-only material out of the generated workspace and ordinary user release unless it is required for setup or product use.

## Change expectations

- Keep the runtime standard-library-only unless an approved requirement justifies a dependency.
- Preserve Python 3.11 as the minimum declared version.
- Preserve `VERSION` as the single version input.
- Preserve `SourcePaths`/`WorkspacePaths` separation and workspace architecture revision 1.3.4.
- Do not introduce automatic Git initialization, broad filesystem writes, network access, system software installation or implicit workspace upgrades.
- Do not claim an OS-level sandbox or universal agent-harness compatibility.
- Keep the bootstrap runtime limited to files required to verify and create a workspace; keep the full developer source and tests in the developer repository.
- Preserve the separate owner confirmation before P0 discovery.
- Keep credentials, secret values, private user information, machine-specific paths and raw operational logs out of permanent source and release assets.

## Tests

Add regression tests for bug fixes and behavioral changes. The 94 compatibility tests are retained with a compact baseline identity/mapping fixture; do not delete coverage merely because its baseline originated in an earlier framework version.

Run:

```bash
python -B bp.py verify
python -B bp.py verify --tests
```

For one framework test module, set the import path for your shell.

POSIX shell:

```bash
PYTHONPATH=framework-dev/tests:src:_framework/tools python -B -m unittest discover -s framework-dev/tests -p test_source_verification.py -v
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "framework-dev/tests;src;_framework/tools"
python -B -m unittest discover -s framework-dev/tests -p test_source_verification.py -v
Remove-Item Env:PYTHONPATH
```

For the bootstrap helper alone:

```bash
python -B -m unittest discover -s tools/agent-bootstrap/tests -p 'test_*.py' -v
```

For a release-impacting change, also run:

```bash
python -B tools/release/build_release.py
```

A contribution is not release-verified merely because an individual unit test passes.

## Documentation and release inputs

Update the relevant authored files under `release-assets/`; do not edit ZIP outputs as source files. Keep links and commands aligned with the actual release package. Release evidence must describe only tests actually run in the current build and must state known limitations.

## Pull request / review description

Include:

- Problem and intended behavior.
- Affected architecture/source areas.
- Tests run and their exact results.
- Any compatibility or security implications.
- Whether release assets or package manifests change.
- Any remaining limitations or follow-up work.

Do not include unrelated session history or personal development-environment details.

## Public contributions

Before opening a pull request:

- Check existing issues and discussions for related work; describe the problem and intended outcome.
- Keep a change focused and explain any effect on workspace architecture, compatibility, package contents or release behavior.
- Add regression tests for behavior changes and report the exact commands/results that you ran. Do not claim platforms or Python versions that were not tested.
- Update the user-facing documentation, maintained test inventory, changelog and release checklist when they are affected.
- Do not include credentials, private project material, personal data, generated ZIPs, build logs or unrelated files.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately using the process in [SECURITY.md](SECURITY.md), not through a public issue.

By intentionally submitting a contribution for inclusion, you agree that the contribution is submitted under the Apache License 2.0, subject to its terms. This does not transfer ownership of your copyright. Do not submit material that you do not have permission to contribute under those terms.

A pull request should include the problem, proposed change, affected areas, tests and observed results, documentation updates, release impact and known limitations. Maintainers may request changes or decline a contribution that conflicts with the accepted scope or quality gates.
