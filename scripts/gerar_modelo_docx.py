"""Gera um modelo .docx ABNT com o perfil de uma instituição (sem dependências).

    py -3 scripts/gerar_modelo_docx.py --instituicao usp --tipo tcc --saida modelo-usp.docx
    py -3 scripts/gerar_modelo_docx.py --instituicao padrao-abnt --tipo artigo --saida artigo.docx
    py -3 scripts/gerar_modelo_docx.py --listar

Tipos: tcc, dissertacao, tese, artigo, projeto.
O modelo traz margens, fonte, espaçamento, recuo, estilos (Citação longa, Referência, Título sem número,
Legenda, Fonte da ilustração) e a paginação no canto superior direito a partir da parte textual, contando
desde a folha de rosto (NBR 14724:2024). Campos a preencher aparecem em azul, entre colchetes.
Para usar como modelo do Word: abra e salve como .dotx (Arquivo > Salvar como > Modelo do Word).
"""
import argparse
import json
import sys
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent.parent
TW_CM = 567  # twips por centímetro

PADRAO = {"margens_cm": {"sup": 3, "esq": 3, "inf": 2, "dir": 2}, "fonte_familia": "Arial", "fonte_pt": 12,
          "fonte_menor_pt": 10, "espacamento": 1.5, "recuo_paragrafo_cm": 1.25, "citacao_longa_recuo_cm": 4,
          "edicao_6023": "2025", "edicao_10520": "2023", "edicao_14724": "2024"}

GRAUS = {"tcc": ("Trabalho de Conclusão de Curso", "Graduação em [curso]"),
         "dissertacao": ("Dissertação", "Mestrado em [área]"),
         "tese": ("Tese", "Doutorado em [área]"),
         "projeto": ("Projeto de pesquisa", "[curso ou programa]"),
         "artigo": ("Artigo", "")}


def carregar_instituicoes():
    caminho = RAIZ / "data" / "instituicoes.json"
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else []


def perfil(inst_id):
    if inst_id in (None, "", "padrao-abnt"):
        return dict(PADRAO, nome="[Nome da instituição]", sigla="", id="padrao-abnt")
    for i in carregar_instituicoes():
        if i["id"] == inst_id or i["sigla"].lower() == inst_id.lower():
            return dict(PADRAO, **{k: v for k, v in i["perfil"].items() if k != "origem"},
                        nome=i["nome"], sigla=i["sigla"], id=i["id"])
    raise SystemExit(f"instituição não encontrada: {inst_id} (use --listar)")


# ---------------------------------------------------------------- XML

def run(texto, campo=False, negrito=False, caixa_alta=False):
    props = ""
    if negrito:
        props += "<w:b/>"
    if caixa_alta:
        props += "<w:caps/>"
    if campo:
        props += '<w:color w:val="1F4E9A"/><w:u w:val="single"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'


def texto_runs(texto, **kw):
    """Partes entre colchetes viram campo azul a preencher."""
    import re
    saida = []
    for parte in re.split(r"(\[[^\]]+\])", texto):
        if parte:
            saida.append(run(parte, campo=parte.startswith("["), **kw))
    return "".join(saida)


def par(texto="", estilo=None, alinhar=None, negrito=False, caixa_alta=False, quebra_antes=False, espaco_antes=None):
    ppr = ""
    if estilo:
        ppr += f'<w:pStyle w:val="{estilo}"/>'
    if quebra_antes:
        ppr += "<w:pageBreakBefore/>"
    if espaco_antes:
        ppr += f'<w:spacing w:before="{espaco_antes}"/>'
    if alinhar in ("center", "right"):
        ppr += '<w:ind w:firstLine="0"/>'  # ordem do esquema OOXML: spacing, ind, jc
    if alinhar:
        ppr += f'<w:jc w:val="{alinhar}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{texto_runs(texto, negrito=negrito, caixa_alta=caixa_alta)}</w:p>"


def secao(p, com_cabecalho, inicio=None, final=False):
    m = p["margens_cm"]
    cab = '<w:headerReference w:type="default" r:id="rIdHeader1"/>' if com_cabecalho else ""
    num = f'<w:pgNumType w:start="{inicio}"/>' if inicio else ""
    sect = (f'<w:sectPr>{cab}<w:type w:val="nextPage"/><w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="{round(m["sup"] * TW_CM)}" w:right="{round(m["dir"] * TW_CM)}" '
            f'w:bottom="{round(m["inf"] * TW_CM)}" w:left="{round(m["esq"] * TW_CM)}" '
            f'w:header="{2 * TW_CM}" w:footer="{TW_CM}" w:gutter="0"/>{num}</w:sectPr>')
    return sect if final else f"<w:p><w:pPr>{sect}</w:pPr></w:p>"


