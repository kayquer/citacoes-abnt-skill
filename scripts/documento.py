"""Leitura de documentos: .docx (sem dependências), .md e .txt.

Separa o corpo do texto da lista de referências (seção REFERÊNCIAS,
BIBLIOGRAFIA ou REFERÊNCIAS BIBLIOGRÁFICAS).
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
RE_TITULO_REFS = re.compile(r"^\s*(#+\s*)?(\d+(\.\d+)*\s+)?(REFER[ÊE]NCIAS( BIBLIOGR[ÁA]FICAS)?|BIBLIOGRAFIA|OBRAS CITADAS)\s*$", re.I)
RE_FIM_REFS = re.compile(r"^\s*(#+\s*)?(AP[ÊE]NDICE|ANEXO|GLOSS[ÁA]RIO|[ÍI]NDICE)\b", re.I)


def paragrafos_docx(caminho):
    """Lista de parágrafos de texto do .docx, com negrito marcado como **...**."""
    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml")
    raiz = ET.fromstring(xml)
    saida = []
    for p in raiz.iter(W + "p"):
        pedacos = []
        for r in p.iter(W + "r"):
            texto = "".join(t.text or "" for t in r.iter(W + "t"))
            if not texto:
                continue
            rpr = r.find(W + "rPr")
            negrito = rpr is not None and rpr.find(W + "b") is not None and \
                rpr.find(W + "b").get(W + "val", "true") not in ("0", "false")
            pedacos.append(f"**{texto}**" if negrito and texto.strip() else texto)
        linha = "".join(pedacos).replace("****", "")
        saida.append(linha)
    return saida


RE_NOTA_MD = re.compile(r"^\[\^([^\]]+)\]:\s?(.*)$")


def _texto_sem_notas(texto):
    """(linhas sem as definições de nota [^n]:, {rótulo: texto da nota})."""
    linhas, notas, rotulo = [], {}, None
    for linha in texto.splitlines():
        m = RE_NOTA_MD.match(linha)
        if m:
            rotulo = m.group(1)
            notas[rotulo] = m.group(2).strip()
            continue
        if rotulo and linha.startswith(("    ", "\t")) and linha.strip():
            notas[rotulo] += " " + linha.strip()  # continuação da nota
            continue
        rotulo = None
        linhas.append(linha)
    return linhas, notas


def notas_docx(caminho):
    """Notas de rodapé e de fim do .docx, na ordem em que aparecem no texto."""
    saida = []
    with zipfile.ZipFile(caminho) as z:
        nomes = set(z.namelist())
        corpo = ET.fromstring(z.read("word/document.xml"))
        for parte, marca in (("word/footnotes.xml", "footnote"), ("word/endnotes.xml", "endnote")):
            if parte not in nomes:
                continue
            textos = {}
            for n in ET.fromstring(z.read(parte)).iter(W + marca):
                if n.get(W + "type") in ("separator", "continuationSeparator", "continuationNotice"):
                    continue
                textos[n.get(W + "id")] = " ".join("".join(t.text or "" for t in n.iter(W + "t")).split())
            for ref in corpo.iter(W + marca + "Reference"):
                nid = ref.get(W + "id")
                if nid in textos:
                    saida.append({"rotulo": f"{marca[0]}{nid}", "texto": textos.pop(nid)})
    return saida


def notas(caminho):
    """[{"rotulo": "1", "texto": "..."}] das notas de rodapé (.docx ou [^n]: em Markdown), em ordem."""
    caminho = str(caminho)
    if caminho.lower().endswith(".docx"):
        return notas_docx(caminho)
    texto = Path(caminho).read_text(encoding="utf-8")
    linhas, defs = _texto_sem_notas(texto)
    ordem = []
    for m in re.finditer(r"\[\^([^\]]+)\](?!:)", "\n".join(linhas)):
        if m.group(1) in defs and m.group(1) not in ordem:
            ordem.append(m.group(1))
    ordem += [r for r in defs if r not in ordem]  # definida e não chamada: vai para o fim
    return [{"rotulo": r, "texto": defs[r]} for r in ordem]


def paragrafos_texto(caminho):
    texto = Path(caminho).read_text(encoding="utf-8")
    blocos, atual = [], []
    for linha in _texto_sem_notas(texto)[0]:
        if not linha.strip():
            if atual:
                blocos.append(" ".join(atual))
                atual = []
            continue
        if RE_TITULO_REFS.match(linha) or linha.lstrip().startswith("#") or re.match(r"^\s*[-*]\s+", linha):
            if atual:
                blocos.append(" ".join(atual))
                atual = []
            blocos.append(re.sub(r"^\s*[-*]\s+", "", linha.strip()))
            continue
        atual.append(linha.strip())
    if atual:
        blocos.append(" ".join(atual))
    return blocos


def paragrafos(caminho):
    caminho = str(caminho)
    if caminho.lower().endswith(".docx"):
        return paragrafos_docx(caminho)
    return paragrafos_texto(caminho)


def separar(pars):
    """(corpo, referencias). Sem seção de referências, tudo é corpo."""
    for i, p in enumerate(pars):
        if RE_TITULO_REFS.match(p.replace("**", "")):
            refs = []
            for q in pars[i + 1:]:
                if RE_FIM_REFS.match(q.replace("**", "")):
                    break
                if q.strip():
                    refs.append(q.strip())
            return pars[:i], refs
    return pars, []


def ler(caminho):
    return separar(paragrafos(caminho))
