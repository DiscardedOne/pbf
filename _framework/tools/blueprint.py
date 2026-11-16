#!/usr/bin/env python3
"""
Blueprint documentation framework - workspace runtime helper (standard library only, Python 3.11+).

  python bp.py check [--strict] [--readiness] [--gate N]   validate workspace; optionally report draft incompleteness
  python bp.py audit-state [--strict]                     read-only STATE/session reconciliation
  python bp.py status [--write] [--profile lite|standard|exhaustive]              progress per phase (--write updates _control/STATE.md)
  python bp.py scaffold --only D0.01[,D0.02] [--dry-run]  create selected document skeletons
  python bp.py scaffold --phase N [--dry-run]           create skeletons for one phase
  python bp.py scaffold --all [--profile P] [--dry-run]  create all active, in-profile skeletons
  python bp.py scaffold --phase N --override-architecture-gate --override-reason "..."
                                                                    reasoned exception to the Phase 0 architecture guard
  python bp.py set-status DOC_ID STATUS [--reason TEXT]   change workflow status (manifest + front matter)
  python bp.py approve DOC_ID --evidence TEXT [--by NAME] record owner approval (lint + SHA-256 approval fingerprint)
  python bp.py index [--check]                            regenerate (or verify) _control/registry/INDEX.md
  python bp.py maturity DOC_ID LEVEL                      set outline/working/detailed maturity
  python bp.py applicability DOC_ID LEVEL --reason TEXT  record applicability decision
  python bp.py profile [lite|standard|exhaustive]         show/set default depth profile
  python bp.py graph                         print a Mermaid dependency graph of documents
  python bp.py session                       create the next session log from the template

Run through the workspace-root bp.py launcher; paths are resolved from the validated workspace marker.
Exit code of `check` is 1 when errors are found, else 0.
"""
from __future__ import annotations

import argparse
import errno
import datetime
import hashlib
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from workspace_paths import (WorkspacePaths, discover_context, WorkspaceDiscoveryError,
                              validate_framework_manifest, validate_gitattributes,
                              validate_workspace_structure)

_ACTIVE_WORKSPACE_PATHS: WorkspacePaths | None = None


def set_workspace_paths(paths: WorkspacePaths) -> None:
    """Bind this process to one validated immutable workspace path map."""
    global _ACTIVE_WORKSPACE_PATHS
    _ACTIVE_WORKSPACE_PATHS = paths


def workspace_paths() -> WorkspacePaths:
    """Return the active workspace paths, discovering them only when needed."""
    global _ACTIVE_WORKSPACE_PATHS
    if _ACTIVE_WORKSPACE_PATHS is None:
        mode, context = discover_context(start=Path.cwd(), launcher_path=Path(__file__).resolve())
        if mode != "workspace":
            raise WorkspaceDiscoveryError("Workspace commands require _control/WORKSPACE.json; no live workspace was discovered")
        _ACTIVE_WORKSPACE_PATHS = context
    return _ACTIVE_WORKSPACE_PATHS


def relative_path(path: Path) -> str:
    return workspace_paths().relative(path)


STATUSES = ["not-started", "interviewing", "drafting", "in-review", "approved",
            "needs-revision", "superseded", "expanded"]
LEGACY_STATUSES = {"excluded"}
SKIP = {"superseded", "expanded"}
APPLICABILITY_VALUES = {"active", "conditional", "deferred", "excluded"}
PROFILE_TIERS = {"lite", "standard", "exhaustive"}
WEIGHT = {"not-started": 0, "interviewing": 10, "drafting": 40, "in-review": 75,
          "approved": 100, "needs-revision": 50}
RANK = {"not-started": 0, "interviewing": 1, "drafting": 2, "needs-revision": 2,
        "in-review": 3, "approved": 4}
SIZE_W = {"S": 1, "M": 2, "L": 3}
ID_PREFIXES = "G|SM|STK|CON|PER|FEAT|UC|US|FR|NFR|ENT|BR|CMP|API|EVT|TC|MS|EP|ASM|RSK|Q|ADR|CR"
ID_RE = re.compile(r"\b(?:%s)-\d{2,4}\b" % ID_PREFIXES)
FULL_ID_RE = re.compile(r"^(?:%s)-\d{2,4}$" % ID_PREFIXES)
DOC_ID_RE = re.compile(r"^D\d+\.\d{2,}(?:\.\d{2,})*$")
REQUIRED_FM = ["doc_id", "title", "phase", "status", "maturity", "version", "last_updated", "depends_on", "summary", "applicability", "profile_tier"]
# Allowed manual workflow transitions. `approved` is reachable only through the `approve` command.
TRANSITIONS = {
    "not-started": {"interviewing", "drafting", "superseded", "expanded"},
    "interviewing": {"drafting", "superseded"},
    "drafting": {"interviewing", "in-review", "superseded"},
    "in-review": {"drafting", "superseded"},
    "approved": {"needs-revision", "superseded"},
    "needs-revision": {"drafting", "in-review", "superseded"},
    "superseded": set(),
    "expanded": set(),
}
VAGUE_RE = re.compile(r"\b(?:fast|quick(?:ly)?|scalable|robust|user-friendly|intuitive|seamless(?:ly)?|easy|easily)\b|\betc\.|\band/or\b|\bas needed\b|\bas appropriate\b", re.I)
FILL_RE = re.compile(r"(?<!\\)\[\[FILL:\s*([^]\n]+?)\]\]", re.I)
IGNORE_LINE_RE = re.compile(r"<!--\s*blueprint-lint:\s*ignore-line\s*--\s*reason:\s*(.*?)\s*-->", re.I)
IGNORE_NEXT_LINE_RE = re.compile(r"<!--\s*blueprint-lint:\s*ignore-next-line\s*--\s*reason:\s*(.*?)\s*-->", re.I)
INLINE_CODE_RE = re.compile(r"(?<!`)(`{1,2})(?!`)(.+?)(?<!`)\1(?!`)")
LINT_DIRECTIVE_TOKEN_RE = re.compile(r"<!--\s*blueprint-lint:", re.I)
FIELD_RE = re.compile(r"^(\s*)[-*]\s+(?:\*\*[^*\n]+:\*\*|\*\*[^*\n]+\*\*:|[A-Za-z][^:\n]{0,60}:)\s*$")
BARE_TBD_RE = re.compile(r"(?<![\[A-Za-z])TBD(?![A-Za-z:\]])")


def strip_html_comments(text: str) -> str:
    """Remove complete HTML comments in one forward pass.

    An unterminated opener is preserved, matching the former non-greedy regex
    substitution while avoiding repeated suffix scans on malformed comments.
    """
    opener = "<!--"
    closer = "-->"
    output: list[str] = []
    cursor = 0
    while True:
        start = text.find(opener, cursor)
        if start < 0:
            output.append(text[cursor:])
            break
        output.append(text[cursor:start])
        end = text.find(closer, start + len(opener))
        if end < 0:
            output.append(text[start:])
            break
        cursor = end + len(closer)
    return "".join(output)


MAX_MARKDOWN_LINK_COMPONENT_CHARS = 2048
MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE = 16
_MARKDOWN_NONWHITESPACE_RE = re.compile(r"\S")
_MARKDOWN_LINK_STOP_RE = re.compile(r"[\s)>]")
_MARKDOWN_URI_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_INVALID_URI_PERCENT_ESCAPE_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_DATA_URI_BASE64_RE = re.compile(r"[A-Za-z0-9+/]*={0,2}")


def _is_external_markdown_target(target: str) -> bool:
    """Return whether a Markdown target has URI rather than local-path syntax."""
    return target.startswith("//") or bool(_MARKDOWN_URI_SCHEME_RE.match(target))


def _external_markdown_target_error(target: str, split) -> str | None:
    """Return a bounded syntax error for an external URI, or ``None`` if valid."""
    if _INVALID_URI_PERCENT_ESCAPE_RE.search(target):
        return "external URI contains an invalid percent escape"

    scheme = split.scheme.lower()
    if scheme in {"http", "https"} or target.startswith("//"):
        if not split.netloc or not split.hostname:
            return "HTTP(S) URI must contain a valid host"
        try:
            _ = split.port
        except ValueError:
            return "HTTP(S) URI contains an invalid port"
    elif scheme == "data":
        _metadata, separator, payload = split.path.partition(",")
        if not separator:
            return "data URI is missing its required comma separator"
        if _metadata.lower().endswith(";base64") and not _DATA_URI_BASE64_RE.fullmatch(payload):
            return "data URI contains malformed Base64 data"

    return None


def inline_markdown_link_occurrences(
    text: str, metrics: dict[str, int] | None = None
) -> tuple[list[tuple[str, int]], list[tuple[int, str]]]:
    """Collect simple inline link targets and malformed/overlong candidates.

    The next target delimiter is cached as candidates advance through the
    document. Whitespace skips use bounded C-level regex searches. Each input
    character is therefore examined a bounded number of times even when a
    document contains dense unterminated link candidates.

    Returns ``(targets, issues)``. Each item carries a source-text offset so
    the caller can report a line number without rescanning the full source for
    every finding. Diagnostic output is capped per file to prevent an attacker
    from generating an unbounded number of messages from repeated fragments.
    """
    n = len(text)
    targets: list[tuple[str, int]] = []
    issues: list[tuple[int, str]] = []
    pending_open: int | None = None
    pos = 0
    cached_from = -1
    cached_stop = -1
    issue_count = 0

    def increment(name: str) -> None:
        if metrics is not None:
            metrics[name] = metrics.get(name, 0) + 1

    def next_stop(start: int) -> int:
        nonlocal cached_from, cached_stop
        if cached_from <= start <= cached_stop:
            return cached_stop
        increment("stop_searches")
        match = _MARKDOWN_LINK_STOP_RE.search(text, start)
        cached_from = start
        cached_stop = match.start() if match else n
        return cached_stop

    def add_issue(offset: int, message: str) -> None:
        nonlocal issue_count
        issue_count += 1
        if len(issues) < MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE:
            issues.append((offset, message))

    def parse_after_close(close_bracket: int) -> tuple[str, int] | None:
        local_limit = min(n, close_bracket + 1 + MAX_MARKDOWN_LINK_COMPONENT_CHARS)
        current = close_bracket + 1
        if current >= n or text[current] != "(":
            return None
        current += 1

        increment("whitespace_searches")
        match = _MARKDOWN_NONWHITESPACE_RE.search(text, current, local_limit)
        if match is None:
            return None
        current = match.start()
        if current < local_limit and text[current] == "<":
            current += 1
        target_start = current

        # URI targets do not become filesystem paths. Let the scanner consume
        # the complete URI, while retaining the 2,048-character bound for
        # local targets. The scan remains a single forward delimiter search.
        uri_target = text.startswith("//", target_start) or bool(_MARKDOWN_URI_SCHEME_RE.match(text, target_start))
        limit = n if uri_target else local_limit
        stop = next_stop(target_start)
        current = min(stop, limit)
        if not uri_target and stop >= limit and limit < n:
            add_issue(target_start, f"inline link target exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character parsing limit")
            return None
        if current == target_start:
            return None

        target = text[target_start:current]
        if current < limit and text[current] == ">":
            current += 1

        whitespace_start = current
        increment("whitespace_searches")
        match = _MARKDOWN_NONWHITESPACE_RE.search(text, current, limit)
        current = match.start() if match else limit
        if current < limit and text[current] == '"':
            if current == whitespace_start:
                return None
            title_end = text.find('"', current + 1, limit)
            if title_end < 0:
                return None
            current = title_end + 1
            increment("whitespace_searches")
            match = _MARKDOWN_NONWHITESPACE_RE.search(text, current, limit)
            current = match.start() if match else limit
        if current >= limit or text[current] != ")":
            return None
        return target, current

    while pos < n:
        open_at = text.find("[", pos)
        close_at = text.find("]", pos)
        if open_at < 0 and close_at < 0:
            break
        if open_at >= 0 and (close_at < 0 or open_at < close_at):
            if pending_open is None:
                pending_open = open_at
            pos = open_at + 1
            continue

        # A closing bracket without a pending opening bracket is just text.
        if pending_open is not None:
            link_start = pending_open
            label_length = close_at - link_start - 1
            if label_length > MAX_MARKDOWN_LINK_COMPONENT_CHARS:
                add_issue(link_start, f"inline link label exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character parsing limit")
                parsed = None
            else:
                parsed = parse_after_close(close_at)
            pending_open = None
            increment("candidates")
            if parsed is not None:
                target, closing_paren = parsed
                targets.append((target, link_start))
                pos = closing_paren + 1
                continue
        pos = close_at + 1

    if metrics is not None:
        metrics["issues_total"] = issue_count
    if issue_count > len(issues):
        issues.append((issues[-1][0] if issues else 0,
                       f"{issue_count - len(issues)} additional malformed/overlong link candidates omitted"))
    return targets, issues


def inline_markdown_link_targets(text: str) -> list[str]:
    """Compatibility wrapper returning only successfully parsed link targets."""
    occurrences, _issues = inline_markdown_link_occurrences(text)
    return [target for target, _offset in occurrences]

def reference_markdown_link_occurrences(
    text: str,
) -> tuple[list[tuple[str, str, int]], list[tuple[int, str]]]:
    """Collect reference-link labels with source offsets and bounded diagnostics."""
    references: list[tuple[str, str, int]] = []
    issues: list[tuple[int, str]] = []
    pending_open: int | None = None
    pos = 0
    while pos < len(text):
        char = text[pos]
        if char == "[" and pending_open is None:
            pending_open = pos
        elif char == "]" and pending_open is not None:
            first_start = pending_open
            first_end = pos
            pending_open = None
            first_length = first_end - first_start - 1
            if first_length > MAX_MARKDOWN_LINK_COMPONENT_CHARS:
                if len(issues) < MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE:
                    issues.append((first_start, f"reference link label exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character parsing limit"))
            elif first_end + 1 < len(text) and text[first_end + 1] == "[":
                second_start = first_end + 2
                second_limit = min(len(text), second_start + MAX_MARKDOWN_LINK_COMPONENT_CHARS + 1)
                second_end = text.find("]", second_start, second_limit)
                if second_end >= 0:
                    references.append((text[first_start + 1:first_end], text[second_start:second_end], first_start))
                    pos = second_end + 1
                    continue
                if second_limit < len(text) and len(issues) < MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE:
                    issues.append((second_start, f"reference link label exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character parsing limit or is unterminated"))
        pos += 1
    return references, issues


def reference_markdown_link_labels(text: str) -> list[tuple[str, str]]:
    """Compatibility wrapper returning `[label][reference]` pairs."""
    references, _issues = reference_markdown_link_occurrences(text)
    return [(label, reference) for label, reference, _offset in references]

# The code and _framework/LINT-RULES.md share these stable rule identifiers.
LINT_RULES = {
    "TPL001": "Unfilled explicit [[FILL: ...]] template marker",
    "DIR001": "Malformed, reasonless, or unused template-marker suppression directive",
    "TBD001": "Untagged [TBD] missing a registered question ID",
    "TBD002": "Approved document retains a tagged or untagged [TBD]",
    "TODO001": "Approved document retains a TODO comment",
    "GUIDE001": "Approved document retains a GUIDE comment",
    "CHK001": "Unchecked checklist item during review or approval",
    "TBD003": "Bare untagged TBD word",
    "SEC001": "Empty Markdown section",
    "FLD001": "Empty labelled field",
    "DIA001": "Catalog-required diagram missing from approved document",
    "VAG001": "Vague or unmeasured wording",
}
MATURITIES = {"outline", "working", "detailed"}
ARCHITECTURE_REQUIRED_HEADINGS = [
    "## Project profile and documentation drivers",
    "## Proposed document architecture",
    "## Document inventory and applicability",
    "## Phase and sequencing adaptations",
    "## Source-of-truth and dependency model",
    "## Diagrams and visual artifacts",
    "## Quality coverage map",
    "## Architecture evolution triggers",
    "## Owner review and current agreement",
]
KNOWN_DIAGRAMS = {"flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
                  "erDiagram", "journey", "gantt", "pie", "quadrantChart", "requirementDiagram", "gitGraph",
                  "mindmap", "timeline", "C4Context", "C4Container", "C4Component", "C4Dynamic",
                  "C4Deployment", "sankey-beta", "xychart-beta", "block-beta", "architecture-beta",
                  "packet-beta", "kanban"}

FENCE_RE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.S | re.M)
MERMAID_RE = re.compile(r"^```mermaid[^\n]*\n(.*?)^```", re.S | re.M)
REFERENCE_DEFINITION_RE = re.compile(r"^[ \t]{0,3}\[([^]\r\n]+)\]:[ \t]*(?:<([^>\r\n]+)>|([^ \t\r\n]+))(?:[ \t]+[^\r\n]*)?$", re.M)
SEP_RE = re.compile(r"^\s*\|[\s:|\-]+\|?\s*$")


# ----------------------------------------------------------------- helpers
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)




def strip_code(text: str) -> str:
    return FENCE_RE.sub("", text)


def strip_noise(text: str) -> str:
    """Remove fenced code and HTML comments (guidance text must not trigger link/ID checks)."""
    return strip_html_comments(FENCE_RE.sub("", text))


_MASK_NON_NEWLINE_RE = re.compile(r"[^\r\n]")


