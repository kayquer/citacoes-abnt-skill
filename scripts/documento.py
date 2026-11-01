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


def paragrafos_texto(caminho):
    texto = Path(caminho).read_text(encoding="utf-8")
    blocos, atual = [], []
    for linha in texto.splitlines():
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
