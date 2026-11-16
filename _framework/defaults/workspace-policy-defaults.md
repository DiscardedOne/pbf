# Workspace Policy Defaults

This document explains the framework-owned defaults in `workspace-defaults.json`. The JSON file is authoritative for machine-readable identifiers and profile ranking. This document explains how those defaults are intended to be interpreted; it does not create a second configuration source.

- The default profile is selected per project in `_control/WORKSPACE.json`.
- Profile ranks establish the Lite < Standard < Exhaustive ordering.
- Vision and architecture document IDs identify the framework bootstrap documents.
- The ID-index document list identifies catalog documents that define stable IDs.
- Structural impact is a review-candidate relationship, distinct from content dependencies.

- `workspace_structure.required_files` and `required_directories` define the minimum operational workspace shape. These are checked by the runtime.
- `workspace_structure.optional_directories` are created by `new` as convenience locations but their presence is not required for workspace validity; Git and archives need not preserve empty folders.
- `asset_categories` defines supported supporting-material types under `docs/_assets/`. Asset files are supporting evidence, not automatically manifest-backed Markdown documents.
- Markdown files do not belong under `docs/_assets/`; explanatory notes belong in a catalog-backed document or `docs/99-appendix/`.
