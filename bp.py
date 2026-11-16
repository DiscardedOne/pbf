#!/usr/bin/env python3
"""Project Blueprint Framework launcher; dispatches by workspace/source context."""
from __future__ import annotations

import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 11)


def _python_guard(version_info=None) -> int:
    detected = version_info if version_info is not None else sys.version_info
    if tuple(detected[:2]) < MINIMUM_PYTHON:
        current = f"{detected[0]}.{detected[1]}.{detected[2]}"
        print(f"Project Blueprint requires Python 3.11 or newer; detected {current}.")
        print("Windows: try `py -3.11` (or another installed 3.11+ version).")
        print("POSIX/WSL: try `python3.11` or `python3`.")
        return 3
    return 0


def _prioritize_import_path(path: Path) -> None:
    """Put the path selected by context discovery ahead of ambient imports.

    A caller's PYTHONPATH may contain another PBF checkout (or a relative
    entry that resolves to the selected tree only after cwd changes). Merely
    checking membership can leave a conflicting path earlier in sys.path.
    Normalize equivalent entries, then place the discovered tree first.
    """
    target = Path(path).resolve()
    retained = []
    for entry in sys.path:
        candidate_path = Path(entry or Path.cwd())
        try:
            if candidate_path.resolve() == target:
                continue
        except (OSError, RuntimeError):
            pass
        retained.append(entry)
    sys.path[:] = [str(target), *retained]


def main(argv=None) -> int:
    guarded = _python_guard()
    if guarded:
        return guarded
    argv = list(sys.argv[1:] if argv is None else argv)
    script = Path(__file__).resolve()
    tools = script.parent / "_framework" / "tools"
    _prioritize_import_path(tools)
    from workspace_paths import discover_context
    mode, context = discover_context(start=Path.cwd(), launcher_path=script)
    if mode == "source":
        source_package = context.root / "src"
        _prioritize_import_path(source_package)
        try:
            from blueprint_framework.source_cli import main as source_main
            return source_main(argv)
        except (ImportError, OSError, ValueError) as exc:
            print(f"ERROR: source command initialization failed: {exc}")
            return 2
    if mode == "workspace":
        _prioritize_import_path(context.framework_tools)
        import blueprint
        blueprint.set_workspace_paths(context)
        return blueprint.main(argv)
    print("ERROR: No Project Blueprint source or workspace marker found.")
    print("Run from a workspace containing _control/WORKSPACE.json, or from the framework source repository.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