def _mask_markdown_noise_with_diagnostics(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Mask fenced code/comments, preserving offsets and reporting open comments."""
    masked = FENCE_RE.sub(lambda match: _MASK_NON_NEWLINE_RE.sub(" ", match.group(0)), text)
    chars = list(masked)
    issues: list[tuple[int, str]] = []
    cursor = 0
    while True:
        start = masked.find("<!--", cursor)
        if start < 0:
            break
        end = masked.find("-->", start + 4)
        if end < 0:
            issues.append((start, "unterminated HTML comment"))
            end = len(masked)
        else:
            end += 3
        replacement = _MASK_NON_NEWLINE_RE.sub(" ", text[start:end])
        chars[start:end] = replacement
        cursor = end
        if end == len(masked):
            break
    return "".join(chars), issues


def mask_markdown_noise_preserving_offsets(text: str) -> str:
    """Mask fenced code and HTML comments while preserving every source offset."""
    return _mask_markdown_noise_with_diagnostics(text)[0]


def split_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_tables(text: str):
    """Return [(header, rows)] for every Markdown table in text."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and SEP_RE.match(lines[i + 1]):
            header = split_row(lines[i])
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append((header, rows))
        else:
            i += 1
    return out


def front_matter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            value = v.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
                value = value[1:-1].replace("\\\"", "\"")
            fm[k.strip()] = value
    return fm


def parse_list(value: str):
    value = value.strip().strip("[]")
    return [x.strip().strip("`") for x in value.split(",") if x.strip() and x.strip() not in ("-", "—")]


def clean(cell: str) -> str:
    return cell.strip().strip("`*").strip()


def doc_phase(doc_id: str) -> int:
    match = re.match(r"D(\d+)\.", doc_id)
    if not match:
        raise ValueError(f"Invalid document ID: {doc_id}")
    return int(match.group(1))


def load_workspace_config():
    """Merge framework-owned defaults with project-owned non-path settings."""
    ws = workspace_paths()
    defaults_path = ws.defaults
    config_path = ws.workspace_config
    try:
        defaults = json.loads(read(defaults_path))
        config = json.loads(read(config_path))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid workspace defaults/configuration: {exc}") from exc
    if not isinstance(defaults, dict) or not isinstance(config, dict):
        raise ValueError("Workspace defaults and WORKSPACE.json must contain JSON objects")
    if isinstance(defaults.get("defaults_schema_version"), bool) or defaults.get("defaults_schema_version") != 1:
        raise ValueError("Unsupported workspace defaults schema; expected defaults_schema_version 1")
    allowed_keys = {"workspace_schema_version", "layout_version", "project", "profile"}
    unknown_keys = sorted(set(config) - allowed_keys)
    if unknown_keys:
        raise ValueError("WORKSPACE.json contains unsupported or framework-owned setting(s): " + ", ".join(unknown_keys))
    if (isinstance(config.get("workspace_schema_version"), bool) or config.get("workspace_schema_version") != 1
            or isinstance(config.get("layout_version"), bool) or config.get("layout_version") != 1):
        raise ValueError("Unsupported workspace schema/layout version; this runtime requires schema 1 and layout 1")
    merged = dict(defaults)
    merged.update(config)
    merged["profile_ranks"] = dict(defaults.get("profile_ranks", {}))
    return merged

def load_phases():
    """Load phase names from the workspace phase registry rather than a hard-coded enum."""
    config = load_workspace_config()
    path = workspace_paths().phases
    if not path.exists():
        return {}
    phases = {}
    for header, rows in parse_tables(strip_code(read(path))):
        h = [c.strip().lower() for c in header]
        if "phase" not in h or "name" not in h:
            continue
        ix_phase, ix_name = h.index("phase"), h.index("name")
        for row in rows:
            if len(row) <= max(ix_phase, ix_name):
                continue
            try:
                number = int(clean(row[ix_phase]))
            except ValueError:
                continue
            name = clean(row[ix_name])
            if name:
                phases[number] = name
    return phases


def profile_rank(profile: str, config=None) -> int:
    config = config or load_workspace_config()
    return int(config.get("profile_ranks", {}).get(profile.lower(), 0))


def profile_eligible(doc: dict, profile: str, config=None) -> bool:
    config = config or load_workspace_config()
    tier = doc.get("profile_tier", "standard").lower()
    rank = profile_rank(profile, config)
    return rank > 0 and profile_rank(tier, config) > 0 and profile_rank(tier, config) <= rank


def is_scaffoldable(doc: dict, profile: str | None = None, config=None) -> bool:
    """Return whether a document is in scope for generated files in the selected profile."""
    config = config or load_workspace_config()
    profile = profile or config.get("profile", "standard")
    return (doc.get("applicability", "active") == "active"
            and doc.get("status") not in SKIP
            and doc.get("status") != "excluded"
            and not doc.get("path", "").endswith("/")
            and profile_eligible(doc, profile, config))


def load_manifest():
    config = load_workspace_config()
    path = workspace_paths().manifest
    if not path.exists():
        sys.exit(f"{path.relative_to(workspace_paths().root).as_posix()} not found")
    docs = []
    for header, rows in parse_tables(strip_code(read(path))):
        h = [c.lower() for c in header]
        if "doc id" not in h:
            continue
        ix = {n: i for i, n in enumerate(h)}
        for r in rows:
            if len(r) < len(h):
                continue

            def g(k):
                return clean(r[ix[k]]) if k in ix else ""
            did = g("doc id")
            if not did:
                continue
            phase_text = g("phase")
            try:
                phase_value = int(phase_text) if phase_text else (doc_phase(did) if DOC_ID_RE.match(did) else -1)
            except ValueError:
                phase_value = -1
            type_value = (g("catalog class") or g("type")).lower()
            default_applicability = "conditional" if type_value == "conditional" else "active"
            docs.append({
                "id": did, "path": g("path"),
                "phase": phase_value,
                "type": type_value, "size": (g("size") or "M").upper(),
                "status": g("status").lower(), "depends": parse_list(g("depends on")),
                "title": g("title"), "maturity": (g("maturity") or "outline").lower(),
                "applicability": (g("applicability") or default_applicability).lower(),
                "applicability_rationale": "" if g("applicability rationale") in ("-", "—") else g("applicability rationale"),
                "profile_tier": (g("profile tier") or "standard").lower(),
                "version": g("version") or "0.1",
                "last_updated": g("last updated") or "",
            })
    return docs


def load_catalog():
    path = workspace_paths().catalog
    cat = {}
    if not path.exists():
        return cat
    for header, rows in parse_tables(strip_code(read(path))):
        h = [c.lower() for c in header]
        if "doc id" not in h or "must contain" not in h:
            continue
        ix = {n: i for i, n in enumerate(h)}
        for r in rows:
            if len(r) < len(h):
                continue
            item = {k: clean(r[ix[k]]) if k != "must contain" else r[ix[k]].strip() for k in ix}
            cat[item["doc id"]] = item
    return cat



def semantic_index_paths(docs=None) -> set[str]:
    """Resolve ID-index files from current workspace configuration and manifest IDs, not stale paths."""
    config = load_workspace_config()
    docs = docs if docs is not None else load_manifest()
    paths = set()
    ws = workspace_paths()
    for fixed_path in (ws.manifest, ws.decisions, ws.approvals, ws.index):
        paths.add(ws.relative(fixed_path))
    indexed_ids = set(config.get("id_index_document_ids", ["D7.04"]))
    for d in docs:
        if d["id"] in indexed_ids and not d["path"].endswith("/"):
            fp = safe_document_path(d["path"])
            if fp:
                paths.add(workspace_paths().relative(fp))
    return paths

def today() -> str:
    return datetime.date.today().isoformat()


def update_manifest_row(doc_id: str, updates: dict[str, str]) -> bool:
    """Update named columns for a document row, preserving unrelated manifest content."""
    path = workspace_paths().manifest
    lines = read(path).splitlines()
    header_idx = next((i for i, line in enumerate(lines)
                       if line.lstrip().startswith("|") and "Doc ID" in split_row(line)
                       and "Applicability" in split_row(line)), None)
    if header_idx is None:
        return False
    headers = split_row(lines[header_idx])
    if any(name not in headers for name in updates):
        raise ValueError("Manifest is missing required column(s): " + ", ".join(name for name in updates if name not in headers))
    id_index = headers.index("Doc ID")
    indexes = {name: headers.index(name) for name in updates}
    for i in range(header_idx + 2, len(lines)):
        if not lines[i].lstrip().startswith("|"):
            continue
        cells = split_row(lines[i])
        if len(cells) > id_index and clean(cells[id_index]) == doc_id:
            for name, value in updates.items():
                if "|" in value:
                    raise ValueError("Manifest field values cannot contain an unescaped pipe character")
                cells[indexes[name]] = value
            lines[i] = "| " + " | ".join(cells) + " |"
            write(path, "\n".join(lines) + "\n")
            return True
    return False


def update_front_matter_fields(path: Path, updates: dict[str, str]) -> bool:
    """Synchronize a set of front-matter fields without touching document prose."""
    if not path.exists():
        return False
    content = read(path)
    if front_matter(content) is None:
        raise ValueError(f"{path.relative_to(workspace_paths().root).as_posix()} has no front matter")
    for key, value in updates.items():
        if key == "applicability_rationale":
            escaped = value.replace('\\', '\\\\').replace('\"', '\\\"')
            line_value = f'"{escaped}"'
        else:
            line_value = value
        pattern = rf"^{re.escape(key)}:\s*.*$"
        if re.search(pattern, content, re.M):
            content = re.sub(pattern, lambda m, k=key, v=line_value: f"{k}: {v}", content, count=1, flags=re.M)
        else:
            content = re.sub(r"^(---\s*\n)", lambda m, k=key, v=line_value: m.group(1) + f"{k}: {v}\n", content, count=1, flags=re.M)
    write(path, content)
    return True


def record_override(kind: str, reason: str, document_ids: list[str]) -> Path:
    """Persist explicit guard overrides instead of relying on console output alone."""
    folder = workspace_paths().overrides
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d-%H%M%S-%f")
    path = folder / f"{kind}-{stamp}.md"
    write(path, f"# Override record — {kind}\n\n- **Date/time (local machine):** {now.isoformat(timespec='microseconds')}\n- **Reason:** {reason.strip()}\n- **Affected document IDs:** {', '.join(document_ids) if document_ids else 'none'}\n- **Scope:** This record documents a tooling-guard exception; it does not imply owner approval of the affected design.\n")
    print(f"Override recorded: {path.relative_to(workspace_paths().root).as_posix()}")
    return path


EVENT_TYPES = {"status_transition", "approval", "scaffold", "applicability_change",
               "maturity_change", "profile_change", "architecture_override"}


def latest_session_context() -> str | None:
    """Return the highest numbered actual session handoff, never README/template files."""
    sessions = []
    if workspace_paths().sessions.exists():
        for path in workspace_paths().sessions.glob("session-*.md"):
            match = re.match(r"^session-(\d{3,})-.+\.md$", path.name, re.I)
            if match:
                sessions.append((int(match.group(1)), path.stem))
    return max(sessions, default=(0, None), key=lambda item: item[0])[1]


def build_state_event(event_type: str, **fields) -> dict:
    event = {
        "schema_version": 1,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "event_type": event_type,
        "actor": "operator",
        "session_id": latest_session_context(),
        "reason": None,
    }
    event.update(fields)
    return event


def append_state_events(events: list[dict]) -> None:
    """Append a batch of JSONL events; attempt truncation if the append fails mid-write."""
    if not events:
        return
    workspace_paths().status_transitions.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in events)
    with open(workspace_paths().status_transitions, "a+", encoding="utf-8", newline="\n") as fh:
        fh.seek(0, os.SEEK_END)
        original_end = fh.tell()
        try:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        except OSError:
            try:
                fh.seek(original_end)
                fh.truncate()
                fh.flush()
                os.fsync(fh.fileno())
            except OSError:
                pass
            raise


def persist_state_events(events: list[dict], operation: str) -> bool:
    """Return False with explicit recovery guidance if the audit-log append fails."""
    try:
        append_state_events(events)
        return True
    except OSError as exc:
        print(f"ERROR: {operation} may already have updated workspace files, but {workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()} could not be written: {exc}")
        print("Inspect the workspace diff, restore write access, reconcile the event log, then run `python bp.py check --strict`. Do not assume the operation was rolled back.")
        return False


