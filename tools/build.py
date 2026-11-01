"""Gera tudo o que deriva de data/: perfis das instituições, página do GitHub Pages e tabela do README.

    py -3 tools/build.py              gera
    py -3 tools/build.py --verificar  sai com 1 se algum arquivo gerado estiver defasado

Fontes:
    data/instituicoes-base.json   (dos CSVs, via tools/importar_csv.py)
    data/pesquisa/grupo*.json     (pesquisa nos manuais oficiais, com URL e data de conferência)
Saídas:
    data/instituicoes.json                                    base + pesquisa + perfil resolvido
    skills/abnt-formatacao/references/instituicoes/*.md       um perfil por instituição + índice
    docs/                                                     site (index, uma página por instituição, sitemap, llms.txt)
    dist/                                                     pacotes para Claude.ai, ChatGPT, Gemini e outros agentes (tools/portatil.py)
    README.md                                                 tabela entre <!-- instituicoes:inicio/fim -->
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import portatil  # noqa: E402
import site_gen  # noqa: E402

CONFERIDO = "2026-11"
VIGENTES = {"6023": "2025", "10520": "2023", "14724": "2024"}
PADRAO = {
    "papel": "A4", "margens_cm": {"sup": 3, "esq": 3, "inf": 2, "dir": 2}, "fonte_familia": "Arial", "fonte_pt": 12,
    "fonte_menor_pt": 10, "espacamento": 1.5, "recuo_paragrafo_cm": 1.25, "citacao_longa_recuo_cm": 4,
    "paginacao": "algarismos arábicos no canto superior direito, a 2 cm das bordas, a partir da primeira folha da parte textual; "
                 "as folhas pré-textuais são contadas, mas não numeradas",
    "sistema_chamada": "autor-data",
}
FAMILIAS = ["Times New Roman", "Arial", "Verdana", "Carlito", "Liberation Sans", "Liberation Serif", "Helvetica", "Calibri"]


def _ano(texto, padrao):
    m = re.search(r"(19|20)\d{2}", str(texto or ""))
    return m.group(0) if m else padrao


def resolver_perfil(regras):
    """Perfil aplicável: o que o manual diz, completado pelo padrão ABNT. 'origem' diz de onde veio cada campo."""
    r = regras or {}
    p, origem = {}, {}

    def put(campo, valor, do_manual):
        p[campo] = valor
        origem[campo] = "manual" if do_manual else "padrao"

    m = r.get("margens_cm") or {}
    margens = {k: (m.get(k) if m.get(k) is not None else PADRAO["margens_cm"][k]) for k in ("sup", "esq", "inf", "dir")}
    put("margens_cm", margens, bool(m) and all(m.get(k) is not None for k in margens))
    fonte = r.get("fonte") or ""
    familia = next((f for f in FAMILIAS if f.lower() in fonte.lower()), None)
    put("fonte_familia", familia or PADRAO["fonte_familia"], bool(familia))
    put("fonte_alternativas", [f for f in FAMILIAS if f.lower() in fonte.lower()], bool(familia))
    tam = re.search(r"\b(1[0-4])\b", fonte)
    put("fonte_pt", int(tam.group(1)) if tam else 12, bool(tam))
    menor = re.search(r"\b(9|10|11)\b", r.get("fonte_menor") or "")
    put("fonte_menor_pt", int(menor.group(1)) if menor else PADRAO["fonte_menor_pt"], bool(menor))
    esp = (r.get("espacamento") or "").lower()
    if esp.startswith("duplo"):
        put("espacamento", 2.0, True)
    elif re.match(r"\s*1[,.]5", esp):
        put("espacamento", 1.5, True)
    else:
        put("espacamento", PADRAO["espacamento"], False)
    rec = r.get("recuo_paragrafo_cm")
    put("recuo_paragrafo_cm", float(rec) if isinstance(rec, (int, float)) else PADRAO["recuo_paragrafo_cm"],
        isinstance(rec, (int, float)))
    cit = r.get("citacao_longa_recuo_cm")
    put("citacao_longa_recuo_cm", float(cit) if isinstance(cit, (int, float)) else PADRAO["citacao_longa_recuo_cm"],
        isinstance(cit, (int, float)))
    put("paginacao", r.get("paginacao") or PADRAO["paginacao"], bool(r.get("paginacao")))
    put("sistema_chamada", r.get("sistema_chamada") or PADRAO["sistema_chamada"], bool(r.get("sistema_chamada")))
    e6023 = _ano(r.get("edicao_6023"), None)
    # O formatador conhece 2018 e 2025; manual ainda na 6023:2002 cai no perfil 2018 (o mais próximo) com aviso.
    put("edicao_6023", {"2025": "2025", None: VIGENTES["6023"]}.get(e6023, "2018"), e6023 is not None)
    e10520 = _ano(r.get("edicao_10520"), None)
    put("edicao_10520", "2002" if e10520 == "2002" else VIGENTES["10520"], e10520 is not None)
    put("edicao_14724", _ano(r.get("edicao_14724"), VIGENTES["14724"]), _ano(r.get("edicao_14724"), None) is not None)
    p["origem"] = origem
    p["manual_desatualizado"] = (e6023 not in (None, "2025")) or e10520 == "2002" or \
        (_ano(r.get("edicao_14724"), None) not in (None, "2024"))
    return p


def carregar_dados():
    base = json.loads((RAIZ / "data" / "instituicoes-base.json").read_text(encoding="utf-8"))
    pesquisa = {}
    for f in sorted((RAIZ / "data" / "pesquisa").glob("grupo*.json")):
        for item in json.loads(f.read_text(encoding="utf-8")):
            pesquisa[item["id"]] = item
    saida = []
    for inst in base:
        p = pesquisa.get(inst["id"], {})
        item = dict(inst)
        for campo in ("manual", "fontes_extras", "regras", "variacoes_area", "particularidades", "modelos", "observacoes"):
            item[campo] = p.get(campo)
        item["conferido_em"] = p.get("conferido_em") or CONFERIDO
        item["tem_manual"] = bool((p.get("manual") or {}).get("url"))
        item["perfil"] = resolver_perfil(p.get("regras"))
        saida.append(item)
    return saida


# ---------------------------------------------------------------- perfis em markdown (lidos pela skill)

def _cm(v):
    return f"{v:g}".replace(".", ",") + " cm"


def _marca(p, campo):
    if p["origem"].get(campo) == "manual":
        return ""
    if campo == "fonte_familia":
        return " *(costume: a NBR 14724 não fixa a família e o manual não especifica)*"
    return " *(padrão ABNT: o manual não especifica)*"


def edicoes_txt(p, md=True):
    """'NBR 6023:2018, NBR 10520:2023*' com * quando a edição não vem do manual (vale a vigente)."""
    partes = []
    for n in ("6023", "10520", "14724"):
        manual = p["origem"].get(f"edicao_{n}") == "manual"
        partes.append(f"NBR {n}:{p[f'edicao_{n}']}" + ("" if manual else "*"))
    return ", ".join(partes)


def perfil_md(i):
    p = i["perfil"]
    m = p["margens_cm"]
    linhas = [f"# {i['nome']}", "",
              f"**Sigla**: {i['sigla']} | **Tipo**: {i['tipo']}" + (f" | **UF**: {i['uf']}" if i.get("uf") else "") +
              f" | **Conferido em**: {i['conferido_em']}", ""]
    man = i.get("manual") or {}
    if man.get("url"):
        linhas += [f"**Manual de referência**: [{man.get('titulo')}]({man['url']})" +
                   (f" ({man.get('orgao')}, {man.get('ano')})" if man.get("orgao") else ""), ""]
    else:
        linhas += ["**Manual de referência**: não encontrado em fonte pública. Aplique a ABNT vigente e peça ao usuário o "
                   "manual do curso ou do programa. [VERIFICAR: manual da instituição]", ""]
    if p["manual_desatualizado"]:
        linhas += ["> **Atenção**: o manual cita edição anterior de alguma norma ABNT. Pergunte ao usuário se o curso ainda "
                   "exige essa edição ou se aceita a vigente (NBR 6023:2025, NBR 10520:2023, NBR 14724:2024).", ""]
    linhas += ["## Perfil aplicado", "",
               "| Elemento | Regra |", "|---|---|",
               f"| Papel | {i['regras'].get('papel') if i.get('regras') and i['regras'].get('papel') else 'A4'} |",
               f"| Margens | superior {_cm(m['sup'])}, esquerda {_cm(m['esq'])}, inferior {_cm(m['inf'])}, "
               f"direita {_cm(m['dir'])}{_marca(p, 'margens_cm')} |",
               f"| Fonte | {p['fonte_familia']} {p['fonte_pt']}" +
               (f" (aceitas: {', '.join(p['fonte_alternativas'])})" if len(p['fonte_alternativas']) > 1 else "") +
               f"{_marca(p, 'fonte_familia')} |",
               f"| Fonte menor | {p['fonte_menor_pt']} pt em citação longa, nota, legenda e fonte de ilustração"
               f"{_marca(p, 'fonte_menor_pt')} |",
               f"| Espaçamento | {str(p['espacamento']).replace('.', ',')}{_marca(p, 'espacamento')} |",
               f"| Recuo de parágrafo | {_cm(p['recuo_paragrafo_cm'])}{_marca(p, 'recuo_paragrafo_cm')} |",
               f"| Recuo da citação longa | {_cm(p['citacao_longa_recuo_cm'])}{_marca(p, 'citacao_longa_recuo_cm')} |",
               f"| Paginação | {p['paginacao']}{_marca(p, 'paginacao')} |",
               f"| Sistema de chamada | {p['sistema_chamada']}{_marca(p, 'sistema_chamada')} |",
               f"| Edições usadas | {edicoes_txt(p)} |",
               "", r"\* edição vigente aplicada porque o manual não informa qual usa.",
               "", f"Para os scripts: `--instituicao {i['id']}` (perfil em `data/instituicoes.json`).", ""]
    if i.get("regras"):
        r = i["regras"]
        detalhes = [(k, r.get(k)) for k in ("fonte", "fonte_menor", "espacamento") if r.get(k)]
        if detalhes:
            linhas += ["## Texto do manual (resumo)", ""] + [f"- **{k.replace('_', ' ')}**: {v}" for k, v in detalhes] + [""]
    if i.get("variacoes_area"):
        linhas += ["## Outras normas por área", ""]
        for v in i["variacoes_area"]:
            linhas.append(f"- {v.get('area')}: {v.get('norma')}" + (f" ([fonte]({v['fonte']}))" if v.get("fonte") else ""))
        linhas.append("")
    elif "Vancouver" in i["norma_csv"] or "APA" in i["norma_csv"]:
        linhas += ["## Outras normas por área", "",
                   f"- A planilha de origem indica \"{i['norma_csv']}\", mas o manual consultado não confirma. "
                   "[VERIFICAR: norma exigida pelo programa]", ""]
    if i.get("particularidades"):
        linhas += ["## Particularidades", ""] + [f"- {x}" for x in i["particularidades"]] + [""]
    if i.get("modelos"):
        linhas += ["## Modelos oficiais", ""] + [f"- {m_.get('tipo')}: {m_.get('url')}" for m_ in i["modelos"] if m_.get("url")] + [""]
    if i.get("observacoes"):
        linhas += ["## Observações da pesquisa", "", i["observacoes"], ""]
    fontes = [man] + (i.get("fontes_extras") or [])
    fontes = [f for f in fontes if f and f.get("url")]
    if fontes:
        linhas += ["## Fontes", ""] + [f"- [{f.get('titulo') or f['url']}]({f['url']})" for f in fontes] + [""]
    linhas += ["---", "Perfil gerado por `tools/build.py` a partir de `data/`. Regras de manual mudam: confira a data acima "
               "e o manual do seu programa antes da entrega."]
    return "\n".join(linhas) + "\n"


def indice_md(dados):
    linhas = ["# Perfis de instituições", "",
              f"{len(dados)} instituições. Conferido em {CONFERIDO}. Abra o arquivo `<id>.md` da instituição do usuário.", "",
              "| id | Instituição | Norma principal | Manual | Edições (6023, 10520, 14724) |", "|---|---|---|---|---|"]
    for i in dados:
        p = i["perfil"]
        linhas.append(f"| `{i['id']}` | {i['nome']} | {i['norma_csv']} | {'sim' if i['tem_manual'] else 'não encontrado'} | "
                      f"{edicoes_txt(p).replace('NBR ', '')} |")
    linhas += ["", r"\* edição vigente aplicada porque o manual não informa. Edição antiga sem asterisco (6023:2018, 10520:2002, "
               "14724:2011) vem do manual: pergunte se o curso ainda a exige.",
               "", "Instituição fora da lista: use o perfil `padrao-abnt` (regras gerais da NBR 14724:2024) e peça o manual."]
    return "\n".join(linhas) + "\n"


PADRAO_MD = """# Padrão ABNT (sem manual institucional)

