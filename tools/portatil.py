"""Pacotes para usar as skills fora do Claude Code (chamado por tools/build.py).

dist/claude-ai/<skill>.zip        uma skill autocontida por zip: Claude.ai (Configurações > Capacidades > Skills)
dist/citacoes-abnt-skills.zip     as três skills autocontidas: .agents/skills (Codex, Gemini CLI, Cursor, Copilot,
                                  opencode e outros que seguem o padrão Agent Skills)
dist/chat/instrucoes.txt          instruções para ChatGPT (GPT ou Projeto), Gemini (Gem), Copilot, Perplexity,
                                  Projeto do Claude.ai: no máximo 8.000 caracteres
dist/chat/conhecimento-*.md       arquivos de conhecimento para anexar junto com as instruções
dist/chat/citacoes-abnt-scripts.zip  scripts e dados para chats com execução de código
dist/citacoes-abnt-agents.md      instruções + uso dos scripts, para salvar como AGENTS.md, GEMINI.md ou regra do Cursor

"Autocontida" quer dizer: a pasta da skill leva scripts/, data/ e references/ dentro dela, e o SKILL.md
é reescrito para apontar para esses caminhos. No repositório, as três skills dividem a raiz do plugin.
"""
import io
import re
import zipfile
from pathlib import Path

DATA_FIXA = (2026, 11, 1, 0, 0, 0)  # zip reprodutível: --verificar compara bytes
LIMITE_INSTRUCOES = 8000             # campo de instruções do GPT personalizado
SKILLS = ("biblioteca-citacoes", "checador-citacoes", "abnt-formatacao")

CAMINHO_SCRIPTS = re.compile(
    r"Os scripts ficam na pasta `scripts/` da raiz do plugin: `\$\{CLAUDE_PLUGIN_ROOT\}/scripts`, ou `\.\./\.\./scripts` "
    r"a partir da pasta desta skill\.")


class ErroPacote(Exception):
    pass


_GERADO = {}  # {Path: str|bytes} gerado nesta rodada do build; tem precedência sobre o disco


def _bytes(p):
    v = _GERADO.get(p)
    if v is None:
        return p.read_bytes()
    return v if isinstance(v, bytes) else v.encode("utf-8")


def _texto(p):
    return _bytes(p).decode("utf-8")


def _glob(pasta, padrao):
    achados = set(pasta.glob(padrao)) | {p for p in _GERADO if p.parent == pasta and p.match(padrao)}
    return sorted(achados)


def _rglob(pasta, padrao):
    achados = set(pasta.rglob(padrao)) | {p for p in _GERADO if pasta in p.parents and p.match(padrao)}
    return sorted(achados)


def reescrever_skill(texto, nome):
    novo, n = CAMINHO_SCRIPTS.subn("Os scripts ficam na pasta `scripts/` desta skill.", texto)
    if n != 1:
        raise ErroPacote(f"{nome}/SKILL.md: frase do caminho dos scripts mudou; ajuste CAMINHO_SCRIPTS em tools/portatil.py")
    novo = novo.replace("../abnt-formatacao/references/", "references/")
    novo = novo.replace("`THIRD_PARTY_NOTICES.md`, na raiz do plugin", "`THIRD_PARTY_NOTICES.md`, nesta pasta")
    if "../" in novo or "CLAUDE_PLUGIN_ROOT" in novo:
        raise ErroPacote(f"{nome}/SKILL.md: sobrou caminho relativo ao plugin no pacote autocontido")
    return novo


def arquivos_skill(raiz, nome):
    """{caminho dentro da pasta da skill: bytes} para a versão autocontida."""
    saida = {"SKILL.md": reescrever_skill(_texto(raiz / "skills" / nome / "SKILL.md"), nome).encode()}
    for p in _glob(raiz / "scripts", "*.py"):
        saida[f"scripts/{p.name}"] = _bytes(p)
    saida["data/instituicoes.json"] = _bytes(raiz / "data" / "instituicoes.json")
    refs = raiz / "skills" / "abnt-formatacao" / "references"
    for p in _rglob(refs, "*.md"):
        saida[f"references/{p.relative_to(refs).as_posix()}"] = _bytes(p)
    for extra in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        saida[extra] = _bytes(raiz / extra)
    return saida


def zipar(arquivos):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in sorted(arquivos):
            info = zipfile.ZipInfo(nome, DATA_FIXA)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, arquivos[nome])
    return buf.getvalue()