def validate_state_event_log(docs: list[dict]):
    """Return severity/message pairs for the optional JSONL workspace mutation log."""
    if not workspace_paths().status_transitions.exists():
        return []
    issues = []
    known = {d["id"]: d for d in docs}
    latest_status_event = {}
    for line_no, raw_line in enumerate(read(workspace_paths().status_transitions).splitlines(), 1):
        if not raw_line.strip():
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: blank lines are not valid JSONL records"))
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: invalid JSON: {exc.msg}"))
            continue
        if not isinstance(event, dict):
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: each record must be a JSON object"))
            continue
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: unknown event_type {event_type!r}"))
            continue
        required = {"schema_version", "timestamp", "event_type", "actor", "session_id", "reason"}
        if not required.issubset(event):
            missing = sorted(required - set(event))
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: missing fields {', '.join(missing)}"))
        if event.get("schema_version") != 1:
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: unsupported schema_version {event.get('schema_version')!r}"))
        if not isinstance(event.get("timestamp"), str):
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: timestamp must be a string"))
        else:
            try:
                datetime.datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: invalid ISO timestamp"))
        if not isinstance(event.get("actor"), str) or not event.get("actor", "").strip():
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: actor must be a non-empty string"))
        if event_type in {"status_transition", "approval"}:
            required_status = {"document_id", "from_status", "to_status"}
            if not required_status.issubset(event):
                issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: {event_type} needs document_id/from_status/to_status"))
            elif event.get("document_id") in known:
                latest_status_event[event["document_id"]] = (event.get("to_status"), line_no)
        if event_type in {"scaffold", "applicability_change", "maturity_change"} and not event.get("document_id"):
            issues.append(("error", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: {event_type} requires document_id"))
    for doc_id, (last_status, line_no) in latest_status_event.items():
        current = known[doc_id]["status"]
        if last_status != current:
            issues.append(("warning", f"{workspace_paths().status_transitions.relative_to(workspace_paths().root).as_posix()}:{line_no}: last logged status for {doc_id} is {last_status!r}, but MANIFEST says {current!r}; this may be a legitimate manual edit, reconcile if unintended"))
    return issues


# ----------------------------------------------------------------- progress
def progress(docs, profile: str | None = None):
    config = load_workspace_config()
    selected_profile = (profile or config.get("profile", "standard")).lower()
    per = {}
    for d in docs:
        if d["applicability"] != "active" or d["status"] in SKIP or d["status"] == "excluded":
            continue
        if not profile_eligible(d, selected_profile, config):
            continue
        if d["phase"] < 0:
            continue
        w = SIZE_W.get(d["size"], 2)
        p = per.setdefault(d["phase"], {"w": 0, "score": 0, "n": 0, "done": 0})
        p["w"] += w
        p["score"] += w * WEIGHT.get(d["status"], 0)
        p["n"] += 1
        p["done"] += 1 if d["status"] == "approved" else 0
    return per


def progress_table(docs, profile: str | None = None) -> str:
    config = load_workspace_config()
    selected_profile = (profile or config.get("profile", "standard")).lower()
    per = progress(docs, selected_profile)
    phase_names = load_phases()
    phases = sorted(set(phase_names) | {d["phase"] for d in docs if d["phase"] >= 0})
    lines = [f"_Selected profile: **{selected_profile.title()}**. Only active, in-profile documents contribute._", "", "| Phase | Name | Approved / total | Progress |", "|---|---|---|---|"]
    tw = ts = tn = td = 0
    for ph in phases:
        p = per.get(ph)
        name = phase_names.get(ph, f"UNREGISTERED PHASE {ph}")
        if not p:
            lines.append(f"| {ph} | {name} | 0 / 0 | n/a |")
            continue
        pct = round(p["score"] / p["w"]) if p["w"] else 0
        lines.append(f"| {ph} | {name} | {p['done']} / {p['n']} | {pct}% |")
        tw += p["w"]; ts += p["score"]; tn += p["n"]; td += p["done"]
    overall = round(ts / tw) if tw else 0
    lines.append(f"| **All** | | **{td} / {tn}** | **{overall}%** |")
    return "\n".join(lines)


def cmd_status(args) -> int:
    docs = load_manifest()
    config = load_workspace_config()
    selected_profile = (args.profile or config.get("profile", "standard")).lower()
    if selected_profile not in PROFILE_TIERS:
        print(f"Unknown profile '{selected_profile}'. Choose: {', '.join(sorted(PROFILE_TIERS))}")
        return 2
    table = progress_table(docs, selected_profile)
    print(table)
    counts = {}
    for d in docs:
        key = f"{d['applicability']} / {d['status']} / {d['profile_tier']}"
        counts[key] = counts.get(key, 0) + 1
    print("\nBy applicability / status / profile tier: " + "; ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if args.write:
        sp = workspace_paths().state
        text = read(sp)
        block = (f"<!-- PROGRESS:START -->\n{table}\n\n"
                 f"_Generated by `python bp.py status --write` on {today()}. Do not hand-edit._\n"
                 f"<!-- PROGRESS:END -->")
        new, n = re.subn(r"<!-- PROGRESS:START -->.*?<!-- PROGRESS:END -->", lambda m: block, text, flags=re.S)
        if n == 0:
            print("\n_control/STATE.md has no PROGRESS markers; nothing written.")
            return 1
        write(sp, new)
        print("\n_control/STATE.md dashboard updated.")
        idx = write_index()
        print(f"{idx.relative_to(workspace_paths().root).as_posix()} regenerated.")
    return 0


# ----------------------------------------------------------------- check
def check_mermaid(rel, text, E, W):
    for n, m in enumerate(MERMAID_RE.finditer(text), 1):
        body = m.group(1)
        lines = [l for l in body.split("\n") if l.strip() and not l.strip().startswith("%%")]
        if lines and lines[0].strip() == "---":  # mermaid frontmatter
            try:
                close = [i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"][0]
                lines = lines[close + 1:]
            except IndexError:
                pass
        if not lines:
            W(f"{rel}: mermaid block #{n} is empty")
            continue
        first = lines[0].strip().split()[0]
        if first not in KNOWN_DIAGRAMS:
            E(f"{rel}: mermaid block #{n} starts with unknown type '{first}'")
            continue
        if first in ("flowchart", "graph"):
            opens = sum(1 for l in lines if re.match(r"^\s*subgraph\b", l))
            ends = sum(1 for l in lines if re.match(r"^\s*end\s*$", l))
            if opens != ends:
                E(f"{rel}: mermaid block #{n}: {opens} 'subgraph' vs {ends} 'end'")
        if first == "sequenceDiagram":
            opens = sum(1 for l in lines if re.match(r"^\s*(alt|opt|loop|par|critical|break|rect)\b", l))
            ends = sum(1 for l in lines if re.match(r"^\s*end\s*$", l))
            if opens != ends:
                E(f"{rel}: mermaid block #{n}: {opens} block starts vs {ends} 'end'")


def scan_files():
    """Return every repository Markdown file so instructions/templates are linted too."""
    excluded_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "framework-dev"}
    files = []
    for path in workspace_paths().root.rglob("*.md"):
        rel_parts = path.relative_to(workspace_paths().root).parts
        if any(part in excluded_dirs for part in rel_parts):
            continue
        files.append(path)
    return sorted(set(files))


def project_semantic_files(files):
    """Yield configured project semantic sources; framework/control metadata is not inferred by filename."""
    config = load_workspace_config()
    rules = config.get("semantic_sources", {})
    include_roots = tuple(rules.get("include_roots", ["docs", "_control/registry"]))
    excluded_paths = set(rules.get("exclude_paths", []))
    excluded_roots = tuple(rules.get("exclude_roots", ["_framework", "_control/logs"]))
    for file_path in files:
        rel = workspace_paths().relative(file_path)
        if rel in excluded_paths or any(rel == root or rel.startswith(root.rstrip("/") + "/") for root in excluded_roots):
            continue
        if any(rel == root or rel.startswith(root.rstrip("/") + "/") for root in include_roots):
            yield file_path

def safe_document_path(relative: str) -> Path | None:
    """Resolve a manifest document path safely inside the fixed docs/ root."""
    return workspace_paths().resolve_document(relative)

def markdown_heading_anchors(text: str) -> set[str]:
    """Approximate GitHub-style heading anchors, including duplicate-heading suffixes."""
    clean_text = strip_noise(text)
    anchors = set()
    counts = {}
    for line in clean_text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = match.group(1).strip()
        heading = re.sub(r"!?(\[[^\]]*\])\([^)]*\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", heading)
        heading = heading.replace("`", "").lower()
        heading = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", heading.strip())
        if not slug:
            continue
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        anchors.add(slug if index == 0 else f"{slug}-{index}")
    anchors.update(re.findall(r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']", clean_text, flags=re.I))
    return anchors


def markdown_link_occurrences(text: str) -> tuple[list[tuple[str, int]], list[tuple[int, str]]]:
    """Collect link targets and source-offset diagnostics, including open comments."""
    prose, comment_issues = _mask_markdown_noise_with_diagnostics(text)
    occurrences, issues = inline_markdown_link_occurrences(prose)
    if comment_issues:
        issues = comment_issues[:MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE] + issues[
            :max(0, MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE - len(comment_issues))
        ]
    definitions: dict[str, tuple[str, int]] = {}
    for match in REFERENCE_DEFINITION_RE.finditer(prose):
        label = re.sub(r"\s+", " ", match.group(1).strip().lower())
        target_group = 2 if match.group(2) else 3
        target = match.group(target_group)
        if label and target:
            offset = match.start(target_group)
            if len(target) > MAX_MARKDOWN_LINK_COMPONENT_CHARS and not _is_external_markdown_target(target):
                if len(issues) < MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE:
                    issues.append((offset, f"reference link target exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character parsing limit"))
            else:
                definitions[label] = (target, offset)
    reference_occurrences, reference_issues = reference_markdown_link_occurrences(prose)
    issues.extend(reference_issues[:max(0, MAX_MARKDOWN_LINK_DIAGNOSTICS_PER_FILE - len(issues))])
    for first_label, second_label, use_offset in reference_occurrences:
        label = re.sub(r"\s+", " ", (second_label or first_label).strip().lower())
        item = definitions.get(label)
        if item is not None:
            occurrences.append(item)
    return occurrences, issues


def markdown_link_targets(text: str) -> list[str]:
    """Collect inline and reference-style Markdown targets from a prose source."""
    occurrences, _issues = markdown_link_occurrences(text)
    return [target for target, _offset in occurrences]


def markdown_link_target_exists(source: Path, target: str, manifest_paths: set[str] | None = None,
                                heading_cache: dict[Path, set[str]] | None = None):
    """Return (state, detail): exists, planned, missing or invalid.

    Filesystem and URL parsing failures are converted into bounded diagnostics;
    malformed project content must never abort the entire workspace check.
    """
    if "{{" in target or "}}" in target:
        return "exists", "template placeholder"
    try:
        split = urlsplit(target)
        if split.scheme or target.startswith("//"):
            detail = _external_markdown_target_error(target, split)
            return ("invalid", detail) if detail else ("exists", "external link")
        if len(target) > MAX_MARKDOWN_LINK_COMPONENT_CHARS:
            return "invalid", f"link target exceeds the {MAX_MARKDOWN_LINK_COMPONENT_CHARS}-character limit"
        path_part = unquote(split.path)
        anchor = unquote(split.fragment)
        if "\x00" in path_part or "\x00" in anchor:
            return "invalid", "link target contains a decoded NUL character"

        workspace_root = workspace_paths().root.resolve()
        dest = source.resolve() if not path_part else (source.parent / path_part).resolve()
        if path_part:
            try:
                dest.relative_to(workspace_root)
            except ValueError:
                return "missing", "relative link escapes the workspace root"
        try:
            dest.stat()
            destination_exists = True
        except FileNotFoundError:
            destination_exists = False
        except OSError as exc:
            if getattr(exc, "errno", None) == errno.ENAMETOOLONG:
                return "invalid", "filesystem rejected an overlong link target"
            return "invalid", f"filesystem rejected the link target ({type(exc).__name__})"

        if destination_exists:
            if anchor and dest.suffix.lower() == ".md":
                cache_key = dest.resolve()
                if heading_cache is not None:
                    known_anchors = heading_cache.get(cache_key)
                    if known_anchors is None:
                        known_anchors = markdown_heading_anchors(read(dest))
                        heading_cache[cache_key] = known_anchors
                else:
                    known_anchors = markdown_heading_anchors(read(dest))
                if anchor not in known_anchors:
                    return "missing", f"heading anchor '#{anchor}' does not exist in {dest.name}"
            return "exists", ""
        if manifest_paths is not None:
            try:
                rel_to_docs = dest.relative_to(workspace_paths().docs.resolve()).as_posix()
            except ValueError:
                rel_to_docs = ""
            if rel_to_docs and (rel_to_docs in manifest_paths or any(x.startswith(rel_to_docs.rstrip("/") + "/") for x in manifest_paths)):
                return "planned", "manifest path has not been scaffolded yet"
        return "missing", "target path does not exist"
    except (OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.ENAMETOOLONG:
            return "invalid", "filesystem rejected an overlong link target"
        return "invalid", f"invalid link target ({type(exc).__name__})"


def markdown_line_starts(text: str) -> list[int]:
    """Build line-start offsets once so many findings do not rescan prefixes."""
    return [0, *(match.end() for match in re.finditer("\n", text))]


def markdown_line_number(offset: int, line_starts: list[int]) -> int:
    """Return a one-based line number for a source offset in logarithmic time."""
    import bisect
    return bisect.bisect_right(line_starts, max(0, offset))

def _doc_ids_in_cell(value: str) -> list[str]:
    """Extract explicit document IDs from a D0.02 inventory cell."""
    return list(dict.fromkeys(re.findall(r"\bD\d+\.\d{2,}(?:\.\d{2,})*\b", value or "")))


def _split_mapping_in_cell(value: str) -> tuple[str | None, list[str]]:
    """Read an explicit `original -> child1, child2` split mapping.

    The first side must contain exactly one original ID; the second side must
    contain at least two child IDs. The function deliberately does not infer
    lineage from a list of IDs without a directional separator.
    """
    parts = re.split(r"\s*(?:→|->)\s*", value or "", maxsplit=1)
    if len(parts) != 2:
        return None, []
    originals = _doc_ids_in_cell(parts[0])
    children = _doc_ids_in_cell(parts[1])
    if len(originals) != 1 or len(children) < 2:
        return None, children
    # Reject additional arrows or IDs before/after the recognized mapping.
    if re.search(r"(?:→|->)", parts[1]):
        return None, children
    return originals[0], children


def architecture_disposition_findings(docs: list[dict], by_id: dict) -> tuple[list[str], list[str]]:
    """Compare an approved project D0.02 inventory with the operational manifest.

    This is project-agnostic: the architecture document ID is workspace-configurable,
    and only IDs/dispositions explicitly present in that project's D0.02 are evaluated.
    No file or owner-controlled record is modified.
    """
    errors, warnings = [], []
    config = load_workspace_config()
    architecture_id = config.get("architecture_document_id", "D0.02")
    arch = by_id.get(architecture_id)
    if not arch:
        return errors, warnings
    arch_path = safe_document_path(arch.get("path", ""))
    if not arch_path or not arch_path.exists():
        return errors, warnings
    raw = read(arch_path)
    if arch.get("status") != "approved":
        warnings.append(f"ARCH-CONFORMANCE: {architecture_id} is '{arch.get('status')}', not approved; disposition comparison is advisory until owner approval")
        return errors, warnings
    approval_issue = approval_problem(arch, arch_path, load_approvals())
    if approval_issue:
        warnings.append(f"ARCH-CONFORMANCE: {architecture_id} claims approved but its approval evidence is not valid ({approval_issue}); disposition comparison is advisory")
        return errors, warnings

    tables = parse_tables(strip_code(raw))
    inventory = None
    for header, rows in tables:
        h = [re.sub(r"\s+", " ", x.strip().lower()) for x in header]
        disposition_ix = next((i for i, x in enumerate(h) if x.startswith("disposition")), None)
        canonical_ix = next((i for i, x in enumerate(h) if x.startswith("proposed canonical document")), None)
        if disposition_ix is not None and canonical_ix is not None:
            inventory = (h, rows, disposition_ix, canonical_ix)
            break
    if inventory is None:
        errors.append(f"ARCH-CONFORMANCE: approved {architecture_id} has no recognizable document inventory table (requires Disposition and Proposed canonical document(s) columns)")
        return errors, warnings

    _, rows, disposition_ix, canonical_ix = inventory
    expected_by_id: dict[str, tuple[str, str, str]] = {}
    represented_ids: set[str] = set()
    recognized = {"core", "core (light)", "core-light", "core light", "conditional", "excluded", "merged", "split", "new", "deferred"}
    for row_no, row in enumerate(rows, start=1):
        if max(disposition_ix, canonical_ix) >= len(row):
            errors.append(f"ARCH-CONFORMANCE: {architecture_id} inventory row {row_no} is incomplete; disposition and canonical document ID must be explicit")
            continue
        disposition_raw = clean(row[disposition_ix]).lower()
        disposition = re.sub(r"\s+", " ", disposition_raw)
        if disposition in {"core-light", "core light"}:
            disposition = "core (light)"
        canonical_cell = row[canonical_ix]
        ids = _doc_ids_in_cell(canonical_cell)
        represented_ids.update(ids)
        split_original, split_children = (None, [])
        if disposition == "split":
            split_original, split_children = _split_mapping_in_cell(canonical_cell)
            if split_original is None:
                errors.append(
                    f"ARCH-CONFORMANCE: split disposition in {architecture_id} row {row_no} "
                    "must use an explicit directional mapping: original ID → at least two child IDs"
                )
            elif set(ids) != {split_original, *split_children}:
                errors.append(
                    f"ARCH-CONFORMANCE: split disposition in {architecture_id} row {row_no} "
                    "contains document IDs outside its explicit original/child mapping"
                )
        # In a merged mapping, the first ID is the retired/source record; subsequent
        # IDs identify the host and must not inherit the source disposition.
        if disposition == "merged" and ids:
            ids = ids[:1]
        if not disposition or disposition in ("—", "-"):
            errors.append(f"ARCH-CONFORMANCE: {architecture_id} inventory row {row_no} has no disposition; an approved inventory must classify every document row")
            continue
        if disposition not in recognized:
            errors.append(f"ARCH-CONFORMANCE: {architecture_id} inventory row {row_no} uses unrecognized disposition '{disposition_raw}'; explicit mapping required")
            continue
        if not ids:
            if disposition != "excluded":
                errors.append(f"ARCH-CONFORMANCE: {architecture_id} inventory row {row_no} ({disposition}) names no canonical document ID")
            continue
        for did in ids:
            if did in expected_by_id:
                prior = expected_by_id[did]
                if prior[0] != disposition:
                    errors.append(f"ARCH-CONFORMANCE: {did} has conflicting dispositions '{prior[0]}' and '{disposition}' in {architecture_id}")
                # Repeated references with the same disposition are legitimate when
                # multiple catalog concerns share one canonical document.
                continue
            expected_by_id[did] = (disposition, row[canonical_ix], row_no)

    for did, (disposition, canonical_cell, row_no) in expected_by_id.items():
        actual = by_id.get(did)
        if actual is None:
            errors.append(f"ARCH-CONFORMANCE: {did} is declared in {architecture_id} row {row_no} ({disposition}) but is missing from MANIFEST.md")
            continue
        applicability = actual.get("applicability", "")
        expected = {"core": "active", "core (light)": "active", "conditional": "conditional",
                    "excluded": "excluded", "deferred": "deferred"}.get(disposition)
        if expected and applicability != expected:
            errors.append(f"ARCH-CONFORMANCE: {did} is '{disposition}' in approved {architecture_id} but manifest applicability is '{applicability}' (expected '{expected}')")
        elif disposition == "merged":
            if applicability != "excluded":
                errors.append(f"ARCH-CONFORMANCE: merged document {did} must be excluded in MANIFEST.md (currently '{applicability}')")
            hosts = [x for x in _doc_ids_in_cell(canonical_cell) if x != did]
            rationale = actual.get("applicability_rationale", "")
            if not hosts or not any(host in rationale for host in hosts):
                errors.append(f"ARCH-CONFORMANCE: merged document {did} must identify its host document in the D0.02 canonical mapping and manifest applicability rationale")
            elif not any(host in by_id for host in hosts):
                errors.append(f"ARCH-CONFORMANCE: merged document {did} names a host that is missing from MANIFEST.md")
            elif not any(host in by_id and by_id[host].get("applicability") == "active" for host in hosts):
                errors.append(f"ARCH-CONFORMANCE: merged document {did} must point to an active host document")
        elif disposition == "new":
            # Applicability is explicitly recorded in the manifest; it is not inferred
            # from the word New or from an unrelated row label.
            if actual.get("applicability") not in {"active", "conditional", "excluded", "deferred"}:
                errors.append(f"ARCH-CONFORMANCE: new document {did} requires an explicit valid manifest applicability")
        elif disposition == "split":
            # Every ID in a valid directional mapping (one original, >=2 children)
            # must resolve to a manifest row. Applicability remains owner-defined for
            # each ID; the validator must not guess whether the original is retained.
            if actual.get("applicability") not in {"active", "conditional", "excluded", "deferred"}:
                errors.append(f"ARCH-CONFORMANCE: split document {did} requires an explicit valid manifest applicability")

    for did, actual in by_id.items():
        if actual.get("applicability") == "active" and did not in represented_ids:
            errors.append(f"ARCH-CONFORMANCE: active manifest document {did} is not represented by an explicit canonical document ID in approved {architecture_id}; add it to the exhaustive inventory or record an approved, explicit system/bootstrap exemption")
    return errors, warnings


def dependency_applicability_findings(docs: list[dict], by_id: dict) -> list[str]:
    """Return invalid active-consumer edges to non-active dependency targets."""
    findings = []
    for consumer in docs:
        if consumer.get("applicability") != "active":
            continue
        for dep_id in consumer.get("depends", []):
            target = by_id.get(dep_id)
            if target and target.get("applicability") != "active":
                findings.append(
                    f"DEPENDENCY-APPLICABILITY: active document {consumer['id']} depends on {dep_id}, "
                    f"whose applicability is '{target.get('applicability')}'; revise the edge. "
                    "This version does not support dependency exceptions"
                )
    return findings


def _state_section(text: str, heading: str) -> str:
    """Return the body of an exact Markdown heading through the next same/higher heading."""
    lines = text.splitlines()
    wanted = heading.strip().lower()
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match or match.group(2).strip().lower() != wanted:
            continue
        level = len(match.group(1))
        body = []
        for following in lines[index + 1:]:
            next_heading = re.match(r"^(#{1,6})\s+", following)
            if next_heading and len(next_heading.group(1)) <= level:
                break
            body.append(following)
        return "\n".join(body).strip()
    return ""


def _version_parts(value: str) -> tuple[int, ...] | None:
    """Parse a dotted numeric document version for conservative ordering."""
    if not re.fullmatch(r"\d+(?:\.\d+){1,3}", value.strip()):
        return None
    return tuple(int(part) for part in value.strip().split("."))


def _explicit_doc_claims(text: str) -> list[dict[str, str]]:
    """Extract explicit document ID/version/status claims within one prose paragraph."""
    statuses = "not-started|interviewing|drafting|in-review|approved|needs-revision|superseded|expanded"
    claims = []
    for paragraph in strip_noise(text).split("\n\n"):
        matches = list(re.finditer(r"\b(D\d+\.\d{2,}(?:\.\d{2,})*)\b", paragraph))
        for index, match in enumerate(matches):
            tail_end = matches[index + 1].start() if index + 1 < len(matches) else len(paragraph)
            tail = paragraph[match.end():tail_end]
            version = re.search(r"\bv(\d+(?:\.\d+){1,3})\b", tail, re.I)
            status = re.search(
                rf"(?:\bstatus\s*[:=]\s*|\(\s*|\s+[—|]\s*|\b(?:is|currently|remains)\s+)({statuses})\b",
                tail, re.I)
            line_start = paragraph.rfind("\n", 0, match.start()) + 1
            line_end = paragraph.find("\n", match.end())
            if line_end < 0:
                line_end = len(paragraph)
            claims.append({
                "id": match.group(1),
                "version": version.group(1) if version else "",
                "status": status.group(1).lower() if status else "",
                "line": paragraph[line_start:line_end].strip(),
                "context": tail.strip(),
            })
    return claims


def _session_number_from_ref(value: str) -> int | None:
    match = re.search(r"\bsession-(\d+)\b", value, re.I)
    return int(match.group(1)) if match else None


def _session_exists(session_dir: Path, reference: str) -> bool:
    """Match the numeric session identity exactly (session-001 must not match 0010)."""
    wanted = _session_number_from_ref(reference)
    if wanted is None or not session_dir.exists():
        return False
    for path in session_dir.glob("session-*.md"):
        match = re.match(r"session-(\d+)(?:-|$)", path.stem, re.I)
        if match and int(match.group(1)) == wanted:
            return True
    return False


def _decision_registry_has_accepted(decisions_text: str) -> bool:
    for header, rows in parse_tables(strip_code(decisions_text)):
        columns = [item.strip().lower() for item in header]
        if "id" not in columns or "status" not in columns:
            continue
        id_index, status_index = columns.index("id"), columns.index("status")
        for row in rows:
            if len(row) > max(id_index, status_index):
                if re.fullmatch(r"ADR-\d{2,4}", clean(row[id_index]), re.I) and clean(row[status_index]).lower() == "accepted":
                    return True
    return False


def _progress_block_is_stale(state_text: str, docs: list[dict]) -> tuple[bool, str]:
    """Compare the generated STATE progress block without rewriting surrounding prose."""
    match = re.search(r"<!-- PROGRESS:START -->\s*(.*?)\s*<!-- PROGRESS:END -->", state_text, re.S)
    if not match:
        return True, "STATE.md has no PROGRESS markers"
    actual = re.sub(r"^_Generated by `python bp\.py status --write` on .*?\. Do not hand-edit\._\s*$", "",
                    match.group(1), flags=re.M).strip()
    expected = progress_table(docs, None).strip()
    return actual != expected, "STATE.md generated progress block is stale; run `python bp.py status --write`"


def state_reconciliation_findings() -> list[tuple[str, str]]:
    """Read-only reconciliation of explicit STATE claims against structured records."""
    findings: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(severity: str, message: str) -> None:
        key = (severity, message)
        if key not in seen:
            seen.add(key)
            findings.append(key)

    ws = workspace_paths()
    state_path = ws.state
    if not state_path.exists():
        return [("error", "STATE-AUDIT: _control/STATE.md is missing")]
    state_text = read(state_path)
    docs = load_manifest()
    by_id = {d["id"]: d for d in docs}
    approvals = load_approvals()
    decisions_path = ws.decisions
    decisions_text = read(decisions_path) if decisions_path.exists() else ""

    # Parse the compact STATE dashboard table without attempting to interpret prose.
    state_fields = {}
    for header, rows in parse_tables(strip_code(state_text)):
        h = [x.strip().lower() for x in header]
        if "field" in h and "value" in h:
            fi, vi = h.index("field"), h.index("value")
            for row in rows:
                if len(row) > max(fi, vi):
                    state_fields[clean(row[fi]).lower()] = clean(row[vi])
            break

    # STATE-001/002: current identity plus explicit version references in scoped fields.
    current_doc = state_fields.get("current document", "")
    scoped_version_text = "\n\n".join([
        current_doc,
        state_fields.get("document step", ""),
        _state_section(state_text, "Awaiting the owner"),
        _state_section(state_text, "Next action"),
    ])
    current_claims = _explicit_doc_claims(current_doc)
    if current_doc and current_doc.lower() not in {"—", "-", "none", "not set"} and not current_claims:
        add("warning", f"STATE-AUDIT STATE-001: current document field '{current_doc}' has no explicit manifest document ID")

    for claim in _explicit_doc_claims(scoped_version_text):
        did = claim["id"]
        d = by_id.get(did)
        if not d:
            add("warning", f"STATE-AUDIT STATE-008: referenced document {did} is not present in MANIFEST.md")
            continue
        version = claim["version"]
        if version and version != d["version"]:
            label = "stale" if (_version_parts(version) is not None and _version_parts(d["version"]) is not None
                                 and _version_parts(version) < _version_parts(d["version"])) else "different"
            code = "STATE-002" if label == "stale" else "STATE-001/002"
            if claim["line"] == current_doc:
                message = f"current document {did} says v{version} but manifest records v{d['version']}"
            else:
                message = f"explicit reference to {did} v{version} is {label}; manifest records v{d['version']} (source line: {claim['line']})"
            add("warning", f"STATE-AUDIT {code}: {message}")
        status = claim["status"]
        if status and status != d["status"]:
            add("warning", f"STATE-AUDIT STATE-001: explicit {did} status '{status}' differs from manifest status '{d['status']}' (source line: {claim['line']})")

    # For the current document, manifest and front matter are expected to agree.
    if current_claims:
        did = current_claims[0]["id"]
        d = by_id.get(did)
        if d:
            fm_path = safe_document_path(d["path"])
            if fm_path and fm_path.exists():
                fm = front_matter(read(fm_path)) or {}
                if fm.get("version") != d["version"] or fm.get("status") != d["status"]:
                    add("error", f"STATE-AUDIT STATE-001: {did} manifest/front matter disagree; resolve structural validation errors first")

    # Session inventory: use numeric ordering, not lexicographic filename order.
    session_dir = ws.sessions
    sessions = sorted(session_dir.glob("session-*.md")) if session_dir.exists() else []
    def session_number(path: Path) -> int:
        return _session_number_from_ref(path.stem) or -1
    latest = max(sessions, key=session_number) if sessions else None

    # STATE-003: the latest handoff must resolve and must not trail a newer available session.
    latest_handoff = state_fields.get("latest handoff", "")
    handoff_refs = re.findall(r"session-\d+", latest_handoff, re.I)
    for ref in handoff_refs:
        if not _session_exists(session_dir, ref):
            add("warning", f"STATE-AUDIT STATE-003/008: latest handoff references missing session {ref}")
    if latest and handoff_refs:
        handoff_numbers = [_session_number_from_ref(ref) for ref in handoff_refs]
        if max(n for n in handoff_numbers if n is not None) < session_number(latest):
            add("warning", f"STATE-AUDIT STATE-003: STATE latest handoff is older than available latest session {latest.stem}")

    # STATE-004: compare Last updated with the declared last clean checkpoint. A
    # reasoned exception is allowed only when explicitly recorded in the field.
    last_updated = state_fields.get("last updated", "")
    clean_checkpoint = state_fields.get("last clean checkpoint", "")
    updated_number = _session_number_from_ref(last_updated)
    checkpoint_number = _session_number_from_ref(clean_checkpoint)
    reason_match = re.search(r"(?:exception|reason)\s*:\s*(.{8,})", last_updated, re.I)
    if updated_number is not None and checkpoint_number is not None and updated_number < checkpoint_number and not reason_match:
        add("warning", f"STATE-AUDIT STATE-004: Last updated references session-{updated_number:03d}, older than last clean checkpoint session-{checkpoint_number:03d}; add an explicit reason if intentional")
    if updated_number is not None and latest and updated_number < session_number(latest) and not reason_match:
        add("warning", f"STATE-AUDIT STATE-004: STATE last-updated reference is older than available latest session {latest.stem}; add an explicit reason if STATE was intentionally unchanged")
    if reason_match and reason_match.group(1).strip().lower() in {"n/a", "none", "tbd", "not applicable"}:
        add("warning", "STATE-AUDIT STATE-004: the Last updated exception/reason marker has no meaningful explanation")

    # STATE-005: inspect structured ADR status, not an arbitrary occurrence of 'none yet'.
    key_decisions = _state_section(state_text, "Key decisions")
    says_no_decisions = bool(re.search(r"\b(?:none yet|no decisions|no accepted decisions)\b", key_decisions, re.I))
    if says_no_decisions and _decision_registry_has_accepted(decisions_text):
        add("warning", "STATE-AUDIT STATE-005: STATE says no key decisions exist, but DECISIONS.md contains an accepted ADR")

    # STATE-006: compare exact document/version claims with the authoritative approval row.
    approval_scope = "\n\n".join([current_doc, _state_section(state_text, "Awaiting the owner"),
                                  _state_section(state_text, "Next action")])
    approval_claims = _explicit_doc_claims(approval_scope)
    awaiting_pattern = re.compile(r"\b(?:awaiting approval|awaiting the owner's approval|pending (?:owner )?approval|ready for owner approval)\b", re.I)
    for claim in approval_claims:
        did, version = claim["id"], claim["version"]
        if not version:
            continue
        d = by_id.get(did)
        rec = approvals.get(did)
        line = claim["line"]
        context = claim.get("context", line)
        awaiting = bool(awaiting_pattern.search(context))
        says_approved = claim["status"] == "approved" or bool(
            re.search(r"\bapproved\b", context, re.I)
            and not re.search(r"\b(?:not|never|not yet)\s+approved\b", context, re.I))
        if awaiting and rec and rec.get("version") == version and d:
            approval_path = safe_document_path(d.get("path", ""))
            approval_issue = approval_problem(d, approval_path, approvals)
            if approval_issue is None:
                add("warning", f"STATE-AUDIT STATE-006: STATE says {did} v{version} is awaiting approval, but APPROVALS.md contains a valid approval record for that exact version")
            else:
                add("warning", f"STATE-AUDIT STATE-006: STATE says {did} v{version} is awaiting approval and APPROVALS.md has a same-version row, but its approval fingerprint is not valid ({approval_issue}); do not treat the row as valid approval")
        if says_approved and d and version == d["version"] and d["status"] != "approved":
            add("warning", f"STATE-AUDIT STATE-006: STATE describes {did} v{version} as approved, but manifest status is '{d['status']}'")

    # STATE-007: missing actionable content or incompatible explicit status claims.
    next_action = _state_section(state_text, "Next action")
    normalized_next = strip_noise(next_action).strip()
    if not normalized_next or re.fullmatch(r"(?:_?\s*(?:tbd|none|not set|to be determined)\s*_?|\(none\))\.?", normalized_next, re.I):
        add("warning", "STATE-AUDIT STATE-007: Next action section is missing or contains only a placeholder; owner/agent review is required")
    next_claims = _explicit_doc_claims(next_action)
    claims_by_doc: dict[str, set[str]] = {}
    for claim in next_claims:
        if claim["status"]:
            claims_by_doc.setdefault(claim["id"], set()).add(claim["status"])
        d = by_id.get(claim["id"])
        if d and claim["status"] and claim["status"] != d["status"]:
            add("warning", f"STATE-AUDIT STATE-007: Next action explicitly describes {claim['id']} as '{claim['status']}', but manifest status is '{d['status']}'; review the instruction")
    for did, values in claims_by_doc.items():
        if len(values) > 1:
            add("warning", f"STATE-AUDIT STATE-007: Next action contains contradictory status claims for {did}: {', '.join(sorted(values))}")

    # STATE-008: verify local Markdown links and explicit document/session references
    # in project control records. Unscaffolded manifest documents remain valid/planned.
    evidence_sources = [state_path, ws.approvals, ws.decisions]
    if session_dir.exists():
        evidence_sources.extend(sorted(session_dir.glob("session-*.md")))
    manifest_paths = {d["path"].rstrip("/") for d in docs if d.get("path")}
    heading_cache = {}
    known_session_refs: set[str] = set()
    known_doc_refs: set[str] = set()
    for source in evidence_sources:
        if not source.exists() or not source.is_file():
            continue
        raw = read(source)
        link_occurrences, link_issues = markdown_link_occurrences(raw)
        line_starts = markdown_line_starts(raw)
        for offset, detail in link_issues:
            line = markdown_line_number(offset, line_starts)
            add("warning", f"STATE-AUDIT STATE-008: invalid Markdown link in {source.relative_to(ws.root).as_posix()}:{line} ({detail})")
        for target, offset in link_occurrences:
            if "{{" in target or "}}" in target:
                continue
            link_state, detail = markdown_link_target_exists(source, target, manifest_paths, heading_cache)
            line = markdown_line_number(offset, line_starts)
            if link_state == "invalid":
                add("warning", f"STATE-AUDIT STATE-008: invalid link target in {source.relative_to(ws.root).as_posix()}:{line} ({detail})")
            elif link_state == "missing":
                add("warning", f"STATE-AUDIT STATE-008: broken local reference in {source.relative_to(ws.root).as_posix()}:{line} -> {target[:160]} ({detail})")
        for ref in re.findall(r"\bsession-\d+\b", strip_noise(raw), re.I):
            known_session_refs.add(ref)
        for did in re.findall(r"\bD\d+\.\d{2,}(?:\.\d{2,})*\b", strip_noise(raw)):
            known_doc_refs.add(did)
    for ref in sorted(known_session_refs, key=str.lower):
        if not _session_exists(session_dir, ref):
            add("warning", f"STATE-AUDIT STATE-008: control evidence references missing session {ref}")
    for did in sorted(known_doc_refs):
        if did not in by_id:
            add("warning", f"STATE-AUDIT STATE-008: control evidence references document {did}, which is not in MANIFEST.md")

    # STATE-009: report generated-block drift; never regenerate from an audit.
    index_path = getattr(ws, "index", None)
    if index_path is not None and index_is_stale(index_path):
        add("warning", "STATE-AUDIT STATE-009: _control/registry/INDEX.md is missing or stale; run `python bp.py index`")
    progress_stale, progress_message = _progress_block_is_stale(state_text, docs)
    if progress_stale:
        add("warning", f"STATE-AUDIT STATE-009: {progress_message}; run `python bp.py status --write`")

    return findings


def cmd_audit_state(args) -> int:
    """Emit a read-only state reconciliation report."""
    findings = state_reconciliation_findings()
    errors = [m for s, m in findings if s == "error"]
    warnings = [m for s, m in findings if s == "warning"]
    print("Project state reconciliation (read-only)")
    print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
    for message in errors + warnings:
        print(f"{'ERROR' if message in errors else 'WARN'}: {message}")
    print("No files were modified.")
    return 1 if errors or (args.strict and warnings) else 0


def cmd_check(args) -> int:
    errors, warns = [], []
    E, W = errors.append, warns.append
    strict = args.strict or args.gate is not None
    docs = load_manifest()
    config = load_workspace_config()
    phases = load_phases()
    by_id = {}
    for first, second in workspace_paths().case_collisions():
        E(f"PATH001: case/Unicode-normalization collision between '{first}' and '{second}'")
    for severity, message in validate_framework_manifest(workspace_paths()):
        # Drift is advisory in ordinary checks and blocks strict validation.
        (E if severity == "error" or strict else W)(f"FRAMEWORK: {message}")
    for severity, message in validate_gitattributes(workspace_paths()):
        (E if strict else W)(f"GIT: {message}")
    for severity, message in validate_workspace_structure(workspace_paths(), config):
        (E if severity == "error" or strict else W)(f"STRUCTURE: {message}")
    try:
        selected_profile = str(args.profile or config.get("profile", "standard")).lower()
        if selected_profile not in PROFILE_TIERS:
            E(f"WORKSPACE: invalid default profile '{selected_profile}' (choose {', '.join(sorted(PROFILE_TIERS))})")
        ranks = config.get("profile_ranks", {})
        missing_ranks = PROFILE_TIERS - set(ranks)
        if missing_ranks:
            E("WORKSPACE: profile_ranks is missing " + ", ".join(sorted(missing_ranks)))
        rank_values = [ranks.get(name) for name in ("lite", "standard", "exhaustive")]
        if any(not isinstance(value, int) for value in rank_values):
            E("WORKSPACE: profile ranks for lite/standard/exhaustive must be integers")
        elif not (rank_values[0] < rank_values[1] < rank_values[2]):
            E("WORKSPACE: profile ranks must increase strictly lite < standard < exhaustive")
        phase_path = workspace_paths().phases
        if not phase_path.exists():
            E(f"WORKSPACE: phase registry missing at {phase_path.relative_to(workspace_paths().root).as_posix()}")
        else:
            seen_phase_rows = set()
            for header, rows in parse_tables(strip_code(read(phase_path))):
                lower = [c.strip().lower() for c in header]
                if "phase" not in lower or "name" not in lower:
                    continue
                iph, inm = lower.index("phase"), lower.index("name")
                for row in rows:
                    if len(row) <= max(iph, inm):
                        continue
                    try:
                        nphase = int(clean(row[iph]))
                    except ValueError:
                        E(f"PHASES: invalid phase number '{row[iph]}'")
                        continue
                    if nphase in seen_phase_rows:
                        E(f"PHASES: duplicate phase number {nphase}")
                    seen_phase_rows.add(nphase)
                    if not clean(row[inm]):
                        E(f"PHASES: phase {nphase} has an empty name")
    except ValueError as exc:
        E(str(exc))
    manifest_path = workspace_paths().manifest
    state_path = workspace_paths().state
    doc_root = workspace_paths().docs.resolve()

    # --- manifest schema and sanity
    try:
        manifest_text = read(manifest_path)
        manifest_header = next((split_row(line) for line in manifest_text.splitlines() if line.lstrip().startswith("|") and "Doc ID" in split_row(line) and "Applicability" in split_row(line)), [])
        required_manifest_columns = {"Doc ID", "Path", "Phase", "Applicability", "Applicability rationale", "Profile tier", "Size", "Status", "Depends on", "Title", "Maturity", "Version", "Last updated"}
        missing_columns = sorted(required_manifest_columns - set(manifest_header))
        if missing_columns:
            E("MANIFEST: missing required column(s): " + ", ".join(missing_columns))
    except OSError as exc:
        E(f"MANIFEST: cannot read {manifest_path}: {exc}")
    for d in docs:
        if d["id"] in by_id:
            E(f"MANIFEST: duplicate doc id {d['id']}")
        by_id[d["id"]] = d
        if not DOC_ID_RE.match(d["id"]):
            E(f"MANIFEST: invalid doc id '{d['id']}'")
        elif doc_phase(d["id"]) != d["phase"]:
            E(f"MANIFEST: {d['id']} phase prefix does not match its phase number")
        if d["status"] not in STATUSES:
            if d["status"] in LEGACY_STATUSES:
                E(f"MANIFEST: {d['id']} uses legacy workflow status 'excluded'; set applicability=excluded and choose an appropriate workflow status")
            else:
                E(f"MANIFEST: {d['id']} has invalid status '{d['status']}'")
        if d["applicability"] not in APPLICABILITY_VALUES:
            E(f"MANIFEST: {d['id']} has invalid applicability '{d['applicability']}' (use {', '.join(sorted(APPLICABILITY_VALUES))})")
        if d["applicability"] != "active" and not d["applicability_rationale"]:
            E(f"MANIFEST: {d['id']} is {d['applicability']} but has no applicability rationale")
        if d["profile_tier"] not in PROFILE_TIERS or profile_rank(d["profile_tier"], config) <= 0:
            E(f"MANIFEST: {d['id']} has invalid profile tier '{d['profile_tier']}'")
        if d["size"] not in SIZE_W:
            W(f"MANIFEST: {d['id']} has unknown size '{d['size']}' (using M)")
        if d["maturity"] not in MATURITIES:
            E(f"MANIFEST: {d['id']} has invalid maturity '{d['maturity']}' (use outline, working or detailed)")
        if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", d["version"]):
            E(f"MANIFEST: {d['id']} has invalid version '{d['version']}'")
        try:
            datetime.date.fromisoformat(d["last_updated"])
        except ValueError:
            E(f"MANIFEST: {d['id']} has invalid last-updated date '{d['last_updated']}'")
        if not d["path"]:
            E(f"MANIFEST: {d['id']} has no path")
        elif "\\" in d["path"] or safe_document_path(d["path"]) is None:
            E(f"MANIFEST: {d['id']} has unsafe path '{d['path']}' (use relative POSIX paths contained within docs/)")
        if d["phase"] not in phases:
            E(f"MANIFEST: {d['id']} uses phase {d['phase']} which is not registered in {workspace_paths().relative(workspace_paths().phases)}")
    for index_id in config.get("id_index_document_ids", ["D7.04"]):
        if index_id not in by_id:
            E(f"WORKSPACE: configured ID-index document '{index_id}' is not present in the manifest")

    for d in docs:
        for dep in d["depends"]:
            if dep not in by_id:
                E(f"MANIFEST: {d['id']} depends on unknown document {dep}")
            elif profile_rank(by_id[dep]["profile_tier"], config) > profile_rank(d["profile_tier"], config):
                E(f"PROFILE: {d['id']} is tier '{d['profile_tier']}' but content-depends on deeper-tier {dep} ('{by_id[dep]['profile_tier']}'); raise the consumer tier or change the dependency")
    # Active consumers may not rely on documents that are not currently applicable.
    for message in dependency_applicability_findings(docs, by_id):
        (E if strict else W)(message)

    # Approved D0.02 is the project-specific architecture source for disposition conformance.
    arch_errors, arch_warnings = architecture_disposition_findings(docs, by_id)
    errors.extend(arch_errors)
    # Draft/in-review architecture drift is explicitly advisory, including in
    # strict mode. Findings against an approved architecture are returned as
    # errors by architecture_disposition_findings when they are blocking.
    for message in arch_warnings:
        W(message)

    state = {}

    def visit(n, stack):
        if state.get(n) == 1:
            E("MANIFEST: dependency cycle " + " -> ".join(stack + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in by_id[n]["depends"]:
            if m in by_id:
                visit(m, stack + [n])
        state[n] = 2
    for n in list(by_id):
        visit(n, [])

    # --- approval records (owner evidence and metadata-bound SHA-256 fingerprints)
    approvals = load_approvals()
    approval_path = workspace_paths().approvals
    if not approval_path.exists():
        E(f"WORKSPACE: approval registry missing at {approval_path.relative_to(workspace_paths().root).as_posix()}")

    # --- document files vs manifest
    path_status = {}
    all_manifest_paths = set()
    seen_paths = {}
    for d in docs:
        normalized_path = d["path"].rstrip("/")
        if normalized_path:
            if normalized_path in seen_paths:
                E(f"MANIFEST: duplicate document path '{normalized_path}' used by {seen_paths[normalized_path]} and {d['id']}")
            else:
                seen_paths[normalized_path] = d["id"]
    for d in docs:
        p = d["path"]
        all_manifest_paths.add(p.rstrip("/"))
        if p.endswith("/") or d["status"] in SKIP:
            continue
        safe_path = safe_document_path(p)
        if safe_path is None:
            continue
        path_status[p] = d["status"]
        fp = safe_path
        if not fp.exists():
            if d["status"] != "not-started" and d["applicability"] not in ("deferred", "excluded"):
                E(f"{d['id']}: status '{d['status']}' but file missing: docs/{p}")
            continue
        fm = front_matter(read(fp))
        if fm is None:
            E(f"docs/{p}: missing front matter")
            continue
        for k in REQUIRED_FM:
            if k not in fm:
                E(f"docs/{p}: front matter missing '{k}'")
        comparisons = {
            "doc_id": d["id"],
            "title": d["title"],
            "phase": str(d["phase"]),
            "status": d["status"],
            "maturity": d["maturity"],
            "version": d["version"],
            "last_updated": d["last_updated"],
            "applicability": d["applicability"],
            "profile_tier": d["profile_tier"],
        }
        for field, expected in comparisons.items():
            if field in fm and fm[field] != expected:
                E(f"docs/{p}: front-matter {field} '{fm[field]}' != manifest '{expected}'")
        try:
            datetime.date.fromisoformat(fm.get("last_updated", ""))
        except ValueError:
            E(f"docs/{p}: last_updated must be a valid ISO date (YYYY-MM-DD)")
        if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", fm.get("version", "")):
            E(f"docs/{p}: version must be numeric semantic form such as 0.1 or 1.0")
        if d["status"] in ("in-review", "approved") and not fm.get("summary"):
            E(f"docs/{p}: summary is empty but status is {d['status']}")
        if d["status"] == "approved" and fm.get("version", "").startswith("0."):
            W(f"docs/{p}: approved but version is {fm.get('version')} (expected 1.0 or higher)")
        deps_fm = parse_list(fm.get("depends_on", ""))
        if sorted(deps_fm) != sorted(d["depends"]):
            E(f"docs/{p}: front-matter depends_on {deps_fm} differs from manifest {d['depends']}")
        if fm.get("applicability_rationale", "") != d["applicability_rationale"]:
            E(f"docs/{p}: front-matter applicability_rationale does not match manifest")
        if d["status"] == "approved":
            problem = approval_problem(d, fp, approvals)
            if problem:
                E(f"{d['id']}: {problem}")

    # --- catalog template mapping validation
    catalog_for_templates = load_catalog()
    configured_template_root = workspace_paths().templates
    for d in docs:
        exact_catalog_row = catalog_for_templates.get(d["id"])
        catalog_key = d["id"] if exact_catalog_row else ".".join(d["id"].split(".")[:2])
        cat_row = exact_catalog_row or catalog_for_templates.get(catalog_key, {})
        if not cat_row:
            E(f"CATALOG: {d['id']} has no document-catalog entry; add its checklist and template mapping")
        elif exact_catalog_row:
            catalog_dependencies = parse_list(cat_row.get("depends on", ""))
            if sorted(catalog_dependencies) != sorted(d["depends"]):
                E(f"CATALOG: {d['id']} content dependencies {catalog_dependencies} differ from manifest {d['depends']}")
            catalog_path = (cat_row.get("path", "") or "").strip()
            if catalog_path != d["path"]:
                E(f"CATALOG: {d['id']} path '{catalog_path}' differs from manifest path '{d['path']}'")
            catalog_title = (cat_row.get("title", "") or "").strip()
            if catalog_title != d["title"]:
                E(f"CATALOG: {d['id']} title '{catalog_title}' differs from manifest title '{d['title']}'")
        else:
            family_path = (cat_row.get("path", "") or "").strip()
            if family_path and family_path.endswith("/") and not d["path"].startswith(family_path):
                E(f"CATALOG: child document {d['id']} path '{d['path']}' is outside repeatable family path '{family_path}'")
        template_name = (cat_row.get("template", "") or "").strip()
        if template_name:
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", template_name):
                E(f"CATALOG: invalid template mapping '{template_name}' for {d['id']}")
            elif not (configured_template_root / f"{template_name}.md").exists():
                E(f"CATALOG: template '{template_name}' for {d['id']} missing at {configured_template_root.relative_to(workspace_paths().root).as_posix()}/{template_name}.md")

    # --- adaptive architecture document content: enforce when it enters review/approval
    architecture_doc_id = config.get("architecture_document_id", "D0.02")
    arch_doc = by_id.get(architecture_doc_id)
    if arch_doc and arch_doc["status"] in ("in-review", "approved") and not arch_doc["path"].endswith("/"):
        arch_path = safe_document_path(arch_doc["path"])
        if arch_path and arch_path.exists():
            arch_text = read(arch_path)
            for heading in ARCHITECTURE_REQUIRED_HEADINGS:
                if heading not in arch_text:
                    E(f"{architecture_doc_id}: adaptive architecture is {arch_doc['status']} but required section is missing: {heading}")
        else:
            # The normal missing-file check above will also describe the path; this message explains why it matters.
            E(f"{architecture_doc_id}: cannot review/approve the adaptive documentation architecture because docs/{arch_doc['path']} is missing")

    # --- orphans
    if workspace_paths().docs.exists():
        for f in workspace_paths().docs.rglob("*.md"):
            rel = f.relative_to(workspace_paths().docs).as_posix()
            if rel == "README.md" or "/adr/" in "/" + rel or rel.startswith("99-appendix/"):
                continue
            if rel not in all_manifest_paths:
                W(f"docs/{rel}: not listed in _control/registry/MANIFEST.md; map project documentation in the manifest or move explanatory Markdown to docs/99-appendix/ (docs/_assets/ is for non-Markdown assets)")

    # --- dependency status order
    for d in docs:
        if d["applicability"] not in ("active", "conditional"):
            continue
        if d["status"] in ("in-review", "approved"):
            for dep in d["depends"]:
                dd = by_id.get(dep)
                if not dd or dd["applicability"] != "active" or dd["status"] in SKIP:
                    continue
                if d["status"] == "approved" and dd["status"] != "approved":
                    E(f"{d['id']} is approved but depends on {dep}, which is '{dd['status']}'; its approval must be reviewed after an upstream change")
                elif RANK.get(dd["status"], 0) < RANK[d["status"]]:
                    W(f"{d['id']} is {d['status']} but content-depends on {dep} which is {dd['status']}")
    nr = [d["id"] for d in docs if d["status"] == "needs-revision" and d["applicability"] == "active"]
    if nr:
        W("Ripple queue: needs-revision -> " + ", ".join(nr))

    # --- package-wide Markdown links/diagrams; semantic ID checks only on project artifacts
    catalog = load_catalog()
    defs, refs = {}, {}
    open_q = {}
    question_registry_path = workspace_paths().questions
    if not question_registry_path.exists():
        E(f"WORKSPACE: question registry missing at {question_registry_path.relative_to(workspace_paths().root).as_posix()}")
    files_to_scan = scan_files()
    semantic_files = {f.resolve() for f in project_semantic_files(files_to_scan)}
    manifest_paths = {d["path"].rstrip("/") for d in docs if d["path"]}
    heading_cache = {}
    index_paths = semantic_index_paths(docs)
    for f in files_to_scan:
        rel = f.relative_to(workspace_paths().root).as_posix()
        raw = read(f)
        text = strip_noise(raw)

        # Relative Markdown links in root instructions, framework protocols, templates, docs, registries and logs.
        link_occurrences, link_issues = markdown_link_occurrences(raw)
        line_starts = markdown_line_starts(raw)
        for offset, detail in link_issues:
            line = markdown_line_number(offset, line_starts)
            E(f"{rel}:{line}: invalid Markdown link ({detail})")
        for target, offset in link_occurrences:
            if "{{" in target or "}}" in target:
                continue
            state, detail = markdown_link_target_exists(f, target, manifest_paths, heading_cache)
            line = markdown_line_number(offset, line_starts)
            if state == "planned":
                W(f"{rel}:{line}: link target not scaffolded yet -> {target[:160]} ({detail})")
            elif state == "invalid":
                E(f"{rel}:{line}: invalid link target ({detail})")
            elif state == "missing":
                E(f"{rel}:{line}: broken link -> {target[:160]} ({detail})")

        # Check Mermaid structure across all repository Markdown, including methodology and templates.
        check_mermaid(rel, raw, E, W)

        # The Mermaid reference index is a curated map to canonical document IDs; stale IDs there are errors.
        if rel == workspace_paths().relative(workspace_paths().framework / "DIAGRAMS.md"):
            for ref in re.findall(r"\bD\d+\.\d{2,}(?:\.\d{2,})*\b", strip_noise(raw)):
                if ref not in by_id:
                    E(f"{rel}: document reference {ref} is not present in _control/registry/MANIFEST.md")

        # Framework documents contain illustrative stable IDs; don't mix those examples into project ID accounting.
        if f.resolve() not in semantic_files:
            continue

        # IDs
        is_index = rel in index_paths
        if not is_index:
            for header, rows in parse_tables(text):
                for r in rows:
                    if r and FULL_ID_RE.match(clean(r[0])):
                        defs.setdefault(clean(r[0]), set()).add(rel)
            for m in re.finditer(r"^#{1,6}\s+`?(" + ID_RE.pattern + r")", text, re.M):
                defs.setdefault(m.group(1), set()).add(rel)
        for m in ID_RE.finditer(text):
            refs.setdefault(m.group(0), set()).add(rel)

        # content lint (docs only): placeholders, empty sections/fields, TBD, TODO, checklists, vague wording
        if rel.startswith("docs/"):
            drel = rel[len("docs/"):]
            status = path_status.get(drel)
            doc_key = next((d["id"] for d in docs if d["path"] == drel), "")
            cat = catalog.get(doc_key) or catalog.get(".".join(doc_key.split(".")[:2]), {})
            for severity, message in lint_document(raw, status, cat):
                (E if severity == "error" else W)(f"{rel}: {message}")

        # question registry
        if f.resolve() == question_registry_path.resolve():
            for header, rows in parse_tables(text):
                h = [c.lower() for c in header]
                if "id" in h and "status" in h:
                    for r in rows:
                        if len(r) >= len(h) and FULL_ID_RE.match(clean(r[h.index("id")])):
                            open_q[clean(r[h.index("id")])] = {
                                "status": clean(r[h.index("status")]).lower(),
                                "blocks": r[h.index("blocks")] if "blocks" in h else ""}

    for i, files in defs.items():
        real = {x for x in files}
        if len(real) > 1:
            E(f"ID {i} is defined in more than one file: {', '.join(sorted(real))}")
    undefined = sorted(i for i in refs if i not in defs and i not in open_q)
    for i in undefined:
        where = sorted(refs[i])
        more = f" and {len(where) - 3} more" if len(where) > 3 else ""
        msg = f"ID {i} is referenced but never defined (in {', '.join(where[:3])}{more})"
        (E if strict else W)(msg)

    # [TBD:Q-nnn] must reference existing questions
    for f in scan_files():
        rel = f.relative_to(workspace_paths().root).as_posix()
        if not rel.startswith("docs/"):
            continue
        for m in re.finditer(r"\[TBD:(Q-\d+)\]", strip_noise(read(f))):
            q = m.group(1)
            if q not in open_q:
                E(f"{rel}: [TBD:{q}] references a question that is not in {question_registry_path.relative_to(workspace_paths().root).as_posix()}")
            elif open_q[q]["status"] in ("answered", "dropped"):
                W(f"{rel}: [TBD:{q}] but the question is {open_q[q]['status']} - update the text")

    # --- registries
    dec = workspace_paths().decisions
    adr_dir = workspace_paths().adr
    if not dec.exists():
        E(f"WORKSPACE: decision registry missing at {dec.relative_to(workspace_paths().root).as_posix()}")
    if dec.exists():
        listed = set()
        for header, rows in parse_tables(strip_code(read(dec))):
            h = [c.lower() for c in header]
            if "id" in h and "file" in h:
                for r in rows:
                    if len(r) >= len(h) and FULL_ID_RE.match(clean(r[h.index("id")])):
                        fn = clean(r[h.index("file")])
                        listed.add(fn)
                        if fn and fn not in ("-", "—") and not (adr_dir / fn).exists():
                            E(f"{dec.relative_to(workspace_paths().root).as_posix()}: ADR file {adr_dir.relative_to(workspace_paths().root).as_posix()}/{fn} not found")
        if adr_dir.exists():
            for f in adr_dir.glob("*.md"):
                if f.name not in listed and f.name.lower() != "readme.md":
                    W(f"{adr_dir.relative_to(workspace_paths().root).as_posix()}/{f.name}: not indexed in {dec.relative_to(workspace_paths().root).as_posix()}")

    # --- STATE.md
    sp = state_path
    if not sp.exists():
        E(f"{workspace_paths().relative(workspace_paths().state)} missing")
    else:
        st = read(sp)
        if "<!-- PROGRESS:START -->" not in st or "<!-- PROGRESS:END -->" not in st:
            E(f"{workspace_paths().relative(workspace_paths().state)}: PROGRESS markers missing")
        if st.count("\n") > 200:
            W(f"{workspace_paths().relative(workspace_paths().state)} is {st.count(chr(10))} lines; keep it under ~150 (move history to _control/logs/)")

    # --- generated index freshness
    idx_path = workspace_paths().index
    if not idx_path.exists():
        W(f"{idx_path.relative_to(workspace_paths().root).as_posix()} is missing; run `python bp.py index`")
    elif index_is_stale(idx_path):
        W(f"{idx_path.relative_to(workspace_paths().root).as_posix()} is stale; run `python bp.py status --write` (or `index`)")

    # --- gate readiness
    if args.gate is not None:
        n = args.gate
        if n not in phases:
            E(f"GATE {n}: phase is not registered in {workspace_paths().relative(workspace_paths().phases)}")
        for d in docs:
            # A gate only governs applicable documents in the selected profile. Conditional,
            # deferred, excluded and deeper-tier documents cannot silently block a Lite gate.
            if (d["status"] in SKIP or d["applicability"] != "active"
                    or not profile_eligible(d, selected_profile, config)):
                continue
            if d["phase"] < n and d["status"] != "approved":
                E(f"GATE {n}: earlier-phase document {d['id']} is {d['status']}, not approved")
            if d["phase"] == n and d["status"] != "approved":
                E(f"GATE {n}: {d['id']} ({d['title']}) is {d['status']}, not approved")
        ids_in_phase = {d["id"] for d in docs if d["phase"] == n}
        for q, info in open_q.items():
            if info["status"] in ("open", "blocked", ""):
                blocks = info["blocks"]
                if f"P{n}" in re.findall(r"\bP\d+\b", blocks) or any(i in blocks for i in ids_in_phase):
                    E(f"GATE {n}: open question {q} blocks this phase")

    # --- state mutation log: valid JSONL plus status-manifest drift warnings
    for severity, message in validate_state_event_log(docs):
        (E if severity == "error" else W)(message)

    # --- optional draft-readiness report (advisory only; never changes validation exit status)
    if getattr(args, "readiness", False):
        eligible_statuses = {"drafting", "interviewing", "in-review"}
        signal_codes = {"TPL001", "SEC001", "FLD001", "CHK001", "TBD001", "TBD002", "TBD003", "DIR001", "VAG001", "GUIDE001", "TODO001", "DIA001"}
        inspected = 0
        documents_with_findings = 0
        total_findings = 0
        print("\nDRAFT READINESS (advisory; does not affect validation exit status)")
        for doc in docs:
            if (doc.get("applicability") != "active" or doc.get("status") not in eligible_statuses
                    or not profile_eligible(doc, selected_profile, config) or doc.get("path", "").endswith("/")):
                continue
            path = safe_document_path(doc["path"])
            if path is None or not path.is_file():
                continue
            inspected += 1
            cat_row = catalog.get(doc["id"]) or catalog.get(".".join(doc["id"].split(".")[:2]), {})
            # Reuse lint_document's existing detectors at review severity. These results are
            # deliberately reported separately and are not added to errors/warnings.
            findings = []
            for _severity, message in lint_document(read(path), "in-review", cat_row):
                code_match = re.match(r"([A-Z]{3}\d{3}):", message)
                if code_match and code_match.group(1) in signal_codes:
                    findings.append(message)
            if findings:
                documents_with_findings += 1
                total_findings += len(findings)
                print(f"READINESS {doc['id']} [{doc['status']}]: {len(findings)} signal(s)")
                for message in findings:
                    print(f"  - {message}")
        if not inspected:
            print("No scaffolded, active, in-profile documents in drafting, interviewing or in-review status were found.")
        elif not total_findings:
            print(f"No mechanical incompleteness signals found in {inspected} eligible document(s). This is not semantic certification.")
        else:
            print(f"Summary: inspected {inspected} eligible document(s); {documents_with_findings} have findings; {total_findings} signal(s). This is not semantic certification.")
        print("Readiness findings are advisory and do not affect the exit code; CI cannot gate on readiness findings in this version.")

    # --- report
    nopen = sum(1 for q in open_q.values() if q["status"] in ("open", "blocked", ""))
    for w in warns:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s). Open questions: {nopen}."
          + ("  [strict]" if strict else ""))
    if not errors:
        print("OK" + (" - gate checks passed." if args.gate is not None else "."))
    return 1 if errors else 0


# ----------------------------------------------------------------- scaffold
def rel_link(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, from_file.parent).replace(os.sep, "/")


def cmd_scaffold(args) -> int:
    docs = load_manifest()
    config = load_workspace_config()
    selected_profile = (args.profile or config.get("profile", "standard")).lower()
    if selected_profile not in PROFILE_TIERS:
        print(f"Unknown profile '{selected_profile}'. Choose: {', '.join(sorted(PROFILE_TIERS))}")
        return 2
    by_id = {d["id"]: d for d in docs}
    vision_id = config.get("vision_document_id", "D0.01")
    architecture_id = config.get("architecture_document_id", "D0.02")
    bootstrap_ids = set(config.get("bootstrap_doc_ids", [vision_id, architecture_id]))
    selected_ids = set()
    if args.only:
        selected_ids = {x.strip() for x in args.only.split(",") if x.strip()}
        unknown = selected_ids - set(by_id)
        if unknown:
            print("Unknown document ID(s): " + ", ".join(sorted(unknown)))
            return 2
        for did in sorted(selected_ids):
            d = by_id[did]
            if d["status"] == "excluded":
                print(f"{did} has legacy workflow status 'excluded'; migrate it to applicability='excluded' and a valid workflow status first.")
                return 2
            if d["applicability"] != "active":
                print(f'{did} is applicability="{d["applicability"]}" and cannot be scaffolded. Resolve its disposition in D0.02, then use: python bp.py applicability {did} active --reason <reason>')
                return 2
            if d["path"].endswith("/"):
                print(f"{did} is a repeatable document family/folder row, not a file template. Expand it into concrete child document records before scaffolding individual specs.")
                return 2
            if not profile_eligible(d, selected_profile, config):
                print(f"{did} has profile tier '{d['profile_tier']}' and is not eligible for profile '{selected_profile}'. Select a higher profile or revise the D0.02 plan.")
                return 2
    if args.override_architecture_gate and not (args.override_reason or "").strip():
        print("An architecture-gate override requires --override-reason with a concise explanation.")
        return 2

    # The architecture baseline must be owner-approved (with an approval record), complete, and its inputs approved.
    architecture_problems = architecture_gate_problems(by_id, config)
    architecture_approved = not architecture_problems

    requested_docs = []
    ignored = []
    for d in docs:
        if selected_ids and d["id"] not in selected_ids:
            continue
        if args.phase is not None and d["phase"] != args.phase:
            continue
        if not selected_ids and args.phase is None and not args.all:
            continue
        if d["status"] in SKIP or d["status"] == "excluded" or d["path"].endswith("/"):
            ignored.append(d)
            continue
        if d["applicability"] != "active":
            ignored.append(d)
            continue
        if not profile_eligible(d, selected_profile, config):
            ignored.append(d)
            continue
        requested_docs.append(d)

    requests_beyond_bootstrap = any(d["id"] not in bootstrap_ids for d in requested_docs)
    upstream_integrity_problems = []
    if requests_beyond_bootstrap:
        upstream_integrity_problems = approved_ancestor_integrity_problems(requested_docs, by_id)
        if upstream_integrity_problems:
            architecture_problems.extend(p for p in upstream_integrity_problems if p not in architecture_problems)
            architecture_approved = False

    # An explicit architecture exception may permit early scaffolding before a baseline
    # is approved, but must never bypass evidence that an already-approved input was
    # modified, has a missing record/file, or uses a legacy/invalid fingerprint.
    integrity_markers = (
        "approval registry has no record", "approved version is", "approval record exists but",
        "legacy body-only hash", "invalid fingerprint format", "fingerprint mismatch",
        "approval fingerprint", "content changed after owner approval",
    )
    integrity_failures = [p for p in architecture_problems if any(m in p for m in integrity_markers)]
    integrity_failures.extend(p for p in upstream_integrity_problems if p not in integrity_failures)
    if requests_beyond_bootstrap and integrity_failures:
        print("Approval integrity failure cannot be bypassed by the architecture-gate override:")
        for problem in integrity_failures:
            print(f"  - {problem}")
        print("Restore the approved artifact or move it through needs-revision and obtain a new explicit approval.")
        return 2

    architecture_id = config.get("architecture_document_id", "D0.02")
    architecture_record = by_id.get(architecture_id)
    if (requests_beyond_bootstrap and args.override_architecture_gate and architecture_record
            and architecture_record["status"] == "approved" and architecture_problems):
        print("Cannot override a broken approved architecture baseline. The architecture is marked approved, "
              "but one or more required inputs/sections/approval records are no longer valid:")
        for problem in architecture_problems:
            print(f"  - {problem}")
        print("Move affected documents through needs-revision, repair the baseline, and re-approve it.")
        return 2

    if requests_beyond_bootstrap and not architecture_approved and not args.override_architecture_gate:
        message = (f"Adaptive documentation architecture gate: cannot scaffold beyond the bootstrap documents "
                   f"({', '.join(sorted(bootstrap_ids))}) because:\n  - " + "\n  - ".join(architecture_problems) +
                   "\nFor a deliberate exception pass --override-architecture-gate --override-reason '<reason>'.")
        if args.dry_run:
            print("PREVIEW NOTE: " + message)
        else:
            print(message)
            return 2
    elif requests_beyond_bootstrap and not architecture_approved and args.override_architecture_gate:
        print("WARNING: Adaptive architecture gate overridden. Reason: " + args.override_reason.strip())
        if not args.dry_run:
            record_override("architecture-gate", args.override_reason.strip(), [d["id"] for d in requested_docs])
            event = build_state_event("architecture_override", document_ids=[d["id"] for d in requested_docs],
                                      reason=args.override_reason.strip(), actor="blueprint CLI")
            if not persist_state_events([event], "Architecture-gate override"):
                return 2

    catalog = load_catalog()
    template_root = workspace_paths().templates
    default_template = "document"
    # Preflight every mapping before creating any file, avoiding partial scaffolds.
    for d in requested_docs:
        target_file = safe_document_path(d["path"])
        if target_file is None:
            print(f"Unsafe output path for {d['id']}: {d['path']}")
            return 2
        if target_file.exists():
            continue
        cat_row = catalog.get(d["id"]) or catalog.get(".".join(d["id"].split(".")[:2]), {})
        template_name = (cat_row.get("template", "") or "").strip() or ("component-spec" if "/components/" in d["path"] else default_template)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", template_name):
            print(f"Invalid template mapping '{template_name}' for {d['id']}; use a simple kebab-case template basename.")
            return 2
        if not (template_root / f"{template_name}.md").exists():
            print(f"Template '{template_name}' for {d['id']} not found: {template_root / (template_name + '.md')}")
            return 2

    created = 0
    created_records = []
    for d in requested_docs:
        fp = safe_document_path(d["path"])
        if fp is None or fp.exists():
            continue
        cat = catalog.get(d["id"]) or catalog.get(".".join(d["id"].split(".")[:2]), {})
        items = [i.strip() for i in cat.get("must contain", "").split(";") if i.strip()]
        checklist = "\n".join(
            "- [ ] **Diagram:** " + re.sub(r"^\[diagram:\s*|\]$", "", i) if i.startswith("[diagram") else "- [ ] " + i
            for i in items) or "- [ ] (define the checklist for this document)"
        links = []
        for dep in d["depends"]:
            dd = by_id.get(dep)
            if not dd or dd["applicability"] in ("excluded", "deferred") or dd["status"] in ("superseded",):
                links.append(f"- {dep} (excluded, deferred or unavailable)")
            elif dd["path"].endswith("/"):
                links.append(f"- {dep} - {dd['title']} (folder: `{dd['path']}`)")
            else:
                links.append(f"- [{dep} - {dd['title']}]({rel_link(fp, safe_document_path(dd['path']) or (workspace_paths().docs / dd['path']))})")
        template_name = (cat.get("template", "") or "").strip() or ("component-spec" if "/components/" in d["path"] else default_template)
        tpl = read(template_root / f"{template_name}.md")
        vision_doc = by_id.get(vision_id)
        vision_path = safe_document_path(vision_doc["path"]) if vision_doc and not vision_doc["path"].endswith("/") else None
        vision_link = rel_link(fp, vision_path) if vision_path else ""
        manifest_link = rel_link(fp, workspace_paths().manifest)
        architecture_protocol_link = rel_link(fp, workspace_paths().framework / "ADAPTIVE-DOCUMENT-ARCHITECTURE.md")
        out = (tpl.replace("{{DOC_ID}}", d["id"]).replace("{{TITLE}}", d["title"])
                  .replace("{{PHASE}}", str(d["phase"])).replace("{{DATE}}", today())
                  .replace("{{STATUS}}", d["status"])
                  .replace("{{MATURITY}}", d["maturity"])
                  .replace("{{APPLICABILITY}}", d["applicability"])
                  .replace("{{APPLICABILITY_RATIONALE}}", d["applicability_rationale"].replace("\\", "\\\\").replace('"', '\\"'))
                  .replace("{{PROFILE_TIER}}", d["profile_tier"])
                  .replace("{{VERSION}}", d["version"])
                  .replace("{{DEPENDS}}", ", ".join(d["depends"]))
                  .replace("{{INPUT_LINKS}}", "\n".join(links) if links else "_None (entry document)._")
                  .replace("{{CHECKLIST}}", checklist)
                  .replace("{{VISION_LINK}}", vision_link)
                  .replace("{{MANIFEST_LINK}}", manifest_link)
                  .replace("{{ARCHITECTURE_PROTOCOL_LINK}}", architecture_protocol_link))
        if re.search(r"{{[A-Z_]+}}", out):
            unresolved = sorted(set(re.findall(r"{{([A-Z_]+)}}", out)))
            print(f"Template '{template_name}' for {d['id']} has unresolved placeholder(s): {', '.join(unresolved)}")
            return 2
        print(("would create " if args.dry_run else "created ") + f"docs/{d['path']}")
        if not args.dry_run:
            write(fp, out)
            # Keep the manifest date aligned with the date written into the new file's front matter.
            if not update_manifest_row(d["id"], {"Last updated": today()}):
                print(f"ERROR: created docs/{d['path']} but could not update its manifest date; reconcile before continuing.")
                return 2
            created_records.append(d)
        created += 1
    if not args.dry_run and created_records:
        events = [build_state_event("scaffold", document_id=d["id"], path=d["path"], status=d["status"],
                                    reason="Initial document skeleton created", actor="blueprint CLI")
                  for d in created_records]
        if not persist_state_events(events, "Scaffolding"):
            return 2
    if ignored and (args.phase is not None or args.all):
        print(f"Skipped {len(ignored)} manifest item(s) outside the selected applicability/profile scope, already expanded, or not scaffoldable.")
    if args.phase is None and not selected_ids and not args.all:
        print("\nNo files selected. For incremental work use --only D0.01 or --phase N. Use --all only when bulk scaffolding is explicitly intended.")
        return 2
    print(f"\n{created} file(s) {'would be ' if args.dry_run else ''}created under profile '{selected_profile}'.")
    return 0


def cmd_maturity(args) -> int:
    level = args.level.lower()
    if level not in MATURITIES:
        print("Maturity must be one of: outline, working, detailed")
        return 2
    docs = load_manifest()
    doc = next((x for x in docs if x["id"] == args.doc_id), None)
    if not doc:
        print(f"Unknown document ID: {args.doc_id}")
        return 2
    old_level = doc["maturity"]
    if old_level == level:
        print(f"{args.doc_id} maturity is already {level}.")
        return 0
    updates = {"Maturity": level, "Last updated": today()}
    if not update_manifest_row(args.doc_id, updates):
        print("Could not update manifest row; verify the manifest schema.")
        return 2
    fp = safe_document_path(doc["path"]) if not doc["path"].endswith("/") else None
    if fp and fp.exists() and not update_front_matter_fields(fp, {"maturity": level, "last_updated": today()}):
        print("ERROR: manifest maturity was updated but front matter could not be synchronized; reconcile before continuing.")
        return 2
    event = build_state_event("maturity_change", document_id=args.doc_id, from_maturity=old_level,
                              to_maturity=level, reason=(args.reason or "").strip() or None, actor=args.by)
    if not persist_state_events([event], "Maturity update"):
        return 2
    print(f"{args.doc_id} maturity set to {level} in manifest" + (" and document front matter." if fp and fp.exists() else ". Document file not scaffolded yet; manifest updated."))
    return 0


def cmd_applicability(args) -> int:
    level = args.level.lower()
    if level not in APPLICABILITY_VALUES:
        print(f"Applicability must be one of: {', '.join(sorted(APPLICABILITY_VALUES))}")
        return 2
    reason = (args.reason or "").strip()
    if not reason:
        print("Applicability changes require --reason so the scope decision remains auditable.")
        return 2
    docs = load_manifest()
    doc = next((x for x in docs if x["id"] == args.doc_id), None)
    if not doc:
        print(f"Unknown document ID: {args.doc_id}")
        return 2
    old_level, old_reason = doc["applicability"], doc["applicability_rationale"]
    updates = {"Applicability": level, "Applicability rationale": reason, "Last updated": today()}
    if not update_manifest_row(args.doc_id, updates):
        print("Could not update manifest row; verify the manifest schema.")
        return 2
    fp = safe_document_path(doc["path"]) if not doc["path"].endswith("/") else None
    if fp and fp.exists() and not update_front_matter_fields(fp, {"applicability": level, "applicability_rationale": reason, "last_updated": today()}):
        print("ERROR: applicability was updated in the manifest but front matter could not be synchronized; reconcile before continuing.")
        return 2
    event = build_state_event("applicability_change", document_id=args.doc_id,
                              from_applicability=old_level, to_applicability=level,
                              from_rationale=old_reason, to_rationale=reason,
                              reason=reason, actor=args.by)
    if not persist_state_events([event], "Applicability update"):
        return 2
    print(f"{args.doc_id} applicability set to {level}. Update D0.02's disposition inventory to keep the rationale and structural design aligned.")
    if level in {"deferred", "excluded"}:
        print("This document will no longer be scaffolded or counted in progress for the selected profile.")
    return 0


def cmd_profile(args) -> int:
    config_path = workspace_paths().workspace_config
    try:
        config = load_workspace_config()
        project_config = json.loads(read(config_path))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(exc)
        return 2
    if args.name is None:
        print(f"Selected profile: {config.get('profile', 'standard')}")
        print("Profiles: lite (tier 1), standard (tiers 1–2), exhaustive (tiers 1–3)")
        return 0
    name = args.name.lower()
    if name not in PROFILE_TIERS:
        print(f"Unknown profile '{name}'. Choose: {', '.join(sorted(PROFILE_TIERS))}")
        return 2
    old_name = str(config.get("profile", "standard")).lower()
    if old_name == name:
        print(f"Default workspace profile is already '{name}'.")
        return 0
    project_config["profile"] = name
    write(config_path, json.dumps(project_config, indent=2, ensure_ascii=False) + "\n")
    event = build_state_event("profile_change", from_profile=old_name, to_profile=name,
                              reason=(args.reason or "").strip() or None, actor=args.by)
    if not persist_state_events([event], "Profile update"):
        return 2
    print(f"Default workspace profile set to '{name}'. Status and scaffold commands will use this profile unless overridden.")
    return 0


# ----------------------------------------------------------------- graph
def cmd_graph(args) -> int:
    config = load_workspace_config()
    selected_profile = (args.profile or config.get("profile", "standard")).lower()
    if selected_profile not in PROFILE_TIERS:
        print(f"Unknown profile '{selected_profile}'. Choose: {', '.join(sorted(PROFILE_TIERS))}")
        return 2
    docs = [d for d in load_manifest()
            if d["status"] not in SKIP and d["applicability"] not in ("excluded", "deferred")
            and profile_eligible(d, selected_profile, config)]
    ids = {d["id"] for d in docs}
    phase_names = load_phases()
    print(f"%% Profile: {selected_profile}; edges represent content dependencies only. Structural impact from {config.get('architecture_document_id', 'D0.02')} is handled separately.\n```mermaid\nflowchart LR")
    for ph in sorted({d["phase"] for d in docs}):
        phase_label = phase_names.get(ph, f"UNREGISTERED PHASE {ph}")
        print(f'    subgraph PH{ph}["Phase {ph}: {phase_label}"]')
        for d in docs:
            if d["phase"] == ph:
                nid = re.sub(r"[^A-Za-z0-9_]", "_", d["id"])
                label = d["title"].replace('"', "'")
                print(f'        {nid}["{d["id"]}<br/>{label}<br/>[{d["applicability"]}/{d["status"]}]"]')
        print("    end")
    for d in docs:
        for dep in d["depends"]:
            if dep in ids:
                print(f'    {re.sub(r"[^A-Za-z0-9_]", "_", dep)} --> {re.sub(r"[^A-Za-z0-9_]", "_", d["id"])}')
    print("```")
    return 0


# ----------------------------------------------------------------- session
def cmd_session(args) -> int:
    d = workspace_paths().sessions
    d.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for f in d.glob("session-*.md") if (m := re.match(r"session-(\d+)-", f.name))]
    n = max(nums, default=0) + 1
    tpl = read(workspace_paths().templates / "session-log.md")
    path = d / f"session-{n:03d}-{today()}.md"
    if path.exists():
        print(f"{path} already exists")
        return 1
    write(path, tpl.replace("{{N}}", str(n)).replace("{{DATE}}", today()))
    print(f"created {path.relative_to(workspace_paths().root).as_posix()}")
    return 0




# ----------------------------------------------------------------- impact analysis
def cmd_impact(args) -> int:
    """Report content dependencies and structural review candidates as distinct relationships."""
    target = args.target
    docs = load_manifest()
    config = load_workspace_config()
    selected_profile = (args.profile or config.get("profile", "standard")).lower()
    if selected_profile not in PROFILE_TIERS:
        print(f"Unknown profile '{selected_profile}'. Choose: {', '.join(sorted(PROFILE_TIERS))}")
        return 2
    by_id = {d["id"]: d for d in docs}
    if target in by_id:
        roots = {target}
        frontier = [target]
        while frontier:
            current = frontier.pop(0)
            for d in docs:
                if current in d["depends"] and d["id"] not in roots:
                    roots.add(d["id"])
                    frontier.append(d["id"])
        print(f"Content-dependency impact for {target} (edges mean a consumer needs information from its dependency):")
        for did in sorted(roots, key=lambda x: (doc_phase(x), x)):
            d = by_id[did]
            marker = "SOURCE" if did == target else "CONTENT DEPENDENT"
            print(f"- [{marker}] {did} — {d['title']} (phase {d['phase']}, applicability {d['applicability']}, status {d['status']})")
        architecture_id = config.get("architecture_document_id", "D0.02")
        if target == architecture_id:
            print(f"\nStructural-impact review candidates for {architecture_id} (NOT content dependents):")
            candidates = [d for d in docs if d["id"] != target and d["applicability"] in ("active", "conditional")
                          and d["status"] not in SKIP and profile_eligible(d, selected_profile, config)]
            for d in sorted(candidates, key=lambda x: (x["phase"], x["id"])):
                print(f"- [STRUCTURAL CANDIDATE] {d['id']} — {d['title']} (phase {d['phase']}, {d['applicability']}/{d['status']})")
            print("Review each candidate; revise only those whose meaning, location, ownership or dependency is actually affected.")
    else:
        pat = re.compile(rf"(?<![A-Z0-9_-]){re.escape(target)}(?![A-Z0-9_-])")
        matches = []
        for f in project_semantic_files(scan_files()):
            rel = f.relative_to(workspace_paths().root).as_posix()
            if pat.search(strip_noise(read(f))):
                matches.append(rel)
        if not matches:
            print(f"No project-content references found for '{target}'. Check spelling or whether the ID is registered.")
            return 1
        print(f"Textual references to {target}:")
        for rel in matches:
            print(f"- {rel}")
    return 0


# ----------------------------------------------------------------- content lint
def mask_code(text: str) -> str:
    return FENCE_RE.sub("(code)", text)


def strip_empty_tables(body: str) -> str:
    """Drop tables that have a header but no non-blank body rows (they carry no content)."""
    lines = body.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and SEP_RE.match(lines[i + 1]):
            j, rows = i + 2, 0
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                if any(c.strip() for c in split_row(lines[j])):
                    rows += 1
                j += 1
            if rows:
                out.extend(lines[i:j])
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def prose_view(raw: str) -> str:
    """Document body without front matter and HTML comments; code blocks collapsed to a marker."""
    body = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.S)
    return mask_code(strip_html_comments(body))


def empty_sections(raw: str):
    lines = prose_view(raw).split("\n")
    heads = [(i, len(m.group(1)), m.group(2).strip())
             for i, l in enumerate(lines) if (m := re.match(r"^(#{1,6})\s+(.*)$", l))]
    empties = []
    for k, (i, level, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        next_level = heads[k + 1][1] if k + 1 < len(heads) else 0
        body = strip_empty_tables("\n".join(lines[i + 1:end]))
        if not body.strip() and not next_level > level:
            empties.append(title)
    return empties


def empty_fields(raw: str):
    lines = prose_view(raw).split("\n")
    found = []
    for i, line in enumerate(lines):
        m = FIELD_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        nxt = next((l for l in lines[i + 1:] if l.strip()), "")
        if nxt and (len(nxt) - len(nxt.lstrip())) > indent and re.match(r"^\s*[-*\d]", nxt):
            continue  # populated by nested items
        found.append(re.sub(r"^[\s\-*]+|[\s*:]+$", "", line))
    return found


def _body_without_front_matter(raw: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.S)


def find_fill_markers(raw: str):
    """Return unfilled explicit markers and directive issues, preserving source-line semantics.

    `ignore-line` suppresses FILL markers on the same physical line. `ignore-next-line`
    suppresses markers only on the immediately following physical line (not the next
    nonblank line). For list/table rows, prefer inline `ignore-line` so Markdown structure
    is not broken by a standalone comment line. Suppressions affect TPL001 only.
    """
    body = _body_without_front_matter(raw)
    lines = body.splitlines()
    ignored_lines = set()
    directives = []
    in_fence = False
    fence_char = None
    for i, line in enumerate(lines):
        # Directives inside fenced code are examples, not active instructions.
        is_fence_line = bool(re.match(r"^\s*(```+|~~~+)", line))
        if not in_fence and not is_fence_line:
            inline_match = IGNORE_LINE_RE.search(line)
            next_match = IGNORE_NEXT_LINE_RE.search(line)
            has_token = bool(LINT_DIRECTIVE_TOKEN_RE.search(line))
            if inline_match:
                reason = inline_match.group(1).strip()
                if len(reason) < 8:
                    directives.append((i + 1, "DIR001", "ignore-line directive requires a meaningful reason of at least 8 characters"))
                else:
                    ignored_lines.add(i)
                    directives.append((i + 1, "DIR001_USED_LINE", reason))
            elif next_match:
                # Next-line directive must be a standalone comment. This is intentionally
                # precise: next means the next physical source line, including blank lines.
                if line.strip() != next_match.group(0).strip():
                    directives.append((i + 1, "DIR001", "ignore-next-line must be a standalone comment; use inline ignore-line in a table/list"))
                elif len(next_match.group(1).strip()) < 8:
                    directives.append((i + 1, "DIR001", "ignore-next-line directive requires a meaningful reason of at least 8 characters"))
                elif i + 1 >= len(lines):
                    directives.append((i + 1, "DIR001", "ignore-next-line has no following physical line"))
                else:
                    ignored_lines.add(i + 1)
                    directives.append((i + 2, "DIR001_USED_NEXT", next_match.group(1).strip()))
            elif has_token:
                named = re.search(r"blueprint-lint:\s*([a-z-]+)", line, re.I)
                directive_name = named.group(1).lower() if named else ""
                if directive_name in {"ignore-line", "ignore-next-line"}:
                    directives.append((i + 1, "DIR001", f"{directive_name} directive requires `-- reason: <meaningful reason> --`"))
                else:
                    directives.append((i + 1, "DIR001", "unrecognized blueprint-lint directive; see _framework/LINT-RULES.md"))
        if is_fence_line:
            fence_match = re.match(r"^\s*(```+|~~~+)", line)
            fence = fence_match.group(1)[0] if fence_match else None
            if not in_fence:
                in_fence = True
                fence_char = fence
            elif fence == fence_char:
                in_fence = False
                fence_char = None
    markers = []
    line_has_marker = set()
    for i, line in enumerate(lines):
        # HTML-comment contents are not rendered document content. Escaped marker syntax
        # (`\\[[FILL: ...]]`) is treated as a literal example.
        visible = strip_html_comments(line)
        visible = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), visible)
        found = list(FILL_RE.finditer(visible))
        if found:
            line_has_marker.add(i)
            if i not in ignored_lines:
                markers.extend((i + 1, m.group(1).strip()) for m in found)
    issues = []
    for line_no, rule, detail in directives:
        if rule == "DIR001":
            issues.append((line_no, detail))
        elif rule in ("DIR001_USED_LINE", "DIR001_USED_NEXT"):
            # Reconstruct the target line from the marker line for this directive.
            target_index = line_no - 1
            if rule == "DIR001_USED_LINE":
                target_index = line_no - 1
            else:
                target_index = line_no - 1
            if target_index not in line_has_marker:
                issues.append((line_no, "suppression directive did not target an unfilled [[FILL: ...]] marker; remove it"))
    return markers, issues


def lint_document(raw: str, status: str | None, cat: dict | None = None):
    """Return [(severity, message)] for one manifest-backed document.

    Template placeholders use only the explicit `[[FILL: ...]]` marker convention.
    Ordinary bracketed prose, citations, Markdown labels and escaped markers are not prompts.
    In `in-review` documents hollow content is a warning; in `approved` documents it is an error.
    """
    out = []
    text = strip_noise(raw)
    for m in re.finditer(r"\[TBD(?::([A-Z]+-\d+))?\]", text):
        if not m.group(1):
            out.append(("error", "TBD001: [TBD] without a question id (use [TBD:Q-nnn])"))
    if status not in ("in-review", "approved"):
        return out
    hard = status == "approved"
    sev = "error" if hard else "warning"
    label = "approved" if hard else "in-review"
    if hard:
        if re.search(r"\[TBD", text):
            out.append(("error", "TBD002: approved document still contains [TBD]"))
        if "<!-- TODO" in raw:
            out.append(("error", "TODO001: approved document still contains a TODO comment"))
        if "<!-- GUIDE" in raw:
            out.append(("warning", "GUIDE001: approved document still contains GUIDE comments"))
    unchecked = len(re.findall(r"^\s*- \[ \]", text, re.M))
    if unchecked:
        out.append((sev, f"CHK001: {label} but {unchecked} checklist item(s) unticked (tick it or write 'N/A: reason')"))
    markers, directive_issues = find_fill_markers(raw)
    for line_no, issue in directive_issues:
        out.append(("error" if hard else "warning", f"DIR001: line {line_no}: {issue}"))
    if markers:
        shown = "; ".join(f"line {n}: [[FILL: {x[:36]}{'…' if len(x) > 36 else ''}]]" for n, x in markers[:3])
        out.append((sev, f"TPL001: {label} but {len(markers)} unfilled template prompt marker(s) remain: {shown}"))
    view = prose_view(raw)
    if BARE_TBD_RE.search(view):
        out.append((sev, f"TBD003: {label} but contains an untagged 'TBD' (resolve it or use [TBD:Q-nnn])"))
    empties = empty_sections(raw)
    if empties:
        shown = ", ".join(f"'{t[:40]}'" for t in empties[:4]) + (" …" if len(empties) > 4 else "")
        out.append((sev, f"SEC001: {label} but {len(empties)} empty section(s): {shown} (write content or 'N/A: reason')"))
    fields = empty_fields(raw)
    if fields:
        shown = ", ".join(f"'{t[:40]}'" for t in fields[:4]) + (" …" if len(fields) > 4 else "")
        out.append((sev, f"FLD001: {label} but {len(fields)} empty field(s): {shown}"))
    if hard and cat and "[diagram" in cat.get("must contain", "") and not MERMAID_RE.search(raw):
        out.append(("warning", "DIA001: approved, catalog expects diagram(s) but none found"))
    if "<!-- vague-ok" not in raw:
        words = {}
        for m in VAGUE_RE.finditer(re.sub(r"^#{1,6}.*$", "", view, flags=re.M)):
            w = m.group(0).lower()
            words[w] = words.get(w, 0) + 1
        if words:
            shown = ", ".join(f"{w}×{n}" for w, n in sorted(words.items(), key=lambda x: -x[1])[:5])
            out.append(("warning", f"VAG001: vague wording to define or quantify ({shown}); add <!-- vague-ok: reason --> to silence"))
    return out


# ----------------------------------------------------------------- approvals
APPROVAL_METADATA_FIELDS = (
    "doc_id", "title", "phase", "summary", "depends_on",
    "applicability", "applicability_rationale", "profile_tier",
)


def approval_fingerprint(text: str, d: dict) -> str:
    """Bind approved prose plus meaning-bearing metadata; ignore lifecycle-only fields.

    The fingerprint normalizes CRLF/LF, whitespace at line ends, and dependency ordering.
    Maturity and last_updated are intentionally excluded so routine elaboration metadata
    does not invalidate an approval. Workflow status/version are validated separately.
    Critical metadata is included twice (manifest and front matter) so changing either
    representation invalidates approval even before/independently of drift diagnostics.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---\n.*?\n---\n", text, re.S)
    body = text[match.end():] if match else text
    body = "\n".join(line.rstrip() for line in body.split("\n")).strip()
    fm = front_matter(text) or {}

    manifest_meta = {
        "doc_id": str(d.get("id", "")).strip(),
        "path": str(d.get("path", "")).strip(),
        "title": str(d.get("title", "")).strip(),
        "phase": str(d.get("phase", "")).strip(),
        "depends_on": sorted(parse_list(", ".join(d.get("depends", [])))),
        "applicability": str(d.get("applicability", "")).strip(),
        "applicability_rationale": str(d.get("applicability_rationale", "")).strip(),
        "profile_tier": str(d.get("profile_tier", "")).strip(),
    }
    front_matter_meta = {}
    for field in APPROVAL_METADATA_FIELDS:
        value = fm.get(field, "").strip()
        if field == "depends_on":
            value = sorted(parse_list(value))
        front_matter_meta[field] = value

    payload = {
        "fingerprint_format": "blueprint-approval-v2",
        "manifest_metadata": manifest_meta,
        "front_matter_metadata": front_matter_meta,
        "body": body,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_approvals():
    path = workspace_paths().approvals
    out = {}
    if not path.exists():
        return out
    for header, rows in parse_tables(strip_code(read(path))):
        h = [c.lower() for c in header]
        if "doc id" not in h or "content hash" not in h:
            continue
        ix = {n: i for i, n in enumerate(h)}
        for r in rows:
            if len(r) < len(h):
                continue
            did = clean(r[ix["doc id"]])
            if did:
                out[did] = {k: clean(r[i]) for k, i in ix.items()}  # later rows supersede earlier ones
    return out


def approval_problem(d: dict, fp: Path, approvals: dict):
    rec = approvals.get(d["id"])
    if rec is None:
        return ("status is 'approved' but the approvals registry has no record for it "
                "(owner approval must be recorded with `python bp.py approve`)")
    if rec.get("version") != d["version"]:
        return (f"approved version is {d['version']} but the latest approval record is for {rec.get('version')}; "
                "re-approve through `approve`")
    if fp is None or not fp.exists():
        return "approval record exists but the document file is missing"
    document_text = read(fp)
    fm = front_matter(document_text) or {}
    # Status and version are deliberately not hashed as semantic content, but gates
    # must still verify that front matter and manifest agree without requiring a
    # separate global `check` to have run first.
    for field in ("status", "version"):
        manifest_value = str(d.get(field, "")).strip()
        front_matter_value = str(fm.get(field, "")).strip()
        if front_matter_value != manifest_value:
            return (f"front-matter {field} '{front_matter_value or '(empty)'}' does not match "
                    f"manifest {field} '{manifest_value or '(empty)'}'; repair metadata and re-check approval")
    recorded_hash = rec.get("content hash", "").strip()
    if len(recorded_hash) != 64 or not re.fullmatch(r"[0-9a-fA-F]{64}", recorded_hash):
        return ("approval record uses a legacy body-only hash or an invalid fingerprint format; "
                "re-review and re-approve this document to bind critical metadata")
    if approval_fingerprint(document_text, d) != recorded_hash.lower():
        return ("content changed after owner approval or approval-bearing metadata changed after owner approval "
                "(fingerprint mismatch). Set it to needs-revision with "
                "`set-status ... needs-revision --reason ...`, revise, and re-approve")
    return None


def approved_ancestor_integrity_problems(seed_docs: list[dict], by_id: dict, approvals: dict | None = None) -> list[str]:
    """Find invalid approval fingerprints anywhere in a set of content-dependency chains.

    This does not require every ancestor to be approved for drafting/scaffolding. It does
    block when an ancestor *claims* to be approved but its approval evidence no longer
    matches the current document and meaning-bearing metadata.
    """
    approvals = approvals if approvals is not None else load_approvals()
    problems = []
    visited = set()

    def visit(doc):
        for dep_id in doc.get("depends", []):
            if dep_id in visited:
                continue
            visited.add(dep_id)
            dep = by_id.get(dep_id)
            if not dep:
                continue  # Unknown edges are diagnosed by `check`; don't invent their state here.
            if (doc.get("status") == "approved" and dep.get("applicability") == "active"
                    and dep.get("status") not in SKIP and dep.get("status") != "approved"):
                problems.append(
                    f"approved upstream document {doc['id']} depends on {dep_id}, which is "
                    f"'{dep.get('status')}'; downstream approval must be reviewed after its input changes"
                )
            if dep.get("status") == "approved":
                dep_path = dep.get("path", "")
                fp = safe_document_path(dep_path) if dep_path and not dep_path.endswith("/") else None
                problem = approval_problem(dep, fp, approvals)
                if problem:
                    problems.append(f"upstream dependency {dep_id}: {problem}")
            visit(dep)

    for seed in seed_docs:
        visit(seed)
    return problems


def architecture_gate_problems(by_id: dict, config: dict):
    aid = config.get("architecture_document_id", "D0.02")
    arch = by_id.get(aid)
    if not arch:
        return [f"{aid} is missing from the manifest"]
    if arch["status"] != "approved":
        return [f"{aid} has status '{arch['status']}'; the owner must approve it (record with `approve`)"]
    problems = []
    fp = safe_document_path(arch["path"]) if not arch["path"].endswith("/") else None
    if not fp or not fp.exists():
        return [f"{aid} is marked approved but its file docs/{arch['path']} is missing"]
    text = read(fp)
    approvals = load_approvals()
    for dep in arch["depends"]:
        dd = by_id.get(dep)
        if not dd or dd["status"] != "approved":
            problems.append(f"{aid} depends on {dep}, which is '{dd['status'] if dd else 'missing'}', not approved")
        elif dd["applicability"] == "active":
            dep_fp = safe_document_path(dd["path"]) if not dd["path"].endswith("/") else None
            dep_problem = approval_problem(dd, dep_fp, approvals)
            if dep_problem:
                problems.append(f"{aid} input {dep}: {dep_problem}")
    for heading in ARCHITECTURE_REQUIRED_HEADINGS:
        if heading not in text:
            problems.append(f"{aid} lacks required section: {heading}")
    problem = approval_problem(arch, fp, approvals)
    if problem:
        problems.append(f"{aid}: {problem}")
    return problems


def append_table_row(path: Path, cells: list) -> None:
    lines = read(path).split("\n")
    last = max((i for i, l in enumerate(lines) if l.lstrip().startswith("|")), default=None)
    if last is None:
        raise ValueError(f"{path.relative_to(workspace_paths().root).as_posix()} has no table to append to")
    safe = [str(c).replace("|", "/").replace("\n", " ") for c in cells]
    lines.insert(last + 1, "| " + " | ".join(safe) + " |")
    write(path, "\n".join(lines).rstrip("\n") + "\n")


def cmd_approve(args) -> int:
    docs = load_manifest()
    by_id = {d["id"]: d for d in docs}
    config = load_workspace_config()
    d = by_id.get(args.doc_id)
    if not d:
        print(f"Unknown document ID: {args.doc_id}")
        return 2
    evidence = (args.evidence or "").strip()
    if not evidence:
        print("Approval requires --evidence: where the owner approved (e.g. the owner's words or a session-log reference).")
        return 2
    if len(evidence) < 24:
        print("WARN: approval evidence is very short; prefer the owner's explicit words plus a session reference.")
    if not re.search(r"\bsession-\d{3,}(?:-[0-9]{4}-[0-9]{2}-[0-9]{2})?\b", evidence, re.I):
        print("WARN: approval evidence has no session reference; include a real session-<NNN>-<date>.md reference when available.")
    if d["applicability"] != "active" or d["path"].endswith("/"):
        print(f"{d['id']} is not an active, file-backed document and cannot be approved.")
        return 2
    fp = safe_document_path(d["path"])
    if not fp or not fp.exists():
        print(f"docs/{d['path']} does not exist; scaffold and write the document first.")
        return 2
    if d["status"] != "in-review":
        print(f"{d['id']} is '{d['status']}'. Only documents in 'in-review' can be approved; finish self-review and run "
              f"`set-status {d['id']} in-review` first.")
        return 2
    raw = read(fp)
    fm = front_matter(raw) or {}
    problems = []
    if not fm.get("summary"):
        problems.append("front-matter summary is empty")
    cat = load_catalog()
    cat_row = cat.get(d["id"]) or cat.get(".".join(d["id"].split(".")[:2]), {})
    problems += [m for sev, m in lint_document(raw, "approved", cat_row) if sev == "error"]
    if d["id"] == config.get("architecture_document_id", "D0.02"):
        problems += [f"required section missing: {h}" for h in ARCHITECTURE_REQUIRED_HEADINGS if h not in raw]
    approvals = load_approvals()
    bootstrap_ids = set(config.get("bootstrap_doc_ids", [config.get("vision_document_id", "D0.01"), config.get("architecture_document_id", "D0.02")]))
    if d["id"] not in bootstrap_ids:
        architecture_problems = architecture_gate_problems(by_id, config)
        problems.extend(f"adaptive architecture gate: {p}" for p in architecture_problems)
    for dep in d["depends"]:
        dd = by_id.get(dep)
        if not dd:
            problems.append(f"upstream dependency {dep} is missing from the manifest")
        elif dd["applicability"] == "active" and dd["status"] not in SKIP:
            if dd["status"] != "approved":
                problems.append(f"upstream dependency {dep} is '{dd['status']}', not approved")
            else:
                dep_fp = safe_document_path(dd["path"]) if not dd["path"].endswith("/") else None
                dep_problem = approval_problem(dd, dep_fp, approvals)
                if dep_problem:
                    problems.append(f"upstream dependency {dep}: {dep_problem}")
    # Verify the complete ancestry of any dependencies that are already approved. A
    # direct dependency can have a valid hash while one of its own approved inputs is stale.
    problems.extend(approved_ancestor_integrity_problems([d], by_id, approvals))
    # Preserve order while avoiding duplicate diagnostics from direct + transitive checks.
    problems = list(dict.fromkeys(problems))
    if problems:
        print(f"Cannot approve {d['id']}:")
        for p in problems:
            print(f"  - {p.replace('approved but ', '')}")
        return 1
    version = d["version"]
    prev = approvals.get(d["id"])
    major, minor = (int(x) for x in version.split(".")[:2])
    if major == 0:
        version = "1.0"
    elif prev and prev.get("version") == version:
        version = f"{major}.{minor + 1}"
        print(f"Previously approved at {prev.get('version')}; version bumped to {version}.")
    updates = {"Status": "approved", "Version": version, "Last updated": today()}
    if not update_manifest_row(d["id"], updates):
        print("Could not update the manifest row.")
        return 2
    front_matter_error = None
    try:
        front_matter_updated = update_front_matter_fields(
            fp, {"status": "approved", "version": version, "last_updated": today()})
        if not front_matter_updated:
            front_matter_error = "the front-matter updater reported that no update was made"
    except (OSError, ValueError) as exc:
        front_matter_error = str(exc)
    if front_matter_error:
        # Do not leave a false 'approved' status in the manifest when no approval
        # artifact has been recorded. Cross-file I/O is not transactional, so report
        # the reconciliation path if even this best-effort rollback fails.
        try:
            manifest_restored = update_manifest_row(d["id"], {
                "Status": d["status"], "Version": d["version"], "Last updated": d["last_updated"]})
        except (OSError, ValueError) as exc:
            manifest_restored = False
            rollback_error = str(exc)
        else:
            rollback_error = "manifest row was not found or could not be updated"
        print(f"ERROR: front matter could not be synchronized for approval: {front_matter_error}")
        if manifest_restored:
            print(f"Manifest workflow fields were restored to {d['status']}/{d['version']}; no approval registry row or approval event was written. Verify the document front matter, then retry after resolving the I/O issue.")
        else:
            print(f"WARNING: manifest rollback also failed ({rollback_error}). The manifest and document may disagree; manually reconcile them before continuing.")
        return 2
    digest = approval_fingerprint(read(fp), next(x for x in load_manifest() if x["id"] == d["id"]))
    approval_path = workspace_paths().approvals
    append_table_row(approval_path, [d["id"], version, today(), args.by, evidence, digest])
    event = build_state_event("approval", document_id=d["id"], from_status="in-review", to_status="approved",
                              reason=evidence, actor=args.by, version=version, fingerprint=digest,
                              approval_registry=approval_path.relative_to(workspace_paths().root).as_posix())
    if not persist_state_events([event], f"Approval of {d['id']}"):
        return 2
    print(f"{d['id']} approved at version {version} by {args.by}; approval fingerprint {digest} recorded in "
          f"{approval_path.relative_to(workspace_paths().root).as_posix()}.")
    print("Next: run `python bp.py status --write`, record the decision in _control/logs/sessions/ session log.")
    return 0


def cmd_set_status(args) -> int:
    new = args.status
    docs = load_manifest()
    d = next((x for x in docs if x["id"] == args.doc_id), None)
    if not d:
        print(f"Unknown document ID: {args.doc_id}")
        return 2
    if new == "approved":
        print("Use `approve DOC_ID --evidence ...` for approval; status cannot be set to 'approved' directly.")
        return 2
    cur = d["status"]
    if new == cur:
        print(f"{d['id']} is already '{cur}'.")
        return 0
    if new not in TRANSITIONS.get(cur, set()):
        allowed = ", ".join(sorted(TRANSITIONS.get(cur, set()))) or "none"
        print(f"Transition {cur} -> {new} is not allowed. From '{cur}' you can go to: {allowed}"
              + ("; approval uses the `approve` command." if cur == "in-review" else "."))
        return 2
    if new in ("needs-revision", "superseded") and not (args.reason or "").strip():
        print(f"Setting '{new}' requires --reason so the ripple is auditable.")
        return 2
    folder = d["path"].endswith("/")
    if new == "expanded" and not folder:
        print("Only repeatable folder rows can be set to 'expanded'.")
        return 2
    fp = None if folder else safe_document_path(d["path"])
    needs_file = new in ("drafting", "in-review", "needs-revision", "interviewing") and not folder
    if needs_file and not (fp and fp.exists()) and new != "interviewing":
        print(f"docs/{d['path']} does not exist; run `scaffold --only {d['id']}` first.")
        return 2
    if new == "in-review":
        raw = read(fp)
        fm = front_matter(raw) or {}
        if not fm.get("summary"):
            print("A document entering review needs a front-matter summary (what it establishes and decides).")
            return 2
        for sev, msg in lint_document(raw, "in-review", None):
            print(f"  note: {msg}")
    if not update_manifest_row(d["id"], {"Status": new, "Last updated": today()}):
        print("Could not update the manifest row.")
        return 2
    if fp and fp.exists() and not update_front_matter_fields(fp, {"status": new, "last_updated": today()}):
        print("ERROR: manifest status changed but front matter could not be synchronized; reconcile before continuing.")
        return 2
    event = build_state_event("status_transition", document_id=d["id"], from_status=cur, to_status=new,
                              reason=(args.reason or "").strip() or None, actor=args.by)
    if not persist_state_events([event], f"Status transition for {d['id']}"):
        return 2
    print(f"{d['id']}: {cur} -> {new}.")
    if new == "needs-revision":
        print("Record it in _control/STATE.md's ripple queue and _control/registry/CHANGELOG.md; re-approval will bump the version.")
    return 0


# ----------------------------------------------------------------- generated index
def load_questions():
    path = workspace_paths().questions
    out = {}
    if not path.exists():
        return out
    for header, rows in parse_tables(strip_noise(read(path))):
        h = [c.lower() for c in header]
        if "id" in h and "status" in h:
            for r in rows:
                if len(r) >= len(h) and FULL_ID_RE.match(clean(r[h.index("id")])):
                    out[clean(r[h.index("id")])] = {
                        "question": r[h.index("question")] if "question" in h else "",
                        "status": clean(r[h.index("status")]).lower(),
                        "blocks": r[h.index("blocks")] if "blocks" in h else ""}
    return out


def ids_defined_in(raw: str) -> dict:
    text = strip_noise(raw)
    ids = set()
    for header, rows in parse_tables(text):
        for r in rows:
            if r and FULL_ID_RE.match(clean(r[0])):
                ids.add(clean(r[0]))
    for m in re.finditer(r"^#{1,6}\s+`?(" + ID_RE.pattern + r")", text, re.M):
        ids.add(m.group(1))
    groups = {}
    for i in ids:
        prefix, num = i.rsplit("-", 1)
        groups.setdefault(prefix, []).append(int(num))
    parts = []
    for prefix in sorted(groups):
        nums = sorted(groups[prefix])
        span = f"{prefix}-{nums[0]:03d}" if len(nums) == 1 else f"{prefix}-{nums[0]:03d}…{nums[-1]:03d}"
        parts.append(f"{span} ({len(nums)})")
    return parts


INDEX_DATE_RE = re.compile(r"<!-- generated: [0-9-]+ -->")


def build_index(date: str) -> str:
    docs = load_manifest()
    config = load_workspace_config()
    profile = str(config.get("profile", "standard")).lower()
    phases = load_phases()
    per = progress(docs, profile)
    tw = sum(p["w"] for p in per.values())
    ts = sum(p["score"] for p in per.values())
    approved = sum(p["done"] for p in per.values())
    total = sum(p["n"] for p in per.values())
    overall = round(ts / tw) if tw else 0
    questions = load_questions()
    open_q = [q for q, v in questions.items() if v["status"] in ("open", "blocked", "")]
    sessions = sorted(workspace_paths().sessions.glob("session-*.md")) if workspace_paths().sessions.exists() else []
    latest = sessions[-1].name if sessions else "none yet"
    attention = [d for d in docs if d["status"] in ("in-review", "needs-revision") and d["applicability"] == "active"]
    lines = [
        "# INDEX.md — Generated documentation index",
        "",
        f"<!-- generated: {date} -->",
        "> **Generated file — do not hand-edit.** Refresh with `python bp.py status --write` "
        "(or `index`). Use this to decide which documents to open: summaries come from each document's "
        "front matter, ID ranges from the documents that define them. `_control/registry/MANIFEST.md` remains the operational inventory.",
        "",
        f"- **Profile:** {profile} · **Approved:** {approved} / {total} active in-profile documents · **Workflow progress:** {overall}%",
        f"- **Open questions:** {len(open_q)} · **Latest session log:** `{latest}`",
    ]
    if attention:
        lines.append("- **Needs attention:** " + ", ".join(f"{d['id']} ({d['status']})" for d in attention))
    lines.append("")
    for ph in sorted({d["phase"] for d in docs if d["phase"] >= 0}):
        group = [d for d in docs if d["phase"] == ph]
        lines += [f"## Phase {ph} — {phases.get(ph, 'UNREGISTERED')}", "",
                  "| Doc | Title | Applic. | Status | Maturity | Ver | Size | Defines IDs | Summary |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for d in group:
            fp = safe_document_path(d["path"]) if d["path"] and not d["path"].endswith("/") else None
            exists = bool(fp and fp.exists())
            raw = read(fp) if exists else ""
            fm = front_matter(raw) or {} if exists else {}
            summary = (fm.get("summary") or "").replace("|", "/").replace("\n", " ")
            if len(summary) > 190:
                summary = summary[:187] + "…"
            title = f"[{d['title']}]({rel_link(workspace_paths().index, fp)})" if exists else d["title"]
            if not exists:
                summary = "_not scaffolded_" if d["applicability"] == "active" else f"_{d['applicability']}_"
            n_lines = raw.count("\n") + 1 if exists else 0
            size = f"~{int(round(n_lines / 10.0)) * 10} lines" if exists else "—"
            defined = "; ".join(ids_defined_in(raw)) if exists else ""
            lines.append(f"| {d['id']} | {title} | {d['applicability']} | {d['status']} | {d['maturity']} | "
                         f"{d['version']} | {size} | {defined or '—'} | {summary or '—'} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def index_is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    normalise = lambda t: INDEX_DATE_RE.sub("<!-- generated -->", t.replace("\r\n", "\n")).strip()
    return normalise(read(path)) != normalise(build_index(today()))


def write_index() -> Path:
    path = workspace_paths().index
    write(path, build_index(today()))
    return path


def cmd_index(args) -> int:
    path = workspace_paths().index
    if args.check:
        if index_is_stale(path):
            print(f"{path.relative_to(workspace_paths().root).as_posix()} is missing or stale. Run `python bp.py index`.")
            return 1
        print("INDEX.md is current.")
        return 0
    write_index()
    print(f"Wrote {path.relative_to(workspace_paths().root).as_posix()}")
    return 0


# ----------------------------------------------------------------- main
def parse_framework_version(value: str) -> bool:
    """Accept stable/prerelease semantic versions, including 3.0.0-alpha.1."""
    return bool(re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", value))


def ensure_supported_python(version_info=None) -> bool:
    """Return whether the current interpreter meets the documented 3.11 minimum."""
    version_info = version_info or sys.version_info
    return tuple(version_info[:2]) >= (3, 11)


def main(argv=None) -> int:
    if not ensure_supported_python():
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"Project Blueprint requires Python 3.11 or newer; detected {current}.")
        print("Windows: use `py -3.11` (or another installed 3.11+ interpreter).")
        print("POSIX/WSL: use `python3.11` or `python3`.")
        return 3
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles
    except Exception:
        pass
    try:
        manifest_data = json.loads(read(workspace_paths().framework_manifest))
        framework_version = str(manifest_data.get("framework_version", "unknown"))
    except (OSError, json.JSONDecodeError, ValueError):
        framework_version = "unknown"
    ap = argparse.ArgumentParser(description="Blueprint documentation framework helper")
    ap.add_argument("--version", action="version", version=f"Project Blueprint Framework {framework_version}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate the complete Markdown workspace")
    c.add_argument("--strict", action="store_true", help="undefined IDs become errors")
    c.add_argument("--readiness", action="store_true", help="report mechanical incompleteness signals in active, in-profile drafting/review documents; advisory only")
    c.add_argument("--gate", type=int, help="also verify readiness of phase N (implies --strict)")
    c.add_argument("--profile", choices=sorted(PROFILE_TIERS), help="profile to validate / gate against (default: workspace profile)")
    sa = sub.add_parser("audit-state", help="read-only reconciliation of STATE, manifest, approvals and session history")
    sa.add_argument("--strict", action="store_true", help="return nonzero when advisory drift is reported")
    s = sub.add_parser("status", help="progress per phase and applicability/profile counts")
    s.add_argument("--write", action="store_true", help="update the dashboard block in _control/STATE.md")
    s.add_argument("--profile", choices=sorted(PROFILE_TIERS), help="temporary profile override")
    sc = sub.add_parser("scaffold", help="create selected active document skeletons within the selected profile")
    group = sc.add_mutually_exclusive_group()
    group.add_argument("--phase", type=int, help="create eligible skeletons in one registered phase")
    group.add_argument("--only", help="comma-separated document IDs, e.g. D0.01,D0.02")
    group.add_argument("--all", action="store_true", help="explicitly create all active, in-profile skeletons")
    sc.add_argument("--profile", choices=sorted(PROFILE_TIERS), help="temporary profile override")
    sc.add_argument("--dry-run", action="store_true")
    sc.add_argument("--override-architecture-gate", action="store_true",
                    help="explicitly bypass the adaptive architecture approval guard (requires a reason; records an audit log)")
    sc.add_argument("--override-reason", default="",
                    help="required explanation when --override-architecture-gate is used")
    ma = sub.add_parser("maturity", help="set outline/working/detailed maturity and synchronize metadata")
    ma.add_argument("doc_id")
    ma.add_argument("level", choices=sorted(MATURITIES))
    ma.add_argument("--reason", default="", help="optional reason for the maturity change")
    ma.add_argument("--by", default="operator", help="actor label for the workspace event log")
    apc = sub.add_parser("applicability", help="set active/conditional/deferred/excluded applicability with a required reason")
    apc.add_argument("doc_id")
    apc.add_argument("level", choices=sorted(APPLICABILITY_VALUES))
    apc.add_argument("--reason", required=True, help="why this scope/applicability decision is justified")
    apc.add_argument("--by", default="operator", help="actor label for the workspace event log")
    prof = sub.add_parser("profile", help="show or set the workspace's default documentation depth profile")
    prof.add_argument("name", nargs="?", choices=sorted(PROFILE_TIERS))
    prof.add_argument("--reason", default="", help="optional reason for the profile change")
    prof.add_argument("--by", default="operator", help="actor label for the workspace event log")
    gr = sub.add_parser("graph", help="print Mermaid graph with content dependencies only")
    gr.add_argument("--profile", choices=sorted(PROFILE_TIERS), help="temporary profile override")
    se = sub.add_parser("session", help="create next session log")
    ap_ = sub.add_parser("approve", help="record explicit owner approval (lint + version + metadata-bound SHA-256 fingerprint)")
    ap_.add_argument("doc_id")
    ap_.add_argument("--evidence", required=True, help="where/how the owner approved (their words, or a session-log reference)")
    ap_.add_argument("--by", default="owner", help="approver name (default: owner)")
    ss = sub.add_parser("set-status", help="change workflow status, keeping manifest and front matter in sync")
    ss.add_argument("doc_id")
    ss.add_argument("status", choices=[x for x in STATUSES])
    ss.add_argument("--reason", default="", help="reason for the status change (required for needs-revision and superseded)")
    ss.add_argument("--by", default="operator", help="actor label for the workspace event log")
    ix = sub.add_parser("index", help="regenerate _control/registry/INDEX.md from front-matter summaries")
    ix.add_argument("--check", action="store_true", help="exit 1 if the index is missing or stale")
    imp = sub.add_parser("impact", help="show content dependents; D0.02 additionally shows structural review candidates")
    imp.add_argument("target", help="document ID such as D4.03 or stable ID such as FR-001")
    imp.add_argument("--profile", choices=sorted(PROFILE_TIERS), help="temporary profile override")
    args = ap.parse_args(argv)
    commands = {"check": cmd_check, "audit-state": cmd_audit_state, "status": cmd_status, "scaffold": cmd_scaffold,
                "maturity": cmd_maturity, "applicability": cmd_applicability, "profile": cmd_profile,
                "graph": cmd_graph, "session": cmd_session, "impact": cmd_impact,
                "approve": cmd_approve, "set-status": cmd_set_status, "index": cmd_index}
    try:
        return commands[args.cmd](args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    mode, context = discover_context(start=Path.cwd(), launcher_path=Path(__file__).resolve())
    if mode != "workspace":
        print("ERROR: workspace runtime requires a live _control/WORKSPACE.json marker; use the root bp.py launcher.")
        raise SystemExit(2)
    set_workspace_paths(context)
    sys.exit(main())
