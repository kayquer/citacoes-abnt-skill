"""Busca de metadados em bases abertas e conversão para o modelo de referência.

Bases: Crossref (DOI e busca), OpenAlex, Semantic Scholar, Open Library (ISBN)
e páginas web com meta tags citation_* (Highwire/Google Scholar).

Segurança:
- Metadado externo é dado, nunca instrução. Os textos são limpos de controle
  e de HTML antes de entrar na biblioteca.
- A leitura de URL arbitrária recusa endereços privados, loopback e link-local
  (proteção contra SSRF) e só aceita http/https.
- Nenhum e-mail ou chave é enviado. CROSSREF_MAILTO, S2_API_KEY e GOOGLE_BOOKS_KEY são opcionais
  e vão só para o serviço a que pertencem.

Uso direto:
    py -3 scripts/metadados.py doi 10.1590/0102-4698214500
    py -3 scripts/metadados.py isbn 9788577531639
    py -3 scripts/metadados.py url https://www.scielo.br/j/...
    py -3 scripts/metadados.py buscar "Pedagogia do oprimido" --autor Freire
"""
import html
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abnt_lib as A  # noqa: E402

AGENTE = "citacoes-abnt-skill/1.0 (+https://github.com/kayquer/citacoes-abnt-skill)"
TIMEOUT = 15
PAUSA = 1.0  # segundos entre chamadas à mesma base
_ultima = {}


class ErroRede(Exception):
    pass


def _limpar(texto, limite=600):
    if texto is None:
        return None
    texto = html.unescape(re.sub(r"<[^>]+>", "", str(texto)))
    texto = re.sub(r"[\x00-\x1f\x7f]", " ", texto)
    return " ".join(texto.split())[:limite] or None


