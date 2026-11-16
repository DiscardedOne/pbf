# Workspace Configuration

The project-owned machine-readable configuration lives at `_control/WORKSPACE.json`. Framework-owned defaults live in [`defaults/workspace-defaults.json`](defaults/workspace-defaults.json), with their intent explained in [`defaults/workspace-policy-defaults.md`](defaults/workspace-policy-defaults.md).

## Project-owned settings

`WORKSPACE.json` contains the workspace schema version, layout version, project identity and permitted project choices such as the selected documentation profile. It does not define physical paths, framework version, profile rank tables, bootstrap document IDs or framework policy defaults. Physical paths are fixed by the layout-version implementation and resolved through `WorkspacePaths`.

## Profiles

The default starter profile is Standard. A profile determines which active document records are eligible for scaffolding, counted in progress and required by phase gates. It does not require the agent to generate every possible document. During D0.02, the agent should recommend the appropriate profile and tailor applicability and depth to the project.

| Profile | Starter active records | Intended depth |
|---|---:|---|
| Lite | 16 | Minimum coherent implementation-planning baseline. |
| Standard | 32 | Normal product and system planning depth. |
| Exhaustive | 42 | Comprehensive documentation for higher-complexity or higher-risk work. |

The counts describe the starter catalog and are neither a document cap nor a mandatory generation target. Repeatable families, conditional artifacts and project-specific additions can expand the actual document set.

## Workspace structure

The machine-readable defaults define required files/directories, optional convenience directories and supported asset categories. Optional directories may be absent because Git and archive formats do not reliably preserve empty directories. The runtime validates required files and directories only.

The canonical ADR directory is `docs/04-architecture/adr/`. It is fixed by layout version 1 rather than a project-configurable path. Project document paths in the manifest remain relative to `docs/`.

## Semantic sources

Project semantic discovery includes catalog-backed project documents and selected stakeholder-readable registers. Root `README.md` is supplemental orientation, not a source of canonical requirement IDs. `AGENTS.md`, `_control/PROJECT-RULES.md` and `_framework/` are operating instructions or framework references, not project requirements.