Use quando a instituição não está na lista ou não tem manual público. Pergunte se há manual do curso.

| Elemento | Regra |
|---|---|
| Papel | A4 (21 cm × 29,7 cm) |
| Margens | anverso: superior e esquerda 3 cm, inferior e direita 2 cm (no verso, invertidas) |
| Fonte | 12 para o texto; menor (10 recomendado) para citação longa, nota, paginação, legenda e fonte de ilustração. A norma não fixa a família; Arial ou Times New Roman é o costume |
| Espaçamento | 1,5 no texto; simples em citação longa, nota, referência, legenda, natureza do trabalho e ficha catalográfica |
| Referências | espaço simples, alinhadas à esquerda, separadas por uma linha em branco de espaço simples |
| Recuo de parágrafo | 1,25 cm (costume; a NBR 14724 não fixa) |
| Citação longa | mais de 3 linhas, recuo de 4 cm (recomendado pela NBR 10520:2023), fonte menor, espaço simples, sem aspas |
| Paginação | arábicos no canto superior direito, a 2 cm das bordas, a partir da parte textual; pré-textuais contadas e não numeradas |
| Títulos de seção | numeração progressiva (NBR 6024), alinhados à esquerda, separados do texto por um espaço de 1,5; títulos sem indicativo numérico (errata, agradecimentos, listas, resumo, sumário, referências, apêndice, anexo) centralizados |
| Edições | NBR 6023:2025, NBR 10520:2023, NBR 14724:2024 |

