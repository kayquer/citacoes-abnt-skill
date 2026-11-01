"""Checador de existência de referências (detecta referência inventada e quimérica).

    py -3 scripts/checar_referencias.py trabalho.docx        (lê a seção REFERÊNCIAS)
    py -3 scripts/checar_referencias.py refs.md | refs.txt   (uma referência por parágrafo)
    py -3 scripts/checar_referencias.py refs.bib | biblioteca.json
    opções: --json  --sem-rede (só forma ABNT)  --bases crossref,openalex,semantic,openlibrary

Para cada referência, procura a obra em bases abertas e classifica:
  verificada      encontrada em 2 ou mais bases, com título e autoria batendo
  parcial         encontrada em 1 base só (comum em livro nacional): conferir à mão
  quimera         o título existe, mas nenhum autor bate (título real, autoria errada)
  doi_divergente  o DOI existe, mas aponta para outra obra
  nao_encontrada  nenhuma base achou: possível referência inventada
  inconclusiva    nada achado, mas menos de 2 bases responderam
  erro_rede       nenhuma base respondeu; nada foi concluído

Regra: uma referência só sai "verificada" com evidência de duas bases. Na dúvida,
o status é o mais conservador.

Saída: 0 = todas verificadas; 1 = há nao_encontrada, quimera ou doi_divergente;
2 = só há parciais, inconclusivas ou erros de rede.
"""
import argparse
import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abnt_lib as A  # noqa: E402
import biblioteca as B  # noqa: E402
import documento as D  # noqa: E402
import metadados as M  # noqa: E402

LIMIAR_TITULO = 0.85
VAZIAS = B.VAZIAS | {"for", "with", "to", "by", "no", "na", "nos", "nas", "com", "por", "sobre", "uma", "um"}


def norm_titulo(t):
    t = re.sub(r"[^a-z0-9 ]", " ", A.sem_acento(t or "").lower())
    return [w for w in t.split() if w not in VAZIAS]


def similaridade(a, b):
    """Maior entre Jaccard de palavras e razão de sequência (ambos sem acento e sem palavras vazias)."""
    wa, wb = norm_titulo(a), norm_titulo(b)
    if not wa or not wb:
        return 0.0
    jac = len(set(wa) & set(wb)) / len(set(wa) | set(wb))
    seq = SequenceMatcher(None, " ".join(wa), " ".join(wb)).ratio()
    # Título da referência pode trazer só a parte antes do subtítulo
    pref = 1.0 if len(wa) >= 3 and " ".join(wb).startswith(" ".join(wa)) else 0.0
    return max(jac, seq, pref * 0.9)


def sobrenomes(autores):
    saida = set()
    for a in autores or []:
        nome = a.get("sobrenome") or a.get("entidade") or ""
        for w in re.sub(r"[^a-z ]", " ", A.sem_acento(nome).lower()).split():
            if len(w) > 2 and w not in A.AGNOMES and w not in A.PARTICULAS:
                saida.add(w)
    return saida


def autores_batem(ref, cand):
    a, b = sobrenomes(ref.get("autores")), sobrenomes(cand.get("autores"))
    if not a or not b:
        return None  # sem dado para comparar
    return bool(a & b)


def melhor(ref, candidatos):
    melhor_c, melhor_s = None, 0.0
    for c in candidatos:
        s = similaridade(ref.get("titulo"), c.get("titulo"))
        if s > melhor_s:
            melhor_c, melhor_s = c, s
    return melhor_c, melhor_s


def buscar_em(base, ref):
    titulo = ref.get("titulo") or ""
    autor = next(iter(sobrenomes(ref.get("autores"))), None)
    if base == "crossref":
        cands = M.crossref_buscar(titulo, autor)
        if autor and melhor(ref, cands)[1] < LIMIAR_TITULO:
            # Sem o filtro de autor: é assim que aparece o título real com autoria trocada (quimera)
            cands += M.crossref_buscar(titulo)
        return cands
    if base == "openalex":
        return M.openalex_buscar(titulo)
    if base == "semantic":
        return M.semantic_buscar(titulo)
    if base == "openlibrary":
        return M.openlibrary_buscar(titulo, autor) or M.openlibrary_buscar(titulo)
    if base == "googlebooks":
        return M.googlebooks_buscar(titulo, autor) or M.googlebooks_buscar(titulo)
    return []


