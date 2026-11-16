# Content lint rules

**Applies to:** project documents at `in-review` or `approved` status.  
**Implementation source:** `LINT_RULES` and `lint_document()` in `_framework/tools/blueprint.py`.  
**Purpose:** detect unfinished structural prompts and common signs of hollow or ambiguous documentation. These rules do not judge whether the requirements or technical content are correct.

## Rule catalog

| Rule ID | What it detects | `in-review` behavior | `approved` behavior | Typical resolution |
|---|---|---|---|---|
| `TPL001` | An unfilled explicit `[[FILL: ...]]` marker | Warning | Error | Replace the marker with real project content or use the narrowly scoped suppression for a literal example. |
| `DIR001` | Malformed, reasonless or unused placeholder suppression directive | Warning | Error | Correct the syntax/reason or remove the stale directive. |
| `TBD001` | `[TBD]` without a registered question ID | Error at all statuses | Error | Use `[TBD:Q-001]` linked to a real open question, or resolve it. |
| `TBD002` | Any `[TBD...]` remaining in approved content | — | Error | Resolve it before approval; even a registered open question is not acceptable in a fully approved document. |
| `TBD003` | Bare word `TBD` used as an unresolved value | Warning | Error | Resolve it or use the tracked `[TBD:Q-001]` form during drafting. |
| `TODO001` | `<!-- TODO ... -->` remains | — | Error | Complete the task or turn it into a tracked question/action. |
| `GUIDE001` | `<!-- GUIDE ... -->` author instruction remains | — | Warning | Remove authoring guidance from the final document. |
| `CHK001` | An unchecked Markdown checklist item | Warning | Error | Complete it, or tick it with evidence; use `N/A: reason` if it genuinely does not apply. |
| `SEC001` | An empty Markdown section | Warning | Error | Add substantive content or state `N/A: reason`; remove an unnecessary section. |
| `FLD001` | An empty labelled field, such as `- **Owner:**` or `- **Goals (G-):**` | Warning | Error | Fill it or write `N/A: reason` when genuinely inapplicable. This detects empty fields only; it does not validate IDs or relationship correctness. |
| `DIA001` | An approved document's catalog checklist expects a diagram, but none is present | — | Warning | Add the appropriate diagram or revisit the catalog requirement. |
| `VAG001` | Common vague wording such as “fast”, “scalable”, “easy”, “etc.”, “and/or”, “as needed” | Warning | Warning | Quantify/define the wording. A justified use may be silenced per document with `<!-- vague-ok: reason -->`. |

The helper emits stable rule IDs in lint messages. If code behavior changes, update this table and the regression tests. The test suite verifies that every rule ID declared by the helper has a documented entry here.

## Template prompt convention

All shipped templates use one explicit marker grammar:

```markdown
[[FILL: Describe the intended reader and why they need this document.]]
```

Only this marker syntax is interpreted as an unfilled template prompt. Ordinary bracketed prose such as `[the next section]`, sources such as `[Source: Acme pricing page]`, Markdown links, and ordinary inline-code phrases are not placeholders. `\\[[FILL: ...]]` is an escaped literal marker example. Fenced code content is scanned for explicit markers because a template may contain unfinished example inputs that must be completed before approval; inline code spans are ignored.

A freshly scaffolded document is expected to fail approval lint until its template markers and hollow sections/fields have been resolved. The regression suite enforces this invariant against every shipped template.

## Narrow suppression for literal marker examples

Suppressions exist only for rare cases where an **unescaped** `[[FILL: ...]]` must appear literally. They suppress `TPL001` only; they do not hide TODOs, TBDs, empty sections, unchecked lists, vague-wording warnings or other checks. Every suppression requires a meaningful reason.

### Inline, same-physical-line suppression

Preferred for a line inside a table or list:

```markdown
| Example syntax | [[FILL: literal marker example]] | <!-- blueprint-lint: ignore-line -- reason: this row documents the marker syntax -->
```

`ignore-line` suppresses only markers on that same physical source line. The comment is parsed from the raw source before HTML comments are stripped for normal lint analysis. It may be placed at the end of a table row or list item without inserting a new Markdown block.

### Next physical line suppression

Use for prose outside tables/lists:

```markdown
<!-- blueprint-lint: ignore-next-line -- reason: this paragraph documents literal marker syntax -->
[[FILL: literal marker example]]
```

“Next line” means the **immediately following physical source line**, not the next nonblank line. If that line is blank or contains no unfilled marker, the directive is stale and `DIR001` is raised. The directive must be a standalone HTML comment with a reason of at least eight characters. A standalone comment can break a Markdown table/list, so use `ignore-line` for those structures. The directive pre-pass runs before HTML comments are removed; otherwise the instruction itself would disappear.

### Suppression safety rules

- Do not add suppressions merely to make approval pass; prefer an escaped marker literal or replace a real prompt.
- Never use document-wide disable switches; the framework deliberately has none.
- Remove a suppression once its target marker is no longer needed, or `DIR001` will identify it as stale.
- Suppression comments are part of the document body. Adding one to an already approved document changes its approval fingerprint and therefore requires the normal revision/re-approval cycle.

## Severity and workflow

- Before `in-review`, ordinary hollow-content checks are not run, so drafting remains flexible. The always-on `[TBD]` question-ID rule still applies.
- In `in-review`, unresolved template/content findings generally warn, letting the owner see what remains.
- On approval, unfinished prompts, empty sections/fields, unchecked checklists and untagged TBD values become errors. `DIA001`, `GUIDE001` and `VAG001` remain warnings by design.
- `approve` runs approval-level lint even if global `check` was not run immediately before it.
- A zero-error result is structural evidence only. It is not a claim of semantic completeness or correctness.

## Workspace validation guidance

A generated project workspace can run its own structural checks from the workspace root:

```bash
python -B bp.py check --strict
python -B bp.py index --check
```

Maintainer regression tests for changes to the lint implementation belong to the separate PBF developer repository, not to an individual project workspace. Tests there should cover explicit marker recognition, normal bracketed prose, inline code, escaped markers, each suppression form, malformed/stale directives, and the invariant that every shipped template's unedited content fails approval-level prompt lint. New code-level rules must be added to this file and the `LINT_RULES` registry.