Para os scripts: `--instituicao padrao-abnt`.
"""


def gerar_perfis(dados):
    pasta = RAIZ / "skills" / "abnt-formatacao" / "references" / "instituicoes"
    saidas = {pasta / f"{i['id']}.md": perfil_md(i) for i in dados}
    saidas[pasta / "index.md"] = indice_md(dados)
    saidas[pasta / "padrao-abnt.md"] = PADRAO_MD
    return saidas


def tabela_readme(dados):
    linhas = ["| Instituição | Tipo | Norma principal | Manual oficial |", "|---|---|---|---|"]
    for i in dados:
        man = i.get("manual") or {}
        link = f"[{man.get('ano') or 'link'}]({man['url']})" if man.get("url") else "não encontrado"
        pagina = f"[{i['sigla']}](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/{i['id']}.html)"
        linhas.append(f"| {pagina} | {i['tipo']} | {i['norma_csv']} | {link} |")
    return "\n".join(linhas)


def gerar_readme(dados):
    p = RAIZ / "README.md"
    if not p.exists():
        return {}
    texto = p.read_text(encoding="utf-8")
    novo = re.sub(r"(<!-- instituicoes:inicio -->).*?(<!-- instituicoes:fim -->)",
                  lambda m: m.group(1) + "\n" + tabela_readme(dados) + "\n" + m.group(2), texto, flags=re.S)
    return {p: novo}


def todas_saidas():
    dados = carregar_dados()
    saidas = {RAIZ / "data" / "instituicoes.json": json.dumps(dados, ensure_ascii=False, indent=2) + "\n"}
    saidas.update(gerar_perfis(dados))
    saidas.update(site_gen.gerar_site(dados, RAIZ, perfil_md))
    saidas.update(gerar_readme(dados))
    saidas.update(portatil.gerar(RAIZ, dados, perfil_md, saidas))
    return saidas


def _igual(p, conteudo):
    if not p.exists():
        return False
    return p.read_bytes() == conteudo if isinstance(conteudo, bytes) else p.read_text(encoding="utf-8") == conteudo


def main(argv):
    saidas = todas_saidas()
    if "--verificar" in argv:
        defasados = [str(p.relative_to(RAIZ)) for p, c in saidas.items()
                     if not _igual(p, c)]
        if defasados:
            print("Defasados (rode py -3 tools/build.py):\n  " + "\n  ".join(defasados))
            return 1
        print(f"OK: {len(saidas)} arquivos em dia")
        return 0
    for p, c in saidas.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if _igual(p, c):
            continue
        if isinstance(c, bytes):
            p.write_bytes(c)
        else:
            p.write_text(c, encoding="utf-8", newline="\n")
    print(f"{len(saidas)} arquivos gerados")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