def corpo(p, tipo):
    natureza, grau = GRAUS[tipo]
    inst = p["nome"]
    ano = str(date.today().year)
    x = []
    if tipo == "artigo":
        x += [par("[Título do artigo]: [subtítulo]", "TituloSemNumero", "center", negrito=True),
              par("[Nome do autor]¹", alinhar="right"),
              par("RESUMO", "TituloSemNumero", "center", negrito=True),
              par("[Resumo em parágrafo único, de 100 a 250 palavras (NBR 6028:2021).]", "Resumo"),
              par("Palavras-chave: [termo um]; [termo dois]; [termo três].", "Resumo")]
    else:
        # Capa
        x += [par(inst, alinhar="center", negrito=True, caixa_alta=True), par("[Nome do autor]", alinhar="center", caixa_alta=True,
                                                                                espaco_antes=2400),
              par("[Título do trabalho]: [subtítulo]", alinhar="center", negrito=True, espaco_antes=3600),
              par("[Cidade]", alinhar="center", espaco_antes=4800), par(ano, alinhar="center"), secao(p, False)]
        # Folha de rosto (primeira página contada)
        x += [par("[Nome do autor]", alinhar="center", caixa_alta=True),
              par("[Título do trabalho]: [subtítulo]", alinhar="center", negrito=True, espaco_antes=3600),
              par(f"{natureza} apresentado(a) ao [programa ou curso] da {inst}, como requisito parcial para obtenção do "
                  f"título de {grau.split(' em ')[0] if ' em ' in grau else '[grau]'}" +
                  (f" em {grau.split(' em ')[1]}" if " em " in grau else "") + ".", "Natureza", espaco_antes=1200),
              par("Orientador(a): [nome].", "Natureza"),
              par("[Cidade]", alinhar="center", espaco_antes=3600), par(ano, alinhar="center")]
        x += [par("[Ficha catalográfica: gere no sistema da biblioteca da instituição e insira aqui, no verso da folha de rosto.]",
                  alinhar="center", quebra_antes=True)]
        if tipo != "projeto":
            x += [par("FOLHA DE APROVAÇÃO", "TituloSemNumero", "center", quebra_antes=True),
                  par("[Modelo da instituição: nome, título, natureza, data de aprovação e banca examinadora.]")]
        x += [par("RESUMO", "TituloSemNumero", "center", quebra_antes=True),
              par("[Resumo em parágrafo único, de 150 a 500 palavras (NBR 6028:2021).]", "Resumo"),
              par("Palavras-chave: [termo um]; [termo dois]; [termo três].", "Resumo"),
              par("ABSTRACT", "TituloSemNumero", "center", quebra_antes=True),
              par("[Abstract.]", "Resumo"), par("Keywords: [term one]; [term two].", "Resumo"),
              par("SUMÁRIO", "TituloSemNumero", "center", quebra_antes=True),
              par("[Atualize o sumário no Word: Referências > Sumário. Pré-textuais não entram (NBR 6027).]"),
              secao(p, False, inicio=1)]
    # Parte textual (numerada)
    secoes = ["INTRODUÇÃO", "DESENVOLVIMENTO", "CONCLUSÃO"] if tipo != "projeto" else \
        ["INTRODUÇÃO", "OBJETIVOS", "JUSTIFICATIVA", "REFERENCIAL TEÓRICO", "METODOLOGIA", "CRONOGRAMA"]
    for n, s in enumerate(secoes, 1):
        x.append(par(f"{n} {s}", "Titulo1", quebra_antes=(n > 1 and tipo != "artigo")))
        if n == 1:
            x += [par("[Texto. Citação curta entre aspas com chamada: \"trecho\" (Sobrenome, ano, p. 10).]"),
                  par("[Citação com mais de três linhas: recuo de " +
                      f"{p['citacao_longa_recuo_cm']:g}".replace(".", ",") + " cm, fonte menor, espaço simples e sem aspas "
                      "(Sobrenome, ano, p. 10).]", "CitacaoLonga"),
                  par("Figura 1 – [Título da figura]", "Legenda"),
                  par("Fonte: [elaborado pelo próprio autor ou a fonte, conforme NBR 14724:2024].", "FonteIlustracao")]
        else:
            x.append(par("[Texto.]"))
    x += [par("REFERÊNCIAS", "TituloSemNumero", "center", quebra_antes=tipo != "artigo"),
          par("[SOBRENOME, Prenome. Título: subtítulo. Edição. Local: Editora, ano.]", "Referencia")]
    x.append(secao(p, True, final=True))
    return "".join(x)