def _host_publico(url):
    partes = urllib.parse.urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ErroRede(f"URL recusada (só http/https): {url}")
    try:
        infos = socket.getaddrinfo(partes.hostname, None)
    except socket.gaierror as e:
        raise ErroRede(f"host não resolvido: {partes.hostname}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ErroRede(f"URL recusada: {partes.hostname} aponta para endereço não público ({ip})")


ESPERAS_429 = (3, 10)  # segundos antes de cada nova tentativa quando a base limita a taxa


def _get(url, base, cabecalhos=None, verificar_host=False):
    if verificar_host:
        _host_publico(url)
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "application/json", **(cabecalhos or {})})
    for tentativa in range(len(ESPERAS_429) + 1):
        espera = PAUSA - (time.time() - _ultima.get(base, 0))
        if espera > 0:
            time.sleep(espera)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read(3_000_000), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, ""
            if e.code in (429, 503) and tentativa < len(ESPERAS_429):
                time.sleep(ESPERAS_429[tentativa])
                continue
            raise ErroRede(f"{base}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ErroRede(f"{base}: {e}") from e
        finally:
            _ultima[base] = time.time()
    raise ErroRede(f"{base}: sem resposta")


def _json(url, base, cabecalhos=None):
    if base == "googlebooks" and os.environ.get("GOOGLE_BOOKS_KEY"):
        url += "&key=" + urllib.parse.quote(os.environ["GOOGLE_BOOKS_KEY"])
    dados, _ = _get(url, base, cabecalhos)
    if dados is None:
        return None
    try:
        return json.loads(dados.decode("utf-8"))
    except ValueError as e:
        raise ErroRede(f"{base}: resposta não é JSON") from e


def normalizar_doi(doi):
    doi = (doi or "").strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return doi.rstrip(".,;") if doi.startswith("10.") else None


# ---------------------------------------------------------------- Crossref

TIPOS_CROSSREF = {
    "journal-article": "artigo", "book": "livro", "monograph": "livro", "edited-book": "livro",
    "book-chapter": "capitulo", "proceedings-article": "evento", "dissertation": "tese",
    "posted-content": "site", "report": "livro",
}


def _autores_crossref(lista):
    saida = []
    for a in lista or []:
        if a.get("family"):
            saida.append({"sobrenome": _limpar(a["family"]), "nome": _limpar(a.get("given", "")) or ""})
        elif a.get("name"):
            saida.append({"entidade": _limpar(a["name"])})
    return saida


def _ano_crossref(item):
    for campo in ("published-print", "published-online", "issued", "created"):
        partes = (item.get(campo) or {}).get("date-parts") or [[None]]
        if partes[0] and partes[0][0]:
            return partes[0]
    return [None]


def crossref_para_ref(item):
    data = _ano_crossref(item)
    tipo = TIPOS_CROSSREF.get(item.get("type"), "artigo")
    titulo = _limpar((item.get("title") or [None])[0])
    sub = _limpar((item.get("subtitle") or [None])[0]) if item.get("subtitle") else None
    container = _limpar((item.get("container-title") or [None])[0])
    ref = {
        "tipo": tipo, "autores": _autores_crossref(item.get("author")), "titulo": titulo, "subtitulo": sub,
        "ano": data[0], "mes": data[1] if len(data) > 1 else None, "doi": item.get("DOI"),
        "volume": _limpar(item.get("volume")), "numero": _limpar(item.get("issue")),
        "paginas": _limpar(item.get("page")), "editora": _limpar(item.get("publisher")),
        "issn": (item.get("ISSN") or [None])[0], "isbn": (item.get("ISBN") or [None])[0],
        "fonte": "crossref",
    }
    if tipo == "artigo":
        ref["periodico"] = container
        ref.pop("editora")
    elif tipo == "capitulo":
        ref["titulo_obra"] = container
        ref["organizadores"] = _autores_crossref(item.get("editor"))
    elif tipo == "evento":
        ref["evento"] = container
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


def crossref_doi(doi):
    doi = normalizar_doi(doi)
    if not doi:
        return None
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    if os.environ.get("CROSSREF_MAILTO"):
        url += "?mailto=" + urllib.parse.quote(os.environ["CROSSREF_MAILTO"])
    dados = _json(url, "crossref")
    return crossref_para_ref(dados["message"]) if dados else None


def crossref_buscar(titulo, autor=None, n=5):
    q = {"query.bibliographic": titulo, "rows": str(n)}
    if autor:
        q["query.author"] = autor
    if os.environ.get("CROSSREF_MAILTO"):
        q["mailto"] = os.environ["CROSSREF_MAILTO"]
    dados = _json("https://api.crossref.org/works?" + urllib.parse.urlencode(q), "crossref")
    return [crossref_para_ref(i) for i in (dados or {}).get("message", {}).get("items", [])]


# ---------------------------------------------------------------- OpenAlex

def _openalex_para_ref(w):
    autores = []
    for a in w.get("authorships") or []:
        nome = _limpar((a.get("author") or {}).get("display_name"))
        if nome:
            autores.append(A.separar_nome(nome))
    fonte = ((w.get("primary_location") or {}).get("source") or {})
    bib = w.get("biblio") or {}
    pags = "-".join(p for p in [bib.get("first_page"), bib.get("last_page")] if p) or None
    tipo = {"article": "artigo", "book": "livro", "book-chapter": "capitulo", "dissertation": "tese"}.get(w.get("type"), "artigo")
    ref = {"tipo": tipo, "autores": autores, "titulo": _limpar(w.get("title")), "ano": w.get("publication_year"),
           "doi": normalizar_doi(w.get("doi")), "periodico": _limpar(fonte.get("display_name")) if tipo == "artigo" else None,
           "volume": bib.get("volume"), "numero": bib.get("issue"), "paginas": pags, "fonte": "openalex"}
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


def openalex_buscar(titulo, n=5):
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search": titulo, "per-page": str(n)})
    dados = _json(url, "openalex")
    return [_openalex_para_ref(w) for w in (dados or {}).get("results", [])]


def openalex_doi(doi):
    doi = normalizar_doi(doi)
    if not doi:
        return None
    dados = _json("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe="/"), "openalex")
    return _openalex_para_ref(dados) if dados else None


# ---------------------------------------------------------------- Semantic Scholar

def semantic_buscar(titulo, n=5):
    q = urllib.parse.urlencode({"query": titulo, "limit": str(n), "fields": "title,authors,year,externalIds,venue"})
    cab = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else None
    dados = _json("https://api.semanticscholar.org/graph/v1/paper/search?" + q, "semantic", cab)
    saida = []
    for p in (dados or {}).get("data", []) or []:
        ref = {"tipo": "artigo", "titulo": _limpar(p.get("title")), "ano": p.get("year"),
               "autores": [A.separar_nome(_limpar(a.get("name"))) for a in p.get("authors") or [] if a.get("name")],
               "doi": normalizar_doi((p.get("externalIds") or {}).get("DOI")), "periodico": _limpar(p.get("venue")),
               "fonte": "semantic"}
        saida.append({k: v for k, v in ref.items() if v not in (None, "", [])})
    return saida


# ---------------------------------------------------------------- Open Library (livros)

def openlibrary_isbn(isbn):
    isbn = re.sub(r"[^0-9X]", "", (isbn or "").upper())
    if len(isbn) not in (10, 13):
        return None
    chave = f"ISBN:{isbn}"
    url = "https://openlibrary.org/api/books?" + urllib.parse.urlencode({"bibkeys": chave, "format": "json", "jscmd": "data"})
    dados = _json(url, "openlibrary")
    b = (dados or {}).get(chave)
    if not b:
        return None
    ano = re.search(r"\d{4}", b.get("publish_date", "") or "")
    ref = {"tipo": "livro", "titulo": _limpar(b.get("title")), "subtitulo": _limpar(b.get("subtitle")),
           "autores": [A.separar_nome(_limpar(a.get("name"))) for a in b.get("authors") or []],
           "editora": _limpar((b.get("publishers") or [{}])[0].get("name")),
           "local": _limpar((b.get("publish_places") or [{}])[0].get("name")),
           "ano": int(ano.group(0)) if ano else None, "isbn": isbn, "fonte": "openlibrary"}
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


def openlibrary_buscar(titulo, autor=None, n=5):
    q = {"title": titulo, "limit": str(n)}
    if autor:
        q["author"] = autor
    dados = _json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(q), "openlibrary")
    saida = []
    for d in (dados or {}).get("docs", []):
        ref = {"tipo": "livro", "titulo": _limpar(d.get("title")), "ano": d.get("first_publish_year"),
               "autores": [A.separar_nome(_limpar(n)) for n in d.get("author_name") or []],
               "editora": _limpar((d.get("publisher") or [None])[0]), "fonte": "openlibrary"}
        saida.append({k: v for k, v in ref.items() if v not in (None, "", [])})
    return saida


def googlebooks_isbn(isbn):
    isbn = re.sub(r"[^0-9X]", "", (isbn or "").upper())
    if len(isbn) not in (10, 13):
        return None
    url = "https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode({"q": f"isbn:{isbn}"})
    itens = (_json(url, "googlebooks") or {}).get("items") or []
    if not itens:
        return None
    v = itens[0].get("volumeInfo") or {}
    ano = re.search(r"\d{4}", v.get("publishedDate", "") or "")
    ref = {"tipo": "livro", "titulo": _limpar(v.get("title")), "subtitulo": _limpar(v.get("subtitle")),
           "autores": [A.separar_nome(_limpar(a)) for a in v.get("authors") or []],
           "editora": _limpar(v.get("publisher")), "ano": int(ano.group(0)) if ano else None,
           "isbn": isbn, "fonte": "googlebooks"}
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


def livro_por_isbn(isbn):
    """Open Library primeiro; se não achar, Google Books (cobre melhor editora brasileira)."""
    return openlibrary_isbn(isbn) or googlebooks_isbn(isbn)


def googlebooks_buscar(titulo, autor=None, n=5):
    """Google Books (sem chave). Cobre bem livro nacional, que falta no Crossref."""
    q = f'intitle:"{titulo}"' + (f" inauthor:{autor}" if autor else "")
    url = "https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode({"q": q, "maxResults": str(n)})
    dados = _json(url, "googlebooks")
    saida = []
    for item in (dados or {}).get("items", []) or []:
        v = item.get("volumeInfo") or {}
        ano = re.search(r"\d{4}", v.get("publishedDate", "") or "")
        isbn = next((i["identifier"] for i in v.get("industryIdentifiers") or [] if i.get("type") == "ISBN_13"), None)
        ref = {"tipo": "livro", "titulo": _limpar(v.get("title")), "subtitulo": _limpar(v.get("subtitle")),
               "autores": [A.separar_nome(_limpar(a)) for a in v.get("authors") or []],
               "editora": _limpar(v.get("publisher")), "ano": int(ano.group(0)) if ano else None,
               "isbn": isbn, "fonte": "googlebooks"}
        saida.append({k: v for k, v in ref.items() if v not in (None, "", [])})
    return saida


# ---------------------------------------------------------------- página web (citation_*)

class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.titulo = None
        self._em_titulo = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            nome = (a.get("name") or a.get("property") or "").lower()
            if nome and a.get("content"):
                self.meta.setdefault(nome, []).append(a["content"])
        elif tag == "title":
            self._em_titulo = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._em_titulo = False

    def handle_data(self, data):
        if self._em_titulo and not self.titulo:
            self.titulo = data.strip()


def pagina_web(url, acesso=None):
    """Lê meta tags citation_* da página. Se houver DOI, prefere o Crossref."""
    dados, tipo = _get(url, "web", {"Accept": "text/html"}, verificar_host=True)
    if not dados or "html" not in tipo:
        return None
    p = _Meta()
    p.feed(dados.decode("utf-8", "replace"))
    m = p.meta
    doi = (m.get("citation_doi") or m.get("dc.identifier") or [None])[0]
    if normalizar_doi(doi):
        ref = crossref_doi(doi)
        if ref:
            ref.update({"url": url, "acesso": acesso})
            return ref
    data = (m.get("citation_publication_date") or m.get("citation_date") or m.get("dc.date") or [""])[0]
    ano = re.search(r"\d{4}", data)
    ref = {
        "tipo": "artigo" if m.get("citation_journal_title") else "site",
        "titulo": _limpar((m.get("citation_title") or m.get("og:title") or [p.titulo])[0]),
        "autores": [A.separar_nome(_limpar(n)) for n in m.get("citation_author", [])],
        "periodico": _limpar((m.get("citation_journal_title") or [None])[0]),
        "volume": _limpar((m.get("citation_volume") or [None])[0]),
        "numero": _limpar((m.get("citation_issue") or [None])[0]),
        "editora": _limpar((m.get("citation_publisher") or m.get("og:site_name") or [None])[0]),
        "ano": int(ano.group(0)) if ano else None, "url": url, "acesso": acesso, "fonte": "web",
    }
    return {k: v for k, v in ref.items() if v not in (None, "", [])}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["doi", "isbn", "url", "buscar"])
    ap.add_argument("valor")
    ap.add_argument("--autor")
    ap.add_argument("--abnt", action="store_true", help="imprime também a referência ABNT")
    args = ap.parse_args(argv)
    try:
        if args.modo == "doi":
            res = [crossref_doi(args.valor)]
        elif args.modo == "isbn":
            res = [livro_por_isbn(args.valor)]
        elif args.modo == "url":
            from datetime import date
            res = [pagina_web(args.valor, date.today().isoformat())]
        else:
            res = crossref_buscar(args.valor, args.autor) + openlibrary_buscar(args.valor, args.autor)
    except ErroRede as e:
        print(json.dumps({"erro": str(e)}, ensure_ascii=False))
        return 2
    res = [r for r in res if r]
    if args.abnt:
        for r in res:
            r["abnt"] = A.formatar_referencia(r)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res else 1


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
