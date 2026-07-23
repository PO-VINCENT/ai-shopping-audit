from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "skills" / "catalogready"


class SkillTests(unittest.TestCase):
    def _frontmatter(self) -> str:
        text = (_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")
        return match.group(1)

    def test_frontmatter_has_required_fields(self) -> None:
        frontmatter = self._frontmatter()
        # Agent Skills spec: name must match the directory name.
        self.assertRegex(frontmatter, r"(?m)^name: catalogready$")
        self.assertIn("description:", frontmatter)

    def test_skill_references_only_real_mcp_tools(self) -> None:
        body = (_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        mcp_source = (_REPO_ROOT / "src" / "catalogready" / "mcp_server.py").read_text(
            encoding="utf-8"
        )
        for tool in set(re.findall(r"catalogready_[a-z_]+", body)):
            self.assertIn(f"def {tool}(", mcp_source, f"skill names unknown tool: {tool}")

    def test_skill_is_discoverable_by_claude_and_codex(self) -> None:
        for client_dir in (".claude", ".codex"):
            link = _REPO_ROOT / client_dir / "skills" / "catalogready" / "SKILL.md"
            self.assertTrue(link.exists(), f"{client_dir} skill link is broken")

    def test_skill_carries_no_secrets_guidance_violations(self) -> None:
        body = (_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        # The skill must repeat the repo's key-handling rule, not undermine it.
        self.assertIn("Never pass API keys", body)
