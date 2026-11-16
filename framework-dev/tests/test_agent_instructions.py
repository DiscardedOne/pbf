"""Regression test for the current shipped AGENTS operating contract."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
if str(SOURCE_ROOT / "_framework" / "tools") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "_framework" / "tools"))
from blueprint_framework.source_cli import validate_agents_instructions  # noqa: E402


class AgentInstructionsTests(unittest.TestCase):
    def test_agents_file_contains_shortcuts_state_line_and_reference_map_within_target(self):
        agents = SOURCE_ROOT / "starter" / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        self.assertLessEqual(len(content), 12_000)
        self.assertEqual([], validate_agents_instructions(agents))
        for expected in (
            "## 9. Owner shortcuts", "`status`", "`next`", "`checkpoint`", "`gate`",
            "`audit`", "`park: <idea>`", "`revisit <doc/topic>`", "`replan`",
            "`explain <x>`", "`wrap up`", "## 10. State line",
            "End every substantive message", "## 11. On-demand reference map",
            "_framework/CONVERSATIONAL-WORKFLOW.md", "_framework/QUESTION-BANK.md",
            "_framework/ADAPTIVE-DOCUMENT-ARCHITECTURE.md",
        ):
            self.assertIn(expected, content)


if __name__ == "__main__":
    unittest.main()
