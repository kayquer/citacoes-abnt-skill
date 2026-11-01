"""Checador de existência de referências (detecta referência inventada e quimérica).

    py -3 scripts/checar_referencias.py trabalho.docx        (lê a seção REFERÊNCIAS)
    py -3 scripts/checar_referencias.py refs.md | refs.txt   (uma referência por parágrafo)
    py -3 scripts/checar_referencias.py refs.bib | biblioteca.json
    opções: --json  --sem-rede (só forma ABNT)  --bases crossref,openalex,semantic,openlibrary,googlebooks
            --saida checagem.jsonl (grava cada obra assim que termina)  --retomar (pula as já checadas)
            --sem-cache  --sem-paralelo  --silencioso (sem progresso no stderr)

Para cada referência, procura a obra em bases abertas e classifica:
  verificada         encontrada em 2 ou mais bases, com título e autoria batendo
  parcial            encontrada em 1 base só (comum em livro nacional): conferir à mão
  quimera            o título existe com outra autoria, em ano e tipo compatíveis (título real, autoria errada)
  homonimo           só apareceu obra de mesmo título, mas de outro ano ou de outro tipo: não prova nada
  doi_divergente     o DOI não existe ou aponta para outra obra
  url_verificada     notícia, site ou relatório: o link responde e o título da página bate
  url_divergente     o link responde, mas o título da página é outro
  url_inacessivel    o link não respondeu (404, 403 ou bloqueio a robôs): abra no navegador
  nao_verificavel    notícia sem URL ou título atribuído [entre colchetes]: não dá para buscar por título
  fora_de_cobertura  obra anterior a 1800 sem resultado: as bases quase não cobrem edições históricas
  nao_encontrada     nenhuma base achou: possível referência inventada
  inconclusiva       nada achado, mas menos de 2 bases responderam (limite de taxa, queda)
  erro_rede          nenhuma base respondeu; nada foi concluído

Regra: uma referência só sai "verificada" com evidência de duas bases. Na dúvida,
o status é o mais conservador. Obra não encontrada não é obra falsa: livro nacional,
notícia e relatório técnico às vezes faltam nas bases.

Saída: 0 = todas verificadas (ou url_verificada); 1 = há nao_encontrada, quimera ou doi_divergente;
2 = só há casos a conferir à mão (parcial, homonimo, url_*, inconclusiva, erro_rede...).
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abnt_lib as A  # noqa: E402
import biblioteca as B  # noqa: E402
import documento as D  # noqa: E402
import metadados as M  # noqa: E402

LIMIAR_TITULO = 0.85
FOLGA_HOMONIMO = 5  # anos: fora disso, mesmo título com outro autor é outra obra, não quimera
VAZIAS = B.VAZIAS | {"for", "with", "to", "by", "no", "na", "nos", "nas", "com", "por", "sobre", "uma", "um"}
BASES_LIVRO = {"openlibrary", "googlebooks"}
SEM_BASE_ACADEMICA = {"site", "jornal", "legislacao"}  # notícia, página e lei: confere-se o link
GRUPOS_TIPO = {"livro": "livro", "capitulo": "livro", "artigo": "periodico", "evento": "periodico",
               "jornal": "periodico", "tese": "tese", "site": "site"}
PREPRINTS = {"10.2139": "SSRN", "10.1101": "bioRxiv/medRxiv", "10.48550": "arXiv", "10.31234": "PsyArXiv",
             "10.31235": "SocArXiv", "10.31219": "OSF Preprints", "10.20944": "Preprints.org",
             "10.21203": "Research Square", "10.5281": "Zenodo", "10.36227": "TechRxiv", "10.1590/scielopreprints": "SciELO Preprints"}
GRAVES = {"nao_encontrada", "quimera", "doi_divergente"}
A_CONFERIR = {"parcial", "homonimo", "url_divergente", "url_inacessivel", "nao_verificavel", "fora_de_cobertura",
              "inconclusiva", "erro_rede"}


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
    pref = 0.9 if len(wa) >= 3 and " ".join(wb).startswith(" ".join(wa)) else 0.0
    # E a base pode guardar só o título principal (Crossref: "Get the message"): compara com a parte antes de ":"
    principal = (a or "").split(":")[0]
    if principal != a and len(norm_titulo(principal)) >= 2 and norm_titulo(principal) == wb:
        pref = 0.9
    return max(jac, seq, pref)


def sobrenomes(autores):
    saida = set()
    for a in autores or []:
        nome = a.get("sobrenome") or a.get("entidade") or ""
        for w in re.sub(r"[^a-z ]", " ", A.sem_acento(nome).lower()).split():
            if len(w) > 2 and w not in A.AGNOMES and w not in A.PARTICULAS:
                saida.add(w)
    return saida


def autores_batem(ref, cand):
    """True, False ou None (sem dado). Um sobrenome em comum só basta se for o do primeiro autor de um dos lados.

    Assim um Wang ou um Silva perdido numa lista de 20 autores não transforma quimera em obra verificada.
    """
    a, b = sobrenomes(ref.get("autores")), sobrenomes(cand.get("autores"))
    if not a or not b:
        return None
    comuns = a & b
    if not comuns:
        return False
    primeiro_ref = sobrenomes((ref.get("autores") or [])[:1])
    primeiro_cand = sobrenomes((cand.get("autores") or [])[:1])
    return bool(primeiro_ref & b or primeiro_cand & a or len(comuns) >= 2)


def _ano(r):
    m = re.match(r"\d{4}", str(A.ano_de_data(r) or ""))
    return int(m.group(0)) if m else None


def homonimo(ref, cand):
    """Mesmo título, outro autor, mas ano ou tipo distantes demais para ser a mesma obra com autoria trocada."""
    a1, a2 = _ano(ref), _ano(cand)
    if a1 and a2 and abs(a1 - a2) > FOLGA_HOMONIMO:
        return True
    g1, g2 = GRUPOS_TIPO.get(ref.get("tipo")), GRUPOS_TIPO.get(cand.get("tipo"))
    if g1 and g2 and g1 != g2:
        return True  # livro x artigo (resenha de mesmo título), livro x dissertação
    return len(norm_titulo(ref.get("titulo"))) <= 2 and not (a1 and a2)  # título curto e sem ano para comparar


def melhor(ref, candidatos):
    melhor_c, melhor_s = None, 0.0
    for c in candidatos:
        s = similaridade(ref.get("titulo"), c.get("titulo"))
        if s > melhor_s:
            melhor_c, melhor_s = c, s
    return melhor_c, melhor_s


def buscar_em(base, ref):
    titulo = ref.get("titulo") or ""
    autor = next(iter(sobrenomes((ref.get("autores") or [])[:1]) or sobrenomes(ref.get("autores"))), None)
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


def preprint(doi):
    doi = (doi or "").lower()
    return next((nome for prefixo, nome in PREPRINTS.items() if doi.startswith(prefixo + "/") or doi.startswith(prefixo)),
                None)


def avaliar_sugestao_doi(ref, cand):
    """(doi ou None, aviso ou None). Só sugere DOI de candidato com autor, ano e periódico compatíveis."""
    doi = cand.get("doi")
    if not doi or ref.get("doi"):
        return None, None
    a1, a2 = _ano(ref), _ano(cand)
    if a1 and a2 and abs(a1 - a2) > 1:
        return None, f"DOI {doi} recusado: é de {a2}, a referência é de {a1} (reedição ou outra versão?)"
    origem = preprint(doi)
    if origem and (ref.get("periodico") or ref.get("tipo") in ("artigo", "livro", "capitulo")):
        return None, f"DOI {doi} recusado: é da versão em {origem}, não da obra publicada"
    if ref.get("periodico") and cand.get("periodico") and \
            SequenceMatcher(None, A.sem_acento(ref["periodico"]).lower(), A.sem_acento(cand["periodico"]).lower()).ratio() < 0.6:
        return None, f"DOI {doi} recusado: periódico da base ('{cand['periodico']}') difere do da referência"
    return doi, None


def _url_do_texto(ref):
    if ref.get("url"):
        return ref["url"]
    m = re.search(r"Disponível em:\s*<?(https?://\S+?)>?\.?(?:\s|$)", ref.get("texto") or "")
    return m.group(1) if m else None


def _checar_url(ref, resultado):
    url = _url_do_texto(ref)
    if not url:
        return None
    try:
        r = M.conferir_url(url)
    except M.ErroRede as e:
        resultado["alertas"].append(f"o link não respondeu ({e}); sites de notícia costumam bloquear robôs: abra no navegador")
        return "url_inacessivel"
    resultado["bases"]["url"] = {"responde": r["responde"], "titulo": r["titulo"]}
    if not r["responde"]:
        resultado["alertas"].append("o link devolveu 404: procure o endereço novo ou uma cópia no Internet Archive")
        return "url_inacessivel"
    if not r["titulo"] or ref.get("titulo_atribuido"):
        resultado["alertas"].append("o link responde; o título não foi comparado: confira o conteúdo")
        return "url_verificada"
    s = max(similaridade(ref.get("titulo"), r["titulo"]), similaridade(r["titulo"], ref.get("titulo")))
    resultado["bases"]["url"]["similaridade"] = round(s, 2)
    if s >= 0.6 or (norm_titulo(ref.get("titulo")) and " ".join(norm_titulo(ref.get("titulo"))) in " ".join(norm_titulo(r["titulo"]))):
        return "url_verificada"
    resultado["alertas"].append(f"o link responde, mas a página se chama \"{r['titulo']}\": confira se é a mesma obra")
    return "url_divergente"


def checar(ref, bases, paralelo=True):
    resultado = {"titulo": ref.get("titulo"), "ano": A.ano_de_data(ref), "doi": ref.get("doi"),
                 "bases": {}, "alertas": [], "status": None}
    if ref.get("id"):
        resultado["id"] = ref["id"]
    if ref.get("texto"):
        resultado["referencia"] = ref["texto"]
        resultado["alertas"] += A.problemas_texto(ref["texto"])
    tipo = ref.get("tipo")
    atribuido = ref.get("titulo_atribuido") or (ref.get("titulo") or "").startswith("[")
    if not atribuido and (not ref.get("titulo") or len(norm_titulo(ref.get("titulo"))) < 2):
        resultado["alertas"].append("título curto ou não identificado: a busca fica pouco confiável")
    confirmadas, quimeras, homonimos, erros, anos_bases = set(), set(), set(), [], {}
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
            if preprint(ref["doi"]) and ref.get("periodico"):
                resultado["alertas"].append(f"o DOI é da versão em {preprint(ref['doi'])}, mas a referência cita um "
                                            "periódico: use o DOI do artigo publicado")

    # 2. Busca por título nas bases (em paralelo entre bases; cada base continua com uma chamada por vez)
    if tipo in SEM_BASE_ACADEMICA or atribuido:
        busca = []  # notícia, site, lei e título atribuído não ficam nas bases acadêmicas
    else:
        sem_livro = tipo in ("artigo", "evento", "jornal") or \
            (not tipo and (ref.get("periodico") or "In:" in (ref.get("texto") or "")))
        busca = [b for b in bases if b not in confirmadas and not (b in BASES_LIVRO and sem_livro)]

    def consulta(base):
        try:
            return base, buscar_em(base, ref), None
        except M.ErroRede as e:
            return base, None, str(e)

    if paralelo and len(busca) > 1:
        with ThreadPoolExecutor(max_workers=len(busca)) as ex:
            respostas = list(ex.map(consulta, busca))
    else:
        respostas = [consulta(b) for b in busca]

    for base, cands, erro in respostas:
        if erro:
            erros.append(erro)
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
            if homonimo(ref, c):
                info["homonimo"] = True
                homonimos.add(base)
            else:
                quimeras.add(base)
            continue
        confirmadas.add(base)
        if bate is None:
            so_titulo.add(base)
        if c.get("ano"):
            anos_bases[base] = int(str(c["ano"])[:4])
        if bate and s >= 0.95 and "sugestao_doi" not in resultado:
            doi, aviso = avaliar_sugestao_doi(ref, c)
            if doi:
                resultado["sugestao_doi"] = doi
            elif aviso and aviso not in resultado["alertas"]:
                resultado["alertas"].append(aviso)

    if erros:
        resultado["erros_rede"] = erros
        if any("429" in e or "503" in e for e in erros):
            resultado["limite_taxa"] = True
            resultado["alertas"].append("alguma base limitou a taxa (HTTP 429): rode de novo com --retomar mais tarde")
            for e in dict.fromkeys(e for e in erros if "cota esgotada" in e):
                resultado["alertas"].append(e)
    ano = _ano(ref)
    if ano and anos_bases and all(abs(ano - a) > 1 for a in anos_bases.values()):
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
    else:
        status_url = _checar_url(ref, resultado)  # sem confirmação nas bases, o link é a última evidência
        if status_url:
            resultado["status"] = status_url
        elif tipo in SEM_BASE_ACADEMICA or atribuido:
            resultado["status"] = "nao_verificavel"
            resultado["alertas"].append("título atribuído entre colchetes não é buscável por título" if atribuido else
                                        "notícia, site ou lei sem URL: confira à mão")
        elif homonimos:
            resultado["status"] = "homonimo"
            resultado["alertas"].append("as bases só têm obra de mesmo título com outro autor e outro ano ou tipo: "
                                        "não é sinal de invenção, mas a obra citada não foi confirmada")
        elif respondidas == 0 and erros:
            resultado["status"] = "erro_rede"
        elif respondidas < 2:
            resultado["status"] = "inconclusiva"
            resultado["alertas"].append("nenhuma base achou, mas algumas não responderam: rode de novo mais tarde")
        elif ano and ano < 1800:
            resultado["status"] = "fora_de_cobertura"
            resultado["alertas"].append(f"obra de {ano}: as bases abertas quase não cobrem edições históricas; "
                                        "confira num catálogo de biblioteca (Biblioteca Nacional, WorldCat)")
        else:
            resultado["status"] = "nao_encontrada"
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


def chave(ref, i):
    """Identifica a obra entre rodadas (--retomar): id, texto ou título."""
    return str(ref.get("id") or ref.get("texto") or f"{ref.get('titulo')}|{A.ano_de_data(ref)}" or i)


def ler_jsonl(caminho):
    feitos = {}
    try:
        linhas = Path(caminho).read_text(encoding="utf-8").splitlines()
    except OSError:
        return feitos
    for linha in linhas:
        try:
            r = json.loads(linha)
        except ValueError:
            continue  # linha cortada por queda no meio da gravação
        if r.get("chave"):
            feitos[r["chave"]] = r  # a última linha de cada obra vale
    return feitos


def precisa_refazer(r):
    return r.get("status") in ("erro_rede", "inconclusiva") or r.get("limite_taxa")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sem-rede", action="store_true", help="só confere a forma ABNT, sem consultar bases")
    ap.add_argument("--bases", default="crossref,openalex,semantic,openlibrary,googlebooks")
    ap.add_argument("--saida", help="arquivo .jsonl gravado a cada obra checada")
    ap.add_argument("--retomar", action="store_true",
                    help="com --saida: pula as obras já checadas e refaz só as que deram erro de rede ou limite de taxa")
    ap.add_argument("--sem-cache", action="store_true", help="não lê nem grava o cache em disco das bases")
    ap.add_argument("--sem-paralelo", action="store_true", help="consulta uma base de cada vez")
    ap.add_argument("--silencioso", action="store_true", help="sem a linha de progresso no stderr")
    args = ap.parse_args(argv)
    if args.retomar and not args.saida:
        ap.error("--retomar precisa de --saida arquivo.jsonl")
    if args.sem_cache:
        M.CACHE_ATIVO = False
    refs = carregar_refs(args.arquivo)
    bases = [b for b in args.bases.split(",") if b]
    feitos = ler_jsonl(args.saida) if args.retomar else {}
    destino = open(args.saida, "a" if args.retomar else "w", encoding="utf-8") if args.saida else None
    saida, pulados = [], 0
    try:
        for i, r in enumerate(refs, 1):
            k = chave(r, i)
            anterior = feitos.get(k)
            if anterior and not precisa_refazer(anterior):
                saida.append(anterior)
                pulados += 1
                continue
            if args.sem_rede:
                res = {"referencia": r.get("texto") or A.formatar_referencia(r, estilo="texto"),
                       "alertas": A.problemas_texto(r["texto"]) if r.get("texto") else A.faltantes(r),
                       "status": "nao_checada"}
            else:
                res = checar(r, bases, paralelo=not args.sem_paralelo)
            res["chave"] = k
            saida.append(res)
            if destino:
                destino.write(json.dumps(res, ensure_ascii=False) + "\n")
                destino.flush()
            if not args.silencioso:
                print(f"[{i}/{len(refs)}] {res['status']}: {(res.get('titulo') or res.get('referencia') or '')[:70]}",
                      file=sys.stderr, flush=True)
    finally:
        if destino:
            destino.close()
    resumo = {}
    for s in saida:
        resumo[s["status"]] = resumo.get(s["status"], 0) + 1
    limite = sum(1 for s in saida if s.get("limite_taxa"))
    if args.json:
        extra = {"afetadas_por_limite_de_taxa": limite} if limite else {}
        if pulados:
            extra["retomadas_do_arquivo"] = pulados
        print(json.dumps({"resumo": resumo, **extra, "referencias": saida}, ensure_ascii=False, indent=2))
    else:
        for i, s in enumerate(saida, 1):
            print(f"[{i}] {s['status'].upper()}: {s.get('referencia') or s.get('titulo')}")
            if s.get("confirmada_em"):
                print(f"    confirmada em: {', '.join(s['confirmada_em'])}")
            for a in s.get("alertas", []):
                print(f"    - {a}")
            if s.get("sugestao_doi"):
                print(f"    - DOI encontrado (autor, ano e periódico conferidos): https://doi.org/{s['sugestao_doi']}")
        print("\nResumo:", ", ".join(f"{k}: {v}" for k, v in sorted(resumo.items())))
        if limite:
            print(f"{limite} obra(s) afetada(s) por limite de taxa: rode de novo com --saida ... --retomar")
    if any(s["status"] in GRAVES for s in saida):
        return 1
    if any(s["status"] in A_CONFERIR for s in saida):
        return 2
    return 0


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main())
