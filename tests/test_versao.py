"""Uma versão só em todos os manifestos.

`.claude-plugin/plugin.json` serve Claude Code, Codex, Copilot CLI e OpenClaw;
`plugin.json` (Agent Plugins v1) serve o Hermes; `gemini-extension.json`, o
Gemini CLI. Cinco arquivos com a mesma informação divergem no primeiro bump
feito à mão.
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILLS = ("abnt-formatacao", "biblioteca-citacoes", "checador-citacoes")


def versoes():
    v = {}
    for manifesto in (".claude-plugin/plugin.json", "plugin.json", "gemini-extension.json"):
        v[manifesto] = json.loads((RAIZ / manifesto).read_text(encoding="utf-8"))["version"]
    cff = re.search(r"^version: (\S+)$", (RAIZ / "CITATION.cff").read_text(encoding="utf-8"), re.MULTILINE)
    v["CITATION.cff"] = cff.group(1) if cff else None
    for nome in SKILLS:
        frente = (RAIZ / "skills" / nome / "SKILL.md").read_text(encoding="utf-8").split("\n---", 1)[0]
        achou = re.search(r'^\s+version:\s*"([^"]+)"\s*$', frente, re.MULTILINE)
        v[f"{nome}/SKILL.md"] = achou.group(1) if achou else None
    return v


class TestVersao(unittest.TestCase):
    def test_mesma_versao_em_todos_os_manifestos(self):
        v = versoes()
        self.assertNotIn(None, v.values(), v)
        self.assertEqual(len(set(v.values())), 1, v)

    def test_changelog_tem_a_versao(self):
        versao = versoes()["plugin.json"]
        self.assertIn(f"## {versao} (", (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_manifesto_agent_plugins(self):
        m = json.loads((RAIZ / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(m["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        # Agent Plugins 1.0.0, seção 5.2: só estes campos de topo; skills ficam em skills/<nome>/.
        permitidos = {"$schema", "name", "version", "description", "author", "homepage", "repository",
                      "license", "keywords", "extensions"}
        self.assertLessEqual(set(m), permitidos)


if __name__ == "__main__":
    unittest.main()
