# Maintained Test Suite

The test suite protects current PBF behavior. File names describe the behavior under test rather than the historical phase in which each test was introduced.

## Test modules

| Module | Methods | Focus |
|---|---:|---|
| `test_workspace_paths.py` | 28 | Centralized workspace/source path resolution, containment and path edge cases |
| `test_source_cli.py` | 27 | Source CLI, verification and workspace build/creation contracts |
| `test_compatibility_regressions.py` | 94 | Preserved v2.3.3-derived behavior, compatibility and golden regression contracts |
| `test_release_readiness.py` | 7 | Regression baseline mapping, Git line-ending policy and active documentation paths |
| `test_integrity_contracts.py` | 38 | Framework integrity, state/applicability and completion contracts |
| `test_agent_instructions.py` | 1 | Generated `AGENTS.md` operating contract |
| `test_source_verification.py` | 21 | Bootstrap/maintainer verification-scope separation, Markdown link handling and validation diagnostics |
| `test_release_builder.py` | 19 | Deterministic ZIPs, checksum inventories, path-collision rejection and authoritative version inputs |

The 94 compatibility methods are mapped one-to-one from the historical baseline in `fixtures/regression-baseline.json`. The fixture records the baseline archive digest, original test-module digest, method identities, port targets and equivalence notes. The retired old test source and migration inventory are not required at runtime or by the current verifier.

The two v2.3.2 golden fixtures remain because active regression tests consume them. They are compact test inputs, not archival reports.

The framework/developer suite has **235 methods**. The bootstrap helper has a separate 19-method suite at `tools/agent-bootstrap/tests/test_bootstrap.py`. The full maintained test count is therefore **254 methods**: 235 framework/developer methods and 19 bootstrap methods.

## Run tests

From the repository root:

```bash
python -B bp.py verify --tests
```

To run one module during development, set the import path for your shell.

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

The verifier runs each module in a separate interpreter process and stops on the first failing module. Git-dependent line-ending coverage skips when Git is unavailable. The test count is derived from test methods discovered in the maintained files; a count alone is not proof that the tests pass.
