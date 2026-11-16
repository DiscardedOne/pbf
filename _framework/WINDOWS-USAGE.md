# Windows and PowerShell Usage

This reference explains how to operate a Project Blueprint **workspace** on Windows. It is guidance, not evidence that a native Windows test was run for every release. Check the release verification record for the environments actually exercised.

## Python interpreter selection

Project Blueprint requires Python 3.11 or newer. Do not assume the `python` command selects the desired interpreter.

```powershell
py -3.11 --version
py -3.11 .\bp.py --version
py -3.11 .\bp.py check --strict
py -3.11 .\bp.py status --write
py -3.11 .\bp.py index --check
```

Use another installed version selector only after confirming it reports Python 3.11+. The launcher checks the version and prints guidance if the selected interpreter is too old.

## Paths and working directory

The workspace launcher discovers the workspace from its own location and supports invocation from nested directories. For predictable commands, open PowerShell at the workspace root. Quote paths containing spaces:

```powershell
Set-Location 'C:\Projects\Example-Blueprint'
py -3.11 .\bp.py check --strict
```

The documentation workspace is not the application repository. Keep application source code in its own repository or directory.

## Git and line endings

Workspace creation does not run `git init`. Initialize Git only after reviewing the destination and deciding that the workspace should be version-controlled:

```powershell
git init
git status --short
```

The workspace includes `.gitattributes` rules that normalize managed text files to LF and mark common binary formats as binary. If Git is installed, the framework's later package/regression validation includes an end-to-end `core.autocrlf=true` checkout test. Until that test is completed for the release, rely on the documented `.gitattributes` policy and the runtime's line-ending-normalized framework hashes; do not interpret this note as a native Windows verification claim.

## Cloud-synchronized folders

For initial agent-assisted deployments and workspaces requiring frequent small-file access, prefer a local, non-synchronized directory. Cloud-sync clients and remote mounts can introduce file-locking, latency, or context-loading behaviour that differs from a local filesystem. The source `new` command uses a path heuristic to warn about common synchronized roots; it does not reliably identify every sync provider and does not refuse creation solely for this reason.

## Troubleshooting

- **Unsupported Python:** run `py -0p` to inspect registered Python interpreters, then select an installed 3.11+ version explicitly.
- **Command not found:** use `py -3.11 .\bp.py ...` rather than relying on a PATH alias.
- **Manifest drift:** run `py -3.11 .\bp.py check`; do not edit the manifest merely to silence an unexpected warning. Restore the managed file or rebuild from a trusted framework package.
- **Git line-ending changes:** inspect `.gitattributes` and `git check-attr text eol -- AGENTS.md bp.py`; do not disable normalization as a shortcut.

For command syntax, use `py -3.11 .\bp.py --help` and the relevant subcommand help. Source-maintenance commands (`verify`, `build`, `new`) are available only in the framework source repository.