def checar(ref, bases):
    resultado = {"titulo": ref.get("titulo"), "ano": ref.get("ano"), "doi": ref.get("doi"),
                 "bases": {}, "alertas": [], "status": None}
    if ref.get("texto"):
        resultado["referencia"] = ref["texto"]
        resultado["alertas"] += A.problemas_texto(ref["texto"])
    if not ref.get("titulo") or len(norm_titulo(ref.get("titulo"))) < 2:
        resultado["alertas"].append("título curto ou não identificado: a busca fica pouco confiável")
    confirmadas, quimeras, erros, anos_bases = set(), set(), [], {}
    respondidas, so_titulo = 0, set()

    # 1. DOI: deve existir e apontar para esta obra
    if ref.get("doi"):
        via_doi, falhou = None, False
        try:
            via_doi = M.crossref_doi(ref["doi"])
        except M.ErroRede as e:
            erros.append(str(e))
            falhou = True
        if via_doi is None and not falhou:
            resultado["alertas"].append("DOI não existe no Crossref")
            resultado["status"] = "doi_divergente"
        elif via_doi:
            s = similaridade(ref.get("titulo"), via_doi.get("titulo"))
            resultado["bases"]["doi"] = {"titulo": via_doi.get("titulo"), "similaridade": round(s, 2)}
            if s < 0.6:
                resultado["status"] = "doi_divergente"
                resultado["alertas"].append(f"o DOI leva a outra obra: \"{via_doi.get('titulo')}\"")
            elif autores_batem(ref, via_doi) is False:
                quimeras.add("crossref")
            else:
                confirmadas.add("crossref")

    # 2. Busca por título nas bases
    for base in bases:
        if base in confirmadas:
            continue
        if base in ("openlibrary", "googlebooks") and ref.get("tipo", "livro") not in ("livro", "capitulo", "tese") \
                and (ref.get("periodico") or "In:" in (ref.get("texto") or "")):
            continue  # artigo e trabalho de evento não ficam nas bases de livros
        try:
            cands = buscar_em(base, ref)
        except M.ErroRede as e:
            erros.append(str(e))
            continue
        respondidas += 1
        c, s = melhor(ref, cands)
        if not c or s < LIMIAR_TITULO:
            resultado["bases"][base] = {"achou": False, "melhor_similaridade": round(s, 2)}
            continue
        bate = autores_batem(ref, c)
        info = {"achou": True, "titulo": c.get("titulo"), "ano": c.get("ano"), "similaridade": round(s, 2),
                "autores_batem": bate, "doi": c.get("doi")}
        resultado["bases"][base] = info
        if bate is False:
            quimeras.add(base)
            continue
        confirmadas.add(base)
        if bate is None:
            so_titulo.add(base)
        if c.get("ano"):
            anos_bases[base] = int(str(c["ano"])[:4])
        if not ref.get("doi") and c.get("doi") and s >= 0.95 and bate:
            resultado["sugestao_doi"] = c["doi"]

    if erros:
        resultado["erros_rede"] = erros
    if ref.get("ano") and anos_bases and str(ref["ano"])[:4].isdigit():
        ano = int(str(ref["ano"])[:4])
        if all(abs(ano - a) > 1 for a in anos_bases.values()):
            resultado["alertas"].append(f"ano {ano} difere das bases ({', '.join(f'{b}: {a}' for b, a in anos_bases.items())}); "
                                        "pode ser outra edição: confira a folha de rosto")
    resultado["confirmada_em"] = sorted(confirmadas)
    if confirmadas and confirmadas <= so_titulo:
        resultado["autoria_nao_comparada"] = True
        resultado["alertas"].append("confirmada só pelo título: faltou autor na referência ou na base; confira a autoria")
    if resultado["status"] == "doi_divergente":
        return resultado
    if len(confirmadas) >= 2:
        resultado["status"] = "verificada"
    elif quimeras and not confirmadas:
        resultado["status"] = "quimera"
        resultado["alertas"].append("o título existe, mas a autoria não bate com nenhuma base")
    elif len(confirmadas) == 1:
        resultado["status"] = "parcial"
    elif respondidas == 0 and erros:
        resultado["status"] = "erro_rede"
    elif respondidas < 2:
        resultado["status"] = "inconclusiva"
        resultado["alertas"].append("nenhuma base achou, mas algumas não responderam: rode de novo mais tarde")
    else:
        resultado["status"] = "nao_encontrada"
    resultado["confirmada_em"] = sorted(confirmadas)
    return resultado


def carregar_refs(caminho):
    ext = Path(caminho).suffix.lower()
    if ext == ".bib":
        return B.ler_bib(Path(caminho).read_text(encoding="utf-8"))
    if ext == ".ris":
        return B.ler_ris(Path(caminho).read_text(encoding="utf-8"))
    if ext == ".json":
        dados = B.carregar(caminho)
        return dados["referencias"]
    corpo, refs = D.ler(caminho)
    if not refs:  # arquivo só com referências
        refs = [p for p in corpo if p.strip() and not p.lstrip().startswith("#")]
    return [A.ler_referencia_texto(r) for r in refs if len(r) > 25]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sem-rede", action="store_true", help="só confere a forma ABNT, sem consultar bases")
    ap.add_argument("--bases", default="crossref,openalex,semantic,openlibrary,googlebooks")
    args = ap.parse_args(argv)
    refs = carregar_refs(args.arquivo)
    bases = [b for b in args.bases.split(",") if b]
    saida = []
    for r in refs:
        if args.sem_rede:
            saida.append({"referencia": r.get("texto") or A.formatar_referencia(r, estilo="texto"),
                          "alertas": A.problemas_texto(r["texto"]) if r.get("texto") else A.faltantes(r), "status": "nao_checada"})
        else:
            saida.append(checar(r, bases))
    resumo = {}
    for s in saida:
        resumo[s["status"]] = resumo.get(s["status"], 0) + 1
    if args.json:
        print(json.dumps({"resumo": resumo, "referencias": saida}, ensure_ascii=False, indent=2))
    else:
        for i, s in enumerate(saida, 1):
            print(f"[{i}] {s['status'].upper()}: {s.get('referencia') or s.get('titulo')}")
            if s.get("confirmada_em"):
                print(f"    confirmada em: {', '.join(s['confirmada_em'])}")
            for a in s.get("alertas", []):
                print(f"    - {a}")
            if s.get("sugestao_doi"):
                print(f"    - DOI encontrado: https://doi.org/{s['sugestao_doi']}")
        print("\nResumo:", ", ".join(f"{k}: {v}" for k, v in sorted(resumo.items())))
    graves = {"nao_encontrada", "quimera", "doi_divergente"}
    if any(s["status"] in graves for s in saida):
        return 1
    if any(s["status"] in ("parcial", "erro_rede", "inconclusiva") for s in saida):
        return 2
    return 0


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main())
