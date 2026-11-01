"""Biblioteca local de citações (biblioteca.json).

    py -3 scripts/biblioteca.py adicionar --doi 10.1038/nature14539
    py -3 scripts/biblioteca.py adicionar --isbn 9788577531639 --tag metodologia
    py -3 scripts/biblioteca.py adicionar --url https://www.scielo.br/j/...
    py -3 scripts/biblioteca.py adicionar --json '{"tipo":"livro","autores":[{"sobrenome":"Freire","nome":"Paulo"}],...}'
    py -3 scripts/biblioteca.py importar refs.bib            (.bib, .ris ou .json)
    py -3 scripts/biblioteca.py listar [--tag X] | buscar termo | remover id
    py -3 scripts/biblioteca.py citar freire1987pedagogia --pagina 45 [--narrativa]
    py -3 scripts/biblioteca.py nota freud2010luto --pagina 172 [--forma completa|curta|ibid|idem|opcit|loccit]
    py -3 scripts/biblioteca.py notas "freud2010luto:172, freud2010luto:180, hobbes2003leviata:cap. XIII" [--expressoes-latinas]
    py -3 scripts/biblioteca.py exportar --formato abnt|bib|ris|csl [--saida arq] [--ids a,b]
    py -3 scripts/biblioteca.py deduplicar [--aplicar]
    py -3 scripts/biblioteca.py faltantes

Opções globais: --arquivo caminho/biblioteca.json (padrão: ./biblioteca.json),
--edicao-6023 2025|2018, --edicao-10520 2023|2002 (só muda a chamada de "citar"), --et-al (4+ autores viram et al.).
O "exportar" em ABNT acrescenta 2010a/2010b nas obras do mesmo autor e ano, como na chamada.

Toda entrada nova guarda "fonte" (de onde veio o metadado) e "revisar" quando
algum campo obrigatório falta. Nada é completado por suposição.
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abnt_lib as A  # noqa: E402

VERSAO = 1


# ---------------------------------------------------------------- armazenamento

def carregar(caminho):
    p = Path(caminho)
    if not p.exists():
        return {"versao": VERSAO, "referencias": []}
    dados = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(dados, list):
        dados = {"versao": VERSAO, "referencias": dados}
    return dados


def salvar(caminho, dados):
    p = Path(caminho)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------- chaves e duplicatas

def _norm(texto):
    return re.sub(r"[^a-z0-9 ]", "", A.sem_acento(texto or "").lower()).strip()


VAZIAS = {"a", "o", "as", "os", "um", "uma", "de", "da", "do", "the", "an", "of", "on", "in", "e", "and", "para", "em"}


def gerar_id(ref, existentes):
    autores = ref.get("autores") or []
    if autores:
        base = autores[0].get("sobrenome") or autores[0].get("entidade") or "anon"
    else:
        base = "anon"
    base = _norm(base).split(" ")[-1] if autores and "sobrenome" in autores[0] else _norm(base).replace(" ", "")[:12]
    palavra = next((w for w in _norm(ref.get("titulo")).split() if w not in VAZIAS), "")
    rid = re.sub(r"[^a-z0-9]", "", f"{base}{ref.get('ano') or 'sd'}{palavra}") or "ref"
    final, n = rid, 2
    while final in existentes:
        final = f"{rid}{n}"
        n += 1
    return final


def mesma_obra(a, b):
    if a.get("doi") and b.get("doi"):
        return a["doi"].lower() == b["doi"].lower()
    if a.get("isbn") and b.get("isbn"):
        return re.sub(r"\D", "", a["isbn"]) == re.sub(r"\D", "", b["isbn"])
    ta, tb = _norm(a.get("titulo")), _norm(b.get("titulo"))
    if not ta or not tb:
        return False
    return SequenceMatcher(None, ta, tb).ratio() >= 0.92 and str(a.get("ano")) == str(b.get("ano"))


def adicionar(dados, ref, tags=None):
    """Adiciona e devolve (ref, duplicata_existente_ou_None)."""
    for existente in dados["referencias"]:
        if mesma_obra(existente, ref):
            return existente, existente
    ref = {k: v for k, v in ref.items() if v not in (None, "", [])}
    if ref.get("id") and not re.match(r"^[a-z0-9]+$", ref["id"]):
        ref.pop("id")
    ref.setdefault("id", gerar_id(ref, {r["id"] for r in dados["referencias"]}))
    if tags:
        ref["tags"] = sorted(set(ref.get("tags", [])) | set(tags))
    falta = A.faltantes(ref)
    if falta:
        ref["revisar"] = falta
    ref["adicionado_em"] = date.today().isoformat()
    dados["referencias"].append(ref)
    return ref, None


# ---------------------------------------------------------------- BibTeX

BIB_TIPO = {"article": "artigo", "book": "livro", "incollection": "capitulo", "inbook": "capitulo",
            "inproceedings": "evento", "conference": "evento", "phdthesis": "tese", "mastersthesis": "tese",
            "misc": "site", "online": "site", "techreport": "livro"}
TIPO_BIB = {"artigo": "article", "jornal": "article", "livro": "book", "capitulo": "incollection",
            "evento": "inproceedings", "site": "misc", "legislacao": "misc"}
# Responsabilidades com campo próprio no biblatex (a lista livre "responsabilidades" fica só na ABNT)
BIB_PAPEIS = (("prefacio", "foreword"), ("introducao", "introduction"), ("notas_de", "annotator"))


def _data_bib(c):
    """date (biblatex, AAAA-MM-DD) ou year + month."""
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", c.get("date") or "")
    if m and m.group(2):
        return m.group(0)
    return None


def _bib_entradas(texto):
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I).search(texto, i)
        if not m:
            return
        tipo, chave, pos, nivel = m.group(1).lower(), m.group(2), m.end(), 1
        j = pos
        while j < len(texto) and nivel:
            nivel += {"{": 1, "}": -1}.get(texto[j], 0)
            j += 1
        yield tipo, chave, texto[pos:j - 1]
        i = j


def _bib_campos(corpo):
    campos, i = {}, 0
    padrao = re.compile(r"\s*(\w+)\s*=\s*", re.I)
    while i < len(corpo):
        m = padrao.match(corpo, i)
        if not m:
            break
        nome, i = m.group(1).lower(), m.end()
        if i < len(corpo) and corpo[i] == "{":
            nivel, j = 1, i + 1
            while j < len(corpo) and nivel:
                nivel += {"{": 1, "}": -1}.get(corpo[j], 0)
                j += 1
            valor, i = corpo[i + 1:j - 1], j
        elif i < len(corpo) and corpo[i] == '"':
            j = corpo.index('"', i + 1)
            valor, i = corpo[i + 1:j], j + 1
        else:
            m2 = re.match(r"[^,]+", corpo[i:])
            valor = m2.group(0).strip() if m2 else ""
            i += len(valor)
        campos[nome] = " ".join(valor.replace("{", "").replace("}", "").split())
        m3 = re.match(r"\s*,", corpo[i:])
        if m3:
            i += m3.end()
    return campos


def _bib_autores(texto):
    saida = []
    for nome in re.split(r"\s+and\s+", texto or ""):
        nome = nome.strip()
        if nome:
            saida.append(A.separar_nome(nome) if "," in nome or " " in nome else {"sobrenome": nome, "nome": ""})
    return saida


def ler_bib(texto):
    refs = []
    for tipo_bib, chave, corpo in _bib_entradas(texto):
        if tipo_bib in ("comment", "preamble", "string"):
            continue
        c = _bib_campos(corpo)
        tipo = BIB_TIPO.get(tipo_bib, "livro")
        titulo, _, sub = (c.get("title") or "").partition(": ")
        if tipo == "artigo" and (c.get("entrysubtype") or "").lower() == "newspaper":
            tipo = "jornal"
        ref = {"id": re.sub(r"[^a-z0-9]", "", chave.lower()), "tipo": tipo, "titulo": titulo or None, "subtitulo": sub or None,
               "autores": _bib_autores(c.get("author")), "ano": c.get("year") or (c.get("date") or "")[:4] or None,
               "data": _data_bib(c), "eloc": c.get("eid"), "caderno": c.get("section"),
               "doi": c.get("doi"), "url": c.get("url"),
               "volume": c.get("volume"), "numero": c.get("number"), "paginas": (c.get("pages") or "").replace("--", "-") or None,
               "editora": c.get("publisher"), "local": c.get("address"), "isbn": c.get("isbn"), "edicao": c.get("edition"),
               "tradutor": c.get("translator"), "titulo_original": c.get("origtitle"),
               "ano_original": (c.get("origdate") or c.get("origyear") or "")[:4] or None, "fonte": "bibtex"}
        ref.update({campo: c.get(bib) for campo, bib in BIB_PAPEIS})
        if tipo in ("artigo", "jornal"):
            ref["periodico"] = c.get("journal") or c.get("journaltitle")
        elif tipo == "capitulo":
            ref["titulo_obra"] = c.get("booktitle")
            ref["organizadores"] = _bib_autores(c.get("editor")) or None
        elif tipo == "evento":
            ref["evento"] = c.get("booktitle")
        elif tipo == "tese":
            ref["tipo_trabalho"] = "Tese" if tipo_bib == "phdthesis" else "Dissertação"
            ref["instituicao"] = c.get("school")
        refs.append({k: v for k, v in ref.items() if v not in (None, "", [])})
    return refs


def _bib_nome(a):
    return "{" + a["entidade"] + "}" if "entidade" in a else f"{a.get('sobrenome', '')}, {a.get('nome', '')}".strip(", ")


def para_bib(ref):
    tipo = TIPO_BIB.get(ref["tipo"])
    if ref["tipo"] == "tese":
        tipo = "phdthesis" if (ref.get("tipo_trabalho") or "").lower().startswith("tese") else "mastersthesis"
    titulo = ref.get("titulo", "") + (": " + ref["subtitulo"] if ref.get("subtitulo") else "")
    campos = [("author", " and ".join(_bib_nome(a) for a in ref.get("autores", []))), ("title", titulo),
              ("year", ref.get("ano")), ("journal", ref.get("periodico")), ("booktitle", ref.get("titulo_obra") or ref.get("evento")),
              ("editor", " and ".join(_bib_nome(a) for a in ref.get("organizadores", []))),
              ("volume", ref.get("volume")), ("number", ref.get("numero")),
              ("pages", str(ref["paginas"]).replace("-", "--") if ref.get("paginas") else None),
              ("publisher", ref.get("editora")), ("address", ref.get("local")), ("edition", ref.get("edicao")),
              ("school", ref.get("instituicao") if ref["tipo"] == "tese" else None),
              ("doi", ref.get("doi")), ("url", ref.get("url")), ("urldate", ref.get("acesso")), ("isbn", ref.get("isbn")),
              ("translator", " and ".join(ref["tradutor"]) if isinstance(ref.get("tradutor"), list) else ref.get("tradutor")),
              ("origtitle", ref.get("titulo_original")), ("origdate", ref.get("ano_original")),
              ("date", ref.get("data")), ("eid", ref.get("eloc")), ("section", ref.get("caderno")),
              ("entrysubtype", "newspaper" if ref["tipo"] == "jornal" else None)]
    campos += [(bib, ref.get(campo)) for campo, bib in BIB_PAPEIS]
    if ref["tipo"] == "capitulo" and ref.get("volume_obra") and not ref.get("volume"):
        campos.append(("volume", ref["volume_obra"]))
    if not ref.get("ano") and ref.get("data"):
        campos[2] = ("year", str(ref["data"])[:4])
    linhas = [f"  {k} = {{{v}}}" for k, v in campos if v not in (None, "")]
    return f"@{tipo}{{{ref['id']},\n" + ",\n".join(linhas) + "\n}"


# ---------------------------------------------------------------- RIS

RIS_TIPO = {"JOUR": "artigo", "BOOK": "livro", "CHAP": "capitulo", "CONF": "evento", "CPAPER": "evento",
            "THES": "tese", "ELEC": "site", "WEB": "site", "STAT": "legislacao", "BILL": "legislacao",
            "NEWS": "jornal", "MGZN": "artigo"}
TIPO_RIS = {"artigo": "JOUR", "jornal": "NEWS", "livro": "BOOK", "capitulo": "CHAP", "evento": "CPAPER", "tese": "THES",
            "site": "ELEC", "legislacao": "STAT"}


def ler_ris(texto):
    refs, atual = [], None
    for linha in texto.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", linha)
        if not m:
            continue
        tag, valor = m.group(1), m.group(2).strip()
        if tag == "TY":
            atual = {"tipo": RIS_TIPO.get(valor, "livro"), "autores": [], "fonte": "ris"}
        elif atual is None:
            continue
        elif tag == "ER":
            refs.append({k: v for k, v in atual.items() if v not in (None, "", [])})
            atual = None
        elif tag in ("AU", "A1"):
            atual["autores"].append(A.separar_nome(valor))
        elif tag in ("TI", "T1"):
            atual["titulo"] = valor
        elif tag in ("T2", "JO", "JF"):
            atual["periodico" if atual["tipo"] in ("artigo", "jornal") else "titulo_obra"] = valor
        elif tag in ("PY", "Y1", "DA"):
            m2 = re.search(r"\d{4}", valor)
            if m2:
                atual.setdefault("ano", m2.group(0))
            m3 = re.match(r"(\d{4})/(\d{1,2})(?:/(\d{1,2}))?", valor)
            if tag == "DA" and m3:
                atual["data"] = "-".join(f"{int(g):02d}" if i else g for i, g in enumerate(m3.groups()) if g)
        else:
            campo = {"VL": "volume", "IS": "numero", "DO": "doi", "UR": "url", "PB": "editora", "CY": "local",
                     "SN": "isbn", "ET": "edicao"}.get(tag)
            if campo:
                atual[campo] = valor
            elif tag == "SP":
                atual["paginas"] = valor
            elif tag == "EP" and atual.get("paginas"):
                atual["paginas"] += "-" + valor
    return refs


def para_ris(ref):
    linhas = [f"TY  - {TIPO_RIS.get(ref['tipo'], 'GEN')}"]
    for a in ref.get("autores", []):
        linhas.append("AU  - " + (a.get("entidade") or f"{a.get('sobrenome', '')}, {a.get('nome', '')}".strip(", ")))
    pares = [("TI", ref.get("titulo") + (": " + ref["subtitulo"] if ref.get("subtitulo") else "") if ref.get("titulo") else None),
             ("T2", ref.get("periodico") or ref.get("titulo_obra") or ref.get("evento")), ("PY", A.ano_de_data(ref)),
             ("VL", ref.get("volume")), ("IS", ref.get("numero")), ("PB", ref.get("editora")), ("CY", ref.get("local")),
             ("DO", ref.get("doi")), ("UR", ref.get("url")), ("SN", ref.get("isbn") or ref.get("issn")),
             ("DA", str(ref["data"]).replace("-", "/") if ref.get("data") else None)]
    if ref.get("eloc") and not ref.get("paginas"):
        pares.append(("SP", ref["eloc"]))
    if ref.get("paginas"):
        ini, _, fim = str(ref["paginas"]).partition("-")
        pares += [("SP", ini), ("EP", fim or None)]
    linhas += [f"{k}  - {v}" for k, v in pares if v not in (None, "")]
    linhas.append("ER  - ")
    return "\n".join(linhas)


# ---------------------------------------------------------------- CSL-JSON (Zotero, Mendeley, Pandoc)

TIPO_CSL = {"artigo": "article-journal", "jornal": "article-newspaper", "livro": "book", "capitulo": "chapter",
            "evento": "paper-conference", "tese": "thesis", "site": "webpage", "legislacao": "legislation"}


def _partes_data(ref):
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", str(ref.get("data") or ""))
    if m:
        return [int(g) for g in m.groups() if g]
    if str(ref.get("ano", "")).isdigit():
        return [int(ref["ano"])] + ([int(ref["mes"])] if str(ref.get("mes", "")).isdigit() else [])
    return None


def para_csl(ref):
    def nomes(lista):
        return [{"literal": a["entidade"]} if "entidade" in a else {"family": a.get("sobrenome"), "given": a.get("nome")}
                for a in lista or []]
    partes = _partes_data(ref)
    item = {"id": ref["id"], "type": TIPO_CSL.get(ref["tipo"], "document"), "title": ref.get("titulo"),
            "author": nomes(ref.get("autores")), "editor": nomes(ref.get("organizadores")) or None,
            "container-title": ref.get("periodico") or ref.get("titulo_obra") or ref.get("evento"),
            "publisher": ref.get("editora"), "publisher-place": ref.get("local"),
            "volume": ref.get("volume") or ref.get("volume_obra"), "section": ref.get("caderno"),
            "issue": ref.get("numero"), "page": ref.get("paginas") or ref.get("eloc"), "DOI": ref.get("doi"),
            "URL": ref.get("url"), "ISBN": ref.get("isbn"), "issued": {"date-parts": [partes]} if partes else None,
            "illustrator": [{"literal": ref["ilustracao"]}] if isinstance(ref.get("ilustracao"), str) else None,
            "translator": [{"literal": t} for t in (ref["tradutor"] if isinstance(ref.get("tradutor"), list)
                                                     else [ref["tradutor"]])] if ref.get("tradutor") else None,
            "original-title": ref.get("titulo_original"),
            "original-date": {"date-parts": [[int(ref["ano_original"])]]} if str(ref.get("ano_original", "")).isdigit() else None}
    return {k: v for k, v in item.items() if v not in (None, "", [])}


CSL_TIPO = {v: k for k, v in TIPO_CSL.items()} | {"article": "artigo", "article-magazine": "artigo",
                                                  "post-weblog": "site", "report": "livro"}


def ler_csl(item):
    """CSL-JSON (Zotero, Mendeley, Pandoc) -> modelo desta biblioteca."""
    def nomes(lista):
        return [{"entidade": n["literal"]} if n.get("literal") else {"sobrenome": n.get("family", ""), "nome": n.get("given", "")}
                for n in lista or []]
    partes = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
    tipo = CSL_TIPO.get(item.get("type"), "livro")
    titulo, _, sub = (item.get("title") or "").partition(": ")
    ref = {"id": re.sub(r"[^a-z0-9]", "", str(item.get("id", "")).lower()) or None, "tipo": tipo,
           "titulo": titulo or None, "subtitulo": sub or None, "autores": nomes(item.get("author")),
           "organizadores": nomes(item.get("editor")) or None, "ano": partes[0] if partes else None,
           "editora": item.get("publisher"), "local": item.get("publisher-place"), "volume": item.get("volume"),
           "numero": item.get("issue"), "paginas": item.get("page"), "doi": item.get("DOI"), "url": item.get("URL"),
           "isbn": item.get("ISBN"), "fonte": "csl",
           "tradutor": [n.get("literal") or f"{n.get('given', '')} {n.get('family', '')}".strip()
                        for n in item.get("translator") or []] or None,
           "titulo_original": item.get("original-title"),
           "ano_original": (((item.get("original-date") or {}).get("date-parts") or [[None]])[0] or [None])[0],
           "caderno": item.get("section")}
    if partes and len(partes) > 1 and all(isinstance(p, int) for p in partes):
        ref["data"] = "-".join([str(partes[0])] + [f"{p:02d}" for p in partes[1:3]])
    container = item.get("container-title")
    ref.update({"artigo": {"periodico": container}, "jornal": {"periodico": container}, "capitulo": {"titulo_obra": container},
                "evento": {"evento": container}}.get(tipo, {}))
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


# ---------------------------------------------------------------- comandos

def _imprimir(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_adicionar(args, dados):
    import metadados as M
    try:
        if args.doi:
            ref = M.crossref_doi(args.doi)
        elif args.isbn:
            ref = M.livro_por_isbn(args.isbn)
        elif args.url:
            ref = M.pagina_web(args.url, date.today().isoformat())
        elif args.json:
            ref = json.loads(Path(args.json).read_text(encoding="utf-8") if Path(args.json).is_file() else args.json)
            ref.setdefault("fonte", "manual")
        else:
            print("informe --doi, --isbn, --url ou --json", file=sys.stderr)
            return 2
    except M.ErroRede as e:
        _imprimir({"erro": str(e)})
        return 2
    if not ref:
        _imprimir({"erro": "não encontrado na base consultada; nada foi adicionado"})
        return 1
    if ref.get("tipo") not in A.TIPOS:
        _imprimir({"erro": f"tipo inválido: {ref.get('tipo')}"})
        return 2
    ref, dup = adicionar(dados, ref, args.tag)
    if dup:
        _imprimir({"aviso": "já existe na biblioteca", "id": dup["id"]})
        return 0
    salvar(args.arquivo, dados)
    _imprimir({"adicionado": ref["id"], "abnt": A.formatar_referencia(ref, edicao_6023=args.edicao_6023),
               "revisar": ref.get("revisar", [])})
    return 0


def cmd_importar(args, dados):
    texto = Path(args.origem).read_text(encoding="utf-8")
    ext = Path(args.origem).suffix.lower()
    if ext == ".bib":
        refs = ler_bib(texto)
    elif ext == ".ris":
        refs = ler_ris(texto)
    else:
        bruto = json.loads(texto)
        refs = bruto.get("referencias", bruto) if isinstance(bruto, dict) else bruto
        refs = [ler_csl(r) if "type" in r and "tipo" not in r else r for r in refs]
    novos, dups, recusados = [], [], []
    for r in refs:
        if r.get("tipo") not in A.TIPOS:
            recusados.append({"entrada": r.get("titulo") or r.get("id"), "motivo": f"tipo inválido: {r.get('tipo')}"})
            continue
        ref, dup = adicionar(dados, r, args.tag)
        (dups if dup else novos).append(ref["id"])
    salvar(args.arquivo, dados)
    _imprimir({"importados": novos, "duplicatas_ignoradas": dups, "recusados": recusados})
    return 1 if recusados else 0


def _filtrar(dados, args):
    refs = dados["referencias"]
    if getattr(args, "tag", None):
        refs = [r for r in refs if set(args.tag) & set(r.get("tags", []))]
    if getattr(args, "ids", None):
        quer = args.ids.split(",")
        refs = [r for r in refs if r["id"] in quer]
    return refs


def cmd_listar(args, dados):
    for r in A.ordenar(_filtrar(dados, args)):
        marca = " [revisar]" if r.get("revisar") else ""
        print(f"{r['id']}{marca}: {A.formatar_referencia(r, estilo='texto', edicao_6023=args.edicao_6023)}")
    return 0


def cmd_buscar(args, dados):
    termo = _norm(args.termo)
    achados = [r for r in dados["referencias"] if termo in _norm(json.dumps(r, ensure_ascii=False))]
    for r in achados:
        print(f"{r['id']}: {A.formatar_referencia(r, estilo='texto', edicao_6023=args.edicao_6023)}")
    return 0 if achados else 1


def cmd_remover(args, dados):
    antes = len(dados["referencias"])
    dados["referencias"] = [r for r in dados["referencias"] if r["id"] != args.id]
    if len(dados["referencias"]) == antes:
        print(f"id não encontrado: {args.id}", file=sys.stderr)
        return 1
    salvar(args.arquivo, dados)
    print(f"removido: {args.id}")
    return 0


def cmd_citar(args, dados):
    ref = next((r for r in dados["referencias"] if r["id"] == args.id), None)
    if not ref:
        print(f"id não encontrado: {args.id}", file=sys.stderr)
        return 1
    suf = A.sufixos_mesmo_autor_ano(dados["referencias"]).get(ref["id"], "")
    resposta = {"chamada": A.chamada(ref, args.pagina, args.narrativa, args.edicao_10520, suf, args.ano_original),
                "referencia": A.formatar_referencia(ref, edicao_6023=args.edicao_6023, max_autores=3 if args.et_al else None)}
    if args.ano_original:
        resposta["aviso"] = ("o ano original entre colchetes é costume (filosofia, clássicos); a NBR 10520:2023 não o prevê. "
                             "Use só se o curso ou o orientador aceitar." if ref.get("ano_original")
                             else "esta entrada não tem ano_original; a chamada saiu sem ele")
    _imprimir(resposta)
    return 0


def com_sufixo(ref, sufixos):
    """Mesmo autor e ano: a referência leva o mesmo 2010a/2010b da chamada (NBR 10520)."""
    suf = sufixos.get(ref.get("id"), "")
    ano = A.ano_de_data(ref)
    return dict(ref, ano=f"{ano}{suf}") if suf and ano else ref


def _estilo_saida(caminho):
    caminho = caminho or ""
    return "html" if caminho.endswith(".html") else ("texto" if caminho.endswith(".txt") else "md")


def cmd_nota(args, dados):
    ref = next((r for r in dados["referencias"] if r["id"] == args.id), None)
    if not ref:
        print(f"id não encontrado: {args.id}", file=sys.stderr)
        return 1
    suf = A.sufixos_mesmo_autor_ano(dados["referencias"]).get(ref["id"], "")
    resposta = {"forma": args.forma,
                "nota": A.nota_referencia(ref, args.forma, args.pagina, edicao_6023=args.edicao_6023,
                                          max_autores=3 if args.et_al else None, sufixo_ano=suf,
                                          maiusculas=not args.minusculas)}
    if args.forma in ("ibid", "idem", "opcit", "loccit"):
        resposta["aviso"] = "expressão latina: só em nota e de preferência na mesma página da nota a que se refere"
    _imprimir(resposta)
    return 0


def cmd_notas(args, dados):
    """Sequência de notas de rodapé: primeira citação completa, as seguintes abreviadas."""
    bruto = Path(args.sequencia).read_text(encoding="utf-8") if Path(args.sequencia).is_file() else args.sequencia
    try:
        itens = json.loads(bruto)
    except ValueError:
        # Formato curto: "freud2010luto:172, freud2010luto:180, hobbes1651leviata:cap. XIII"
        itens = []
        for parte in [p.strip() for p in bruto.split(",") if p.strip()]:
            rid, _, pag = parte.partition(":")
            itens.append({"id": rid.strip(), "pagina": pag.strip() or None})
    try:
        notas = A.notas_em_sequencia(dados["referencias"], itens, _estilo_saida(args.saida), args.edicao_6023,
                                     3 if args.et_al else None, args.expressoes_latinas, not args.minusculas)
    except KeyError as e:
        print(f"id não encontrado: {e.args[0]}", file=sys.stderr)
        return 1
    if args.saida:
        Path(args.saida).write_text("\n".join(f"{n['n']}. {n['nota']}" for n in notas) + "\n", encoding="utf-8")
        print(f"{len(notas)} notas -> {args.saida}")
    else:
        _imprimir({"notas": notas,
                   "aviso": "notas curtas em MAIÚSCULAS seguem os exemplos de guias de 2023 (UFSCar); a NBR 10520:2023 "
                            "não fixa a caixa da nota abreviada. Use --minusculas se o curso pedir."})
    return 0


def cmd_exportar(args, dados):
    refs = A.ordenar(_filtrar(dados, args))
    if args.formato == "abnt":
        estilo = _estilo_saida(args.saida)
        sufixos = A.sufixos_mesmo_autor_ano(dados["referencias"])
        saida = "\n\n".join(A.formatar_referencia(com_sufixo(r, sufixos), estilo=estilo, edicao_6023=args.edicao_6023,
                                                  max_autores=3 if args.et_al else None) for r in refs)
    elif args.formato == "bib":
        saida = "\n\n".join(para_bib(r) for r in refs)
    elif args.formato == "ris":
        saida = "\n\n".join(para_ris(r) for r in refs)
    else:
        saida = json.dumps([para_csl(r) for r in refs], ensure_ascii=False, indent=2)
    if args.saida:
        Path(args.saida).write_text(saida + "\n", encoding="utf-8")
        print(f"{len(refs)} referências -> {args.saida}")
    else:
        print(saida)
    return 0


def cmd_deduplicar(args, dados):
    refs, grupos, vistos = dados["referencias"], [], set()
    for i, a in enumerate(refs):
        if a["id"] in vistos:
            continue
        grupo = [a] + [b for b in refs[i + 1:] if b["id"] not in vistos and mesma_obra(a, b)]
        if len(grupo) > 1:
            grupos.append([g["id"] for g in grupo])
            vistos.update(g["id"] for g in grupo)
    if args.aplicar and grupos:
        remover = {gid for g in grupos for gid in g[1:]}
        dados["referencias"] = [r for r in refs if r["id"] not in remover]
        salvar(args.arquivo, dados)
    _imprimir({"grupos_duplicados": grupos, "aplicado": bool(args.aplicar and grupos)})
    return 0


def cmd_faltantes(args, dados):
    rel = {r["id"]: A.faltantes(r) for r in dados["referencias"] if A.faltantes(r)}
    _imprimir(rel)
    return 1 if rel else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", default="biblioteca.json")
    ap.add_argument("--edicao-6023", default=A.EDICAO_6023_PADRAO, choices=A.EDICOES_6023)
    ap.add_argument("--edicao-10520", default=A.EDICAO_10520_PADRAO, choices=A.EDICOES_10520)
    ap.add_argument("--et-al", action="store_true", help="com 4+ autores, lista o primeiro e et al.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("adicionar")
    s.add_argument("--doi"); s.add_argument("--isbn"); s.add_argument("--url"); s.add_argument("--json")
    s.add_argument("--tag", action="append")
    s = sub.add_parser("importar"); s.add_argument("origem"); s.add_argument("--tag", action="append")
    s = sub.add_parser("listar"); s.add_argument("--tag", action="append")
    s = sub.add_parser("buscar"); s.add_argument("termo")
    s = sub.add_parser("remover"); s.add_argument("id")
    s = sub.add_parser("citar"); s.add_argument("id"); s.add_argument("--pagina"); s.add_argument("--narrativa", action="store_true")
    s.add_argument("--ano-original", action="store_true", help="(Kant, 2015 [1781]): costume, fora da NBR 10520")
    s = sub.add_parser("nota"); s.add_argument("id"); s.add_argument("--pagina", "--localizador", dest="pagina")
    s.add_argument("--forma", choices=A.FORMAS_NOTA, default="completa")
    s.add_argument("--minusculas", action="store_true", help="nota curta como (Freud, 2010): Freud, 2010, p. 20.")
    s = sub.add_parser("notas", help="sequência de notas: primeira completa, depois abreviadas")
    s.add_argument("sequencia", help='JSON [{"id":..,"pagina":..}] (texto ou arquivo) ou "id:pág, id:pág"')
    s.add_argument("--expressoes-latinas", action="store_true", help="Ibid. e Id. quando a nota anterior permite")
    s.add_argument("--minusculas", action="store_true"); s.add_argument("--saida")
    s = sub.add_parser("exportar"); s.add_argument("--formato", choices=["abnt", "bib", "ris", "csl"], default="abnt")
    s.add_argument("--saida"); s.add_argument("--ids"); s.add_argument("--tag", action="append")
    s = sub.add_parser("deduplicar"); s.add_argument("--aplicar", action="store_true")
    sub.add_parser("faltantes")
    args = ap.parse_args(argv)
    dados = carregar(args.arquivo)
    return globals()["cmd_" + args.cmd](args, dados)


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main())