def estilos(p):
    fonte = escape(p["fonte_familia"])
    meio = p["fonte_pt"] * 2
    menor = p["fonte_menor_pt"] * 2
    linha = round(240 * p["espacamento"])
    recuo = round(p["recuo_paragrafo_cm"] * TW_CM)
    cit = round(p["citacao_longa_recuo_cm"] * TW_CM)

    def estilo(sid, nome, ppr, rpr="", base="Normal"):
        return (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{nome}"/>'
                f'<w:basedOn w:val="{base}"/><w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{fonte}" w:hAnsi="{fonte}" w:cs="{fonte}" w:eastAsia="{fonte}"/>
<w:sz w:val="{meio}"/><w:szCs w:val="{meio}"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="{linha}" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>
<w:pPr><w:ind w:firstLine="{recuo}"/><w:jc w:val="both"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Titulo1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="{linha}"/><w:ind w:firstLine="0"/><w:jc w:val="left"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:caps/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Titulo2"><w:name w:val="heading 2"/><w:basedOn w:val="Titulo1"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:spacing w:before="{linha}" w:after="{linha}"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b w:val="0"/><w:caps/></w:rPr></w:style>
{estilo("TituloSemNumero", "Título sem número", f'<w:keepNext/><w:spacing w:after="{linha}"/><w:ind w:firstLine="0"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>', "<w:b/><w:caps/>")}
{estilo("CitacaoLonga", "Citação longa", f'<w:spacing w:before="{linha}" w:after="{linha}" w:line="240" w:lineRule="auto"/><w:ind w:left="{cit}" w:firstLine="0"/>', f'<w:sz w:val="{menor}"/><w:szCs w:val="{menor}"/>')}
{estilo("Referencia", "Referência", '<w:spacing w:after="240" w:line="240" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="left"/>')}
{estilo("Resumo", "Resumo", '<w:spacing w:line="240" w:lineRule="auto" w:after="240"/><w:ind w:firstLine="0"/>')}
{estilo("Natureza", "Natureza do trabalho", f'<w:spacing w:line="240" w:lineRule="auto"/><w:ind w:left="{round(8 * TW_CM)}" w:firstLine="0"/>', f'<w:sz w:val="{menor}"/>')}
{estilo("Legenda", "Legenda", '<w:keepNext/><w:spacing w:line="240" w:lineRule="auto"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', f'<w:sz w:val="{menor}"/>')}
{estilo("FonteIlustracao", "Fonte da ilustração", '<w:spacing w:line="240" w:lineRule="auto" w:after="240"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', f'<w:sz w:val="{menor}"/>')}
<w:style w:type="paragraph" w:styleId="Cabecalho"><w:name w:val="header"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:firstLine="0"/><w:jc w:val="right"/></w:pPr><w:rPr><w:sz w:val="{menor}"/></w:rPr></w:style>
</w:styles>"""


NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def gerar(p, saida, tipo="tcc"):
    if tipo not in GRAUS:
        raise SystemExit(f"tipo inválido: {tipo} ({', '.join(GRAUS)})")
    documento = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>{corpo(p, tipo)}</w:body></w:document>'
    cabecalho = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr {NS}><w:p><w:pPr><w:pStyle w:val="Cabecalho"/>'
                 '</w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText>'
                 '</w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/>'
                 '</w:r></w:p></w:hdr>')
    arquivos = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
        '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '</Relationships>',
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
        '<Relationship Id="rIdHeader1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
        '</Relationships>',
        "word/settings.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:defaultTabStop w:val="709"/>'
        '<w:updateFields w:val="true"/><w:themeFontLang w:val="pt-BR"/></w:settings>',
        "word/styles.xml": estilos(p),
        "word/document.xml": documento,
        "word/header1.xml": cabecalho,
        "docProps/core.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>Modelo ABNT {escape(p.get("sigla") or "")} ({tipo})</dc:title><dc:creator>citacoes-abnt-skill</dc:creator>'
        '<dc:language>pt-BR</dc:language></cp:coreProperties>',
    }
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return saida


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instituicao", default="padrao-abnt")
    ap.add_argument("--tipo", default="tcc", choices=list(GRAUS))
    ap.add_argument("--saida")
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args(argv)
    if args.listar:
        for i in carregar_instituicoes():
            print(f"{i['id']:16} {i['nome']}")
        return 0
    p = perfil(args.instituicao)
    saida = args.saida or f"modelo-{p['id']}-{args.tipo}.docx"
    gerar(p, saida, args.tipo)
    m = p["margens_cm"]
    print(f"{saida}: {p['fonte_familia']} {p['fonte_pt']}, espaço {p['espacamento']:g}, margens {m['sup']:g}/{m['esq']:g}/"
          f"{m['inf']:g}/{m['dir']:g} cm, recuo {p['recuo_paragrafo_cm']:g} cm")
    return 0


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main())