def conhecimento_normas(raiz):
    pasta = raiz / "skills" / "abnt-formatacao" / "references" / "normas"
    ordem = ["vigencia.md", "nbr-6023-referencias.md", "nbr-10520-citacoes.md", "nbr-14724-estrutura.md",
             "regras-do-validador.md"]
    partes = ["# Conhecimento: normas ABNT (citacoes-abnt-skill)\n\nResumo próprio de guias públicos de bibliotecas. "
              "As normas ABNT são pagas e não são reproduzidas aqui.\n"]
    for nome in ordem:
        partes.append(_texto(pasta / nome))
    sobra = {p.name for p in _glob(pasta, "*.md")} - set(ordem)
    if sobra:
        raise ErroPacote(f"arquivo de norma fora do pacote de chat: {sorted(sobra)}")
    return "\n\n---\n\n".join(partes)


def conhecimento_instituicoes(raiz, dados, perfil_md):
    pasta = raiz / "skills" / "abnt-formatacao" / "references" / "instituicoes"
    partes = ["# Conhecimento: perfis de formatação de 50 instituições (citacoes-abnt-skill)\n\n"
              "Procure a instituição pelo nome ou pela sigla. Fora da lista, use o perfil \"Padrão ABNT\".\n",
              _texto(pasta / "padrao-abnt.md"), _texto(pasta / "index.md")]
    partes += [perfil_md(i).replace("Para os scripts: `--instituicao", "Id para os scripts: `--instituicao") for i in dados]
    return "\n\n---\n\n".join(partes)


AGENTS_EXTRA = """

## Scripts (agentes com terminal: Codex, Gemini CLI, Cursor, Copilot, Aider, opencode)

Clone o repositório uma vez: `git clone https://github.com/kayquer/citacoes-abnt-skill`. Os scripts estão em
`citacoes-abnt-skill/scripts/` e usam só Python 3, sem dependências (no Windows, `py -3`).

```bash
python3 scripts/checar_referencias.py trabalho.docx --json        # existência das obras (precisa de internet)
python3 scripts/conferir_citacoes.py trabalho.docx --json         # citação x referência e forma ABNT
python3 scripts/biblioteca.py adicionar --doi 10.1038/nature14539  # biblioteca.json na pasta atual
python3 scripts/biblioteca.py citar <id> --pagina 45
python3 scripts/biblioteca.py exportar --formato abnt|bib|ris|csl --saida refs.md
python3 scripts/gerar_modelo_docx.py --instituicao usp --tipo tcc --saida modelo.docx
```

Os perfis das instituições ficam em `skills/abnt-formatacao/references/instituicoes/<id>.md` e as normas em
`skills/abnt-formatacao/references/normas/`. Código de saída 1 ou 2 indica achados, não falha do script.
Se o seu agente aceita Agent Skills (pasta `.agents/skills/`), prefira instalar `dist/citacoes-abnt-skills.zip`.
"""


def gerar(raiz, dados, perfil_md, gerado):
    _GERADO.clear()
    _GERADO.update(gerado)
    instrucoes = _texto(raiz / "portatil" / "instrucoes.md")
    if len(instrucoes) > LIMITE_INSTRUCOES:
        raise ErroPacote(f"portatil/instrucoes.md tem {len(instrucoes)} caracteres; o limite é {LIMITE_INSTRUCOES}")
    dist = raiz / "dist"
    saidas = {}
    todas = {}
    for nome in SKILLS:
        arquivos = arquivos_skill(raiz, nome)
        saidas[dist / "claude-ai" / f"{nome}.zip"] = zipar({f"{nome}/{k}": v for k, v in arquivos.items()})
        todas.update({f"{nome}/{k}": v for k, v in arquivos.items()})
    saidas[dist / "citacoes-abnt-skills.zip"] = zipar(todas)
    scripts = {f"scripts/{p.name}": _bytes(p) for p in _glob(raiz / "scripts", "*.py")}
    scripts["data/instituicoes.json"] = _bytes(raiz / "data" / "instituicoes.json")
    scripts["LICENSE"] = _bytes(raiz / "LICENSE")
    saidas[dist / "chat" / "citacoes-abnt-scripts.zip"] = zipar(scripts)
    saidas[dist / "chat" / "instrucoes.txt"] = instrucoes
    saidas[dist / "chat" / "conhecimento-normas.md"] = conhecimento_normas(raiz)
    saidas[dist / "chat" / "conhecimento-instituicoes.md"] = conhecimento_instituicoes(raiz, dados, perfil_md)
    saidas[dist / "citacoes-abnt-agents.md"] = instrucoes.rstrip() + "\n" + AGENTS_EXTRA
    return saidas
