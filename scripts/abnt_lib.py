"""Núcleo ABNT: modelo de referência, formatação (NBR 6023) e chamadas (NBR 10520).

Só usa a biblioteca padrão. Os demais scripts importam este módulo.

Modelo de referência (dict, campos opcionais exceto "tipo"):
    id, tipo (livro | capitulo | artigo | jornal | tese | site | evento | legislacao),
    autores: [{"sobrenome": "Silva", "nome": "João Carlos"} | {"entidade": "Universidade de São Paulo", "sigla": "USP"}],
    titulo, subtitulo, titulo_atribuido (true: título dado por quem cita, sai entre colchetes),
    edicao, local, editora, sem_local / sem_editora (true: conferido, a obra não traz; sai [S. l.] / [s. n.]), ano, mes, data (AAAA-MM-DD ou AAAA-MM: jornal, site, periódico diário),
    volume, numero, paginas, eloc (e-localização: e2023301118, art. 428), caderno (jornal),
    periodico, doi, url, acesso (AAAA-MM-DD), isbn, issn,
    organizadores (lista de autores) + papel_org ("org." | "ed." | "coord."), titulo_obra, subtitulo_obra,
    in_mesmo_autor (true: capítulo do próprio autor da obra; repete o autor depois de "In:", sem papel),
    volume_obra (volume da obra no todo: "v. 14, p. 161-239"),
    tradutor ("Ivo Korytowski" ou lista), titulo_original, ano_original (obra traduzida ou reeditada),
    responsabilidades ([{"papel": "Organização", "nome": "Richard Tuck"}]) ou os atalhos
    organizacao, revisao, prefacio, introducao, notas_de, ilustracao (vão depois do título, como a tradução),
    paginas_total (livro: "320" vira "320 p."),
    tipo_trabalho ("Tese" | "Dissertação" | "Trabalho de Conclusão de Curso"), grau ("Doutorado em Educação"),
    orientador, folhas (tese: "180" vira "180 f."), unidade ("Faculdade de Educação"), instituicao, evento, evento_numero, evento_ano, evento_local,
    titulo_anais ("Anais"), jurisdicao, epigrafe, ementa, publicacao, nota.

Metadados de controle (gravados pela biblioteca, não saem na referência): fonte (base de onde veio),
revisar (o que faltava quando entrou), tags.

Regra de ouro: nada é inventado. Campo obrigatório ausente vira "[VERIFICAR: campo]".
"""
import re
import unicodedata
from datetime import date

EDICOES_6023 = ("2025", "2018")
EDICAO_6023_PADRAO = "2025"
EDICOES_10520 = ("2023", "2002")
EDICAO_10520_PADRAO = "2023"

MESES = ["jan.", "fev.", "mar.", "abr.", "maio", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]
AGNOMES = {"neto", "netto", "filho", "filha", "junior", "júnior", "jr.", "sobrinho", "segundo", "terceiro"}
PARTICULAS = {"da", "das", "de", "do", "dos", "e", "d'", "del", "della", "van", "von", "der"}
TIPOS = ("livro", "capitulo", "artigo", "jornal", "tese", "site", "evento", "legislacao")
# Artigo ou monossílabo inicial entra em maiúsculas junto com a palavra seguinte (NBR 6023 e 10520)
INICIAIS_FRACAS = {"a", "o", "as", "os", "um", "uma", "uns", "umas", "à", "às", "ao", "aos", "de", "da", "do", "das",
                   "dos", "em", "no", "na", "nos", "nas", "por", "com", "sem", "sob", "e", "ou", "se", "que", "the",
                   "an", "le", "la", "les", "l'", "el", "los", "las", "il", "lo", "der", "die", "das", "ein", "eine"}
# Cidades com homônimas conhecidas: a NBR 6023 manda acrescentar estado ou país
LOCAIS_HOMONIMOS = {"cambridge", "birmingham", "portland", "springfield", "richmond", "washington", "santa cruz",
                    "santa maria", "bom jesus", "viçosa", "córdoba", "valença"}


def verificar(campo):
    return f"[VERIFICAR: {campo}]"


def sem_acento(texto):
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()


def caixa_alta(texto):
    return (texto or "").upper()


# ---------------------------------------------------------------- nomes

def separar_nome(nome_completo):
    """'João Carlos da Silva Neto' -> {'sobrenome': 'Silva Neto', 'nome': 'João Carlos da'}.

    A partícula fica com o prenome, como pede a NBR 6023 (SILVA, João da).
    Nome no formato 'Silva, João' é respeitado.
    """
    nome_completo = " ".join((nome_completo or "").split())
    if not nome_completo:
        return {}
    if "," in nome_completo:
        sob, _, pre = nome_completo.partition(",")
        return {"sobrenome": sob.strip(), "nome": pre.strip()}
    partes = nome_completo.split(" ")
    if len(partes) == 1:
        return {"sobrenome": partes[0], "nome": ""}
    sob = [partes.pop()]
    if sob[0].lower() in AGNOMES and len(partes) > 1:
        sob.insert(0, partes.pop())
    return {"sobrenome": " ".join(sob), "nome": " ".join(partes)}


def abreviar_prenome(nome):
    saida = []
    for p in nome.split():
        if p.lower() in PARTICULAS:
            continue
        saida.append(p[0].upper() + ".")
    return " ".join(saida)


def formatar_autor(autor, abreviar=False):
    if "entidade" in autor:
        nome = caixa_alta(autor["entidade"])
        sigla = autor.get("sigla")
        # Com sigla, a chamada sai (IIMM, 2024): a referência precisa mostrar a sigla para o leitor achar a entrada
        return f"{nome} ({sigla})" if sigla and caixa_alta(sigla) != nome else nome
    sob = caixa_alta(autor.get("sobrenome", ""))
    nome = autor.get("nome", "")
    if abreviar:
        nome = abreviar_prenome(nome)
    return f"{sob}, {nome}" if nome else sob


def formatar_autores(autores, abreviar=False, max_autores=None):
    """Lista de autores separada por ponto e vírgula.

    Com max_autores=3 e quatro ou mais autores, lista o primeiro e usa et al.
    (opção permitida pela NBR 6023). Com None, lista todos.
    """
    autores = autores or []
    if max_autores and len(autores) > max_autores:
        return formatar_autor(autores[0], abreviar) + " et al."
    return "; ".join(formatar_autor(a, abreviar) for a in autores)


# ---------------------------------------------------------------- partes

def destacar(texto, estilo):
    if not texto:
        return texto
    if estilo == "md":
        return f"**{texto}**"
    if estilo == "html":
        return f"<strong>{texto}</strong>"
    return texto


def colchetes(titulo, atribuido):
    """Título atribuído por quem cita (a obra não tem título) vai entre colchetes."""
    if atribuido and titulo and not titulo.startswith("["):
        return f"[{titulo}]"
    return titulo


def titulo_completo(titulo, subtitulo, estilo, destaque=True, atribuido=False):
    """Título em destaque; o subtítulo vem depois de dois-pontos e sem destaque."""
    t = colchetes(titulo, atribuido) or verificar("título")
    t = destacar(t, estilo) if destaque else t
    return f"{t}: {subtitulo}" if subtitulo else t


def palavras_de_entrada(titulo):
    """Quantas palavras iniciais entram em destaque: 1, ou 2 se a primeira for artigo ou monossílabo."""
    partes = (titulo or "").split()
    if len(partes) > 1 and partes[0].lower().strip("\"'“”") in INICIAIS_FRACAS:
        return 2
    return 1


def entrada_por_titulo(titulo):
    """Sem autoria, a entrada é pelo título com a primeira palavra em maiúsculas.

    Artigo ou monossílabo inicial vai em maiúsculas junto com a palavra seguinte: A SOCIEDADE do espetáculo.
    """
    titulo = titulo or verificar("título")
    if titulo.startswith("[VERIFICAR"):
        return titulo
    n = palavras_de_entrada(titulo)
    partes = titulo.split(" ", n)
    cabeca = caixa_alta(" ".join(partes[:n]))
    return cabeca + (" " + partes[n] if len(partes) > n else "")


def local_editora(ref):
    local, editora = ref.get("local"), ref.get("editora")
    if not local and not editora:
        return "[S. l.: s. n.]"  # NBR 6023: sem local e sem editora, num colchete só
    return f"{local or '[S. l.]'}: {editora or '[s. n.]'}"


def ano_de(ref):
    ano = ano_de_data(ref)
    return str(ano) if ano else verificar("ano")


def data_acesso(iso):
    try:
        d = date.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return verificar("data de acesso (AAAA-MM-DD)")
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def data_publicacao(ref):
    """'26 out. 2021' (campo data AAAA-MM-DD), 'out. 2021' (AAAA-MM ou mes) ou só o ano."""
    bruto = str(ref.get("data") or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", bruto)
    if m and 1 <= int(m.group(2)) <= 12:
        mes = MESES[int(m.group(2)) - 1]
        dia = f"{int(m.group(3))} " if m.group(3) else ""
        return f"{dia}{mes} {m.group(1)}"
    ano = ano_de(ref)
    if ref.get("mes"):
        try:
            return f"{MESES[int(ref['mes']) - 1]} {ano}"
        except (ValueError, IndexError):
            pass
    return ano


def ano_de_data(ref):
    """Ano para chamada e ordenação: campo ano, ou o ano do campo data."""
    if ref.get("ano"):
        return ref["ano"]
    m = re.match(r"(\d{4})", str(ref.get("data") or ""))
    return m.group(1) if m else None


RE_ELOC = re.compile(r"(?i)(e\d{3,}|[a-z]{2,6}\d{2,}|art\.\s*\d+)")


def eh_eloc(valor):
    """e2023301118, eabe5641, pgaf310, art. 428: identificador de artigo, não página."""
    return bool(RE_ELOC.fullmatch(str(valor or "").strip()))


def paginas(ref, prefixo="p. "):
    p = ref.get("paginas")
    if not p:
        return ""
    p = str(p).replace("–", "-").replace("—", "-")
    return f"{prefixo}{p}"


def edicao(ref):
    e = ref.get("edicao")
    if not e or str(e).strip() in ("1", "1."):
        return ""
    e = str(e).strip().rstrip(".").replace(" ed", "").strip()
    return f"{e}. ed."


def doi_url(doi):
    doi = (doi or "").strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return f"https://doi.org/{doi}" if doi else ""


def eletronico(ref):
    partes = []
    if ref.get("doi"):
        partes.append(f"DOI: {doi_url(ref['doi'])}.")
    if ref.get("url"):
        partes.append(f"Disponível em: {ref['url']}.")
        partes.append(f"Acesso em: {data_acesso(ref.get('acesso'))}.")
    return " ".join(partes)


def juntar(*partes):
    texto = " ".join(p.strip() for p in partes if p and p.strip())
    texto = re.sub(r"(?<!\.)\.\.(?!\.)", ".", texto)  # ponto duplo, preservando reticências
    texto = re.sub(r"([?!])\.(?=\s|$)", r"\1", texto)  # título interrogativo: "...X?." vira "...X?"
    return re.sub(r"\s+", " ", texto).strip()


def responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=True):
    """Devolve (abertura, titulo) conforme haja autoria ou não."""
    autores = ref.get("autores")
    if autores:
        abertura = formatar_autores(autores, abreviar, max_autores)
        if not abertura.endswith("."):
            abertura += "."
        tit = titulo_completo(ref.get("titulo"), ref.get("subtitulo"), estilo, titulo_destacado,
                              ref.get("titulo_atribuido"))
        return abertura, tit
    tit = entrada_por_titulo(colchetes(ref.get("titulo"), ref.get("titulo_atribuido")))
    if ref.get("subtitulo"):
        tit += ": " + ref["subtitulo"]
    return "", tit


# ---------------------------------------------------------------- tipos

PAPEIS_ATALHO = (("tradutor", "Tradução"), ("organizacao", "Organização"), ("revisao", "Revisão"),
                 ("prefacio", "Prefácio"), ("introducao", "Introdução"), ("notas_de", "Notas"),
                 ("ilustracao", "Ilustrações"))


def _lista_nomes(t):
    if isinstance(t, (list, tuple)):
        t = [str(x) for x in t if x]
        return " e ".join([", ".join(t[:-1]), t[-1]]) if len(t) > 1 else (t[0] if t else "")
    return str(t)


def responsabilidades(ref):
    """[(papel, nomes)] na ordem: atalhos (tradutor primeiro) e depois a lista livre."""
    saida = [(papel, _lista_nomes(ref[campo])) for campo, papel in PAPEIS_ATALHO if ref.get(campo)]
    for item in ref.get("responsabilidades") or []:
        if isinstance(item, dict) and item.get("papel") and item.get("nome"):
            saida.append((str(item["papel"]).strip().rstrip(":"), _lista_nomes(item["nome"])))
    return saida


def traducao(ref):
    """'Tradução: Nome. Organização: Nome.' logo depois do título e antes da edição (NBR 6023)."""
    return " ".join(f"{papel}: {nomes.rstrip('.')}." for papel, nomes in responsabilidades(ref) if nomes)


def complementos_originais(ref):
    """Elementos complementares no fim: título original e data da publicação original."""
    partes = []
    if ref.get("titulo_original"):
        partes.append(f"Título original: {str(ref['titulo_original']).rstrip('.')}.")
    if ref.get("ano_original"):
        partes.append(f"Publicação original: {ref['ano_original']}.")
    return " ".join(partes)


def _volume(valor):
    v = str(valor or "").strip()
    if not v:
        return ""
    return v if re.match(r"(?i)(v|t|vol)\.\s", v) else f"v. {v}"


def _livro(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores)
    vol = _volume(ref.get("volume_obra") or ref.get("volume"))
    loc = ref.get("_localizador")  # nota de rodapé: a passagem citada no lugar do total de páginas
    fisica = ", ".join(p for p in [vol, loc] if p) if loc else vol
    return juntar(abertura, tit + ".", traducao(ref), edicao(ref), local_editora(ref) + ",", ano_de(ref) + ".",
                  (fisica + ".") if fisica else "",
                  f"{ref['paginas_total']} p." if ref.get("paginas_total") and not loc else "",
                  complementos_originais(ref), eletronico(ref))


def _sem_titulo_destaque(ref):
    """Título do artigo, jornal ou capítulo: sem destaque, com subtítulo e colchetes de título atribuído."""
    tit = colchetes(ref.get("titulo"), ref.get("titulo_atribuido")) or verificar("título")
    return f"{tit}: {ref['subtitulo']}" if ref.get("subtitulo") else tit


def _capitulo(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    orgs = ref.get("organizadores")
    if ref.get("in_mesmo_autor") and ref.get("autores"):
        # Capítulo na obra do próprio autor: In: FREUD, Sigmund. **Obras completas** (sem papel de organizador)
        quem = formatar_autores(ref["autores"], abreviar, max_autores).rstrip(".") + "."
    elif orgs:
        papel = ref.get("papel_org", "org.")
        quem = formatar_autores(orgs, abreviar, max_autores) + f" ({papel})."
    else:
        quem = ""
    obra = titulo_completo(ref.get("titulo_obra") or verificar("título da obra"), ref.get("subtitulo_obra"), estilo)
    vol = _volume(ref.get("volume_obra") or ref.get("volume"))
    if ref.get("_localizador"):  # nota de rodapé: o localizador entra no lugar das páginas do capítulo
        pags = ", ".join(p for p in [vol, ref["_localizador"]] if p) + "."
    else:
        pags = paginas(ref) if ref.get("paginas") else verificar("páginas do capítulo")
        pags = (f"{vol}, {pags}" if vol else pags) + "."
    return juntar(abertura, tit + ".", "In:", quem, obra + ".", traducao(ref), edicao(ref), local_editora(ref) + ",",
                  ano_de(ref) + ".", pags, complementos_originais(ref), eletronico(ref))


def _artigo(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    if ref.get("autores"):
        tit = _sem_titulo_destaque(ref)
    per = destacar(ref.get("periodico") or verificar("periódico"), estilo)
    meio = [per]
    if ref.get("local"):
        meio.append(ref["local"])
    if ref.get("volume"):
        meio.append(f"v. {ref['volume']}")
    if ref.get("numero"):
        meio.append(f"n. {ref['numero']}")
    eloc = ref.get("eloc")
    if not eloc and eh_eloc(ref.get("paginas")):
        eloc = ref["paginas"]  # identificador de artigo guardado como página: sai sem "p."
    if eloc:
        meio.append(str(eloc).strip())
    elif ref.get("paginas"):
        meio.append(paginas(ref))
    meio.append(data_publicacao(ref))
    return juntar(abertura, tit + ".", ", ".join(meio) + ".", eletronico(ref))


def _jornal(ref, estilo, abreviar, max_autores):
    """AUTOR. Título. **Jornal**, Local, ano 131, n. 42656, 1 ago. 2010. Caderno, p. B1."""
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    if ref.get("autores"):
        tit = _sem_titulo_destaque(ref)
    meio = [destacar(ref.get("periodico") or verificar("nome do jornal"), estilo)]
    meio.append(ref.get("local") or "[S. l.]")
    if ref.get("volume"):
        v = str(ref["volume"])
        meio.append(v if re.match(r"(?i)(ano|v\.)\s", v) else f"ano {v}")
    if ref.get("numero"):
        meio.append(f"n. {ref['numero']}")
    meio.append(data_publicacao(ref) if (ref.get("data") or ref.get("mes")) else verificar("data (dia, mês e ano)"))
    fim = [p for p in [ref.get("caderno"), paginas(ref)] if p]
    return juntar(abertura, tit + ".", ", ".join(meio) + ".", (", ".join(fim) + ".") if fim else "", eletronico(ref))


def _tese(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores)
    tipo = ref.get("tipo_trabalho") or verificar("tipo de trabalho")
    grau = f" ({ref['grau']})" if ref.get("grau") else ""
    inst = ", ".join(p for p in [ref.get("unidade"), ref.get("instituicao") or verificar("instituição"),
                                   ref.get("local") or verificar("local")] if p)
    orientador = f"Orientador: {ref['orientador']}." if ref.get("orientador") else ""
    return juntar(abertura, tit + ".", orientador, ano_de(ref) + ".",
                  f"{ref['folhas']} f." if ref.get("folhas") else "",
                  f"{tipo}{grau} – {inst}, {ano_de(ref)}.", eletronico(ref))


def _site(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores)
    local = ref.get("local") or "[S. l.]"
    meio = f"{local}: {ref['editora']}," if ref.get("editora") else f"{local},"
    if not ref.get("url"):
        ref = dict(ref, url=verificar("URL"))
    return juntar(abertura, tit + ".", meio, data_publicacao(ref) + ".", eletronico(ref))


def _evento(ref, estilo, abreviar, max_autores):
    """In: NOME DO EVENTO, 10., 2020, São Paulo. **Anais** [...]. São Paulo: Editora, 2020. p. 1-10."""
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    dados = [caixa_alta(ref.get("evento") or verificar("nome do evento"))]
    if ref.get("evento_numero"):
        dados.append(f"{str(ref['evento_numero']).rstrip('.')}.")
    dados.append(str(ref.get("evento_ano") or ano_de(ref)))
    if ref.get("evento_local"):
        dados.append(ref["evento_local"])
    elif ref.get("_edicao_6023") == "2018":
        dados.append(verificar("local do evento"))  # na 2025, a cidade só entra se for conhecida
    anais = destacar(ref.get("titulo_anais") or "Anais", estilo) + " [...]"
    return juntar(abertura, tit + ".", "In:", ", ".join(dados) + ".", anais + ".", local_editora(ref) + ",",
                  ano_de(ref) + ".", (paginas(ref) + ".") if ref.get("paginas") else "", eletronico(ref))


def _legislacao(ref, estilo, abreviar, max_autores):
    jur = caixa_alta(ref.get("jurisdicao") or "BRASIL")
    epi = ref.get("epigrafe") or verificar("epígrafe (ex.: Lei nº 9.610, de 19 de fevereiro de 1998)")
    partes = [jur + ".", epi + "."]
    if ref.get("ementa"):
        partes.append(ref["ementa"].rstrip(".") + ".")
    if ref.get("publicacao"):
        pub = ref["publicacao"]
        nome, _, resto = pub.partition(",")
        partes.append(destacar(nome.strip(), estilo) + ("," + resto if resto else "") + ".")
    partes.append(eletronico(ref))
    return juntar(*partes)


FORMATADORES = {
    "livro": _livro, "capitulo": _capitulo, "artigo": _artigo, "jornal": _jornal, "tese": _tese,
    "site": _site, "evento": _evento, "legislacao": _legislacao,
}


def formatar_referencia(ref, estilo="md", edicao_6023=EDICAO_6023_PADRAO, abreviar=False, max_autores=None):
    """Referência completa segundo a NBR 6023.

    estilo: "md" (**negrito**), "html" ou "texto" (sem marca de destaque).
    edicao_6023: "2025" ou "2018". As duas aceitam listar todos os autores ou
    usar et al. a partir de quatro; a escolha fica em max_autores (None = todos,
    3 = et al. a partir de quatro).
    """
    if edicao_6023 not in EDICOES_6023:
        raise ValueError(f"edição da NBR 6023 desconhecida: {edicao_6023}")
    tipo = ref.get("tipo")
    if tipo not in FORMATADORES:
        raise ValueError(f"tipo de referência desconhecido: {tipo!r} (use um de {', '.join(TIPOS)})")
    texto = FORMATADORES[tipo](dict(ref, _edicao_6023=edicao_6023), estilo, abreviar, max_autores)
    if ref.get("nota"):
        texto = juntar(texto, ref["nota"].rstrip(".") + ".")
    return texto


# ---------------------------------------------------------------- chamadas (NBR 10520)

def eh_sigla(nome):
    """IBGE, UFMG, ABNT: só maiúsculas, até 8 letras."""
    return bool(re.fullmatch(r"[A-ZÀ-Ý]{2,8}", nome or ""))


def _nome_chamada(autor, edicao_10520):
    if "entidade" in autor:
        nome = autor.get("sigla") or autor["entidade"]
        if eh_sigla(nome):
            return nome
    else:
        nome = autor.get("sobrenome", "")
    return caixa_alta(nome) if edicao_10520 == "2002" else nome


# Romano minúsculo válido (xiv, cxl): "civil" ou "mil" não viram página
ROMANO = r"(?=[ivxlcdm])m{0,3}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"


def localizador(pagina, separador=""):
    """'75' -> 'p. 75'; 'B 75', 'local. 264', 'cap. V', '9min 41s' ficam como estão."""
    if not pagina:
        return ""
    pagina = str(pagina).strip()
    # "p." só para número, intervalo ou romano, sozinhos ou em lista ("45, 47", "45-50 e 62");
    # o resto já é localizador próprio
    item = rf"(?:\d+(?:[-–]\d+)?|{ROMANO}(?:[-–]{ROMANO})?)"
    if re.fullmatch(rf"{item}(?:(?:,\s*|\s+e\s+){item})*", pagina):
        return f"{separador}p. {pagina.replace('–', '-')}"
    return f"{separador}{pagina}"


def chamada(ref, pagina=None, narrativa=False, edicao_10520=EDICAO_10520_PADRAO, sufixo_ano="", ano_original=False):
    """Chamada autor-data.

    2023: (Silva, 2020, p. 15) | Silva (2020, p. 15) | (Silva; Souza, 2020) | (Silva et al., 2020)
    2002: (SILVA, 2020, p. 15)
    Sem autoria: primeira palavra do título seguida de [...].
    """
    if edicao_10520 not in EDICOES_10520:
        raise ValueError(f"edição da NBR 10520 desconhecida: {edicao_10520}")
    autores = ref.get("autores") or []
    if autores:
        if len(autores) > 3:
            nomes = _nome_chamada(autores[0], edicao_10520) + " et al."
        else:
            nomes = "; ".join(_nome_chamada(a, edicao_10520) for a in autores)
    else:
        titulo = colchetes(ref.get("titulo"), ref.get("titulo_atribuido")) or verificar("título")
        palavras = titulo.split(" ")[:palavras_de_entrada(titulo)]
        if edicao_10520 == "2002":
            cabeca = caixa_alta(" ".join(palavras))
        else:
            cabeca = " ".join([palavras[0].capitalize()] + palavras[1:])
        nomes = cabeca + " [...]"
    ano = ano_de(ref) + sufixo_ano
    if ano_original and ref.get("ano_original"):
        # Costume em filosofia e clássicos: (Kant, 2015 [1781]). A NBR 10520:2023 não prevê; use só se o curso aceitar.
        ano += f" [{ref['ano_original']}]"
    loc = localizador(pagina, ", ")
    if narrativa:
        if len(autores) > 1 and len(autores) <= 3:
            ultimos = [_nome_chamada(a, edicao_10520) for a in autores]
            nomes = ", ".join(ultimos[:-1]) + " e " + ultimos[-1]
        return f"{nomes} ({ano}{loc})"
    return f"({nomes}, {ano}{loc})"


# ---------------------------------------------------------------- notas de referência (NBR 10520, 4.4)

FORMAS_NOTA = ("completa", "curta", "ibid", "idem", "opcit", "loccit")


def italico(texto, estilo):
    if estilo == "md":
        return f"*{texto}*"
    if estilo == "html":
        return f"<em>{texto}</em>"
    return texto


def nota_referencia(ref, forma="completa", pagina=None, estilo="md", edicao_6023=EDICAO_6023_PADRAO,
                    max_autores=None, sufixo_ano="", maiusculas=True):
    """Texto de uma nota de rodapé de referência.

    completa  referência inteira; o localizador entra no lugar das páginas do capítulo e antes do DOI/URL
    curta     FREUD, 2010a, p. 20.   (maiusculas=False: Freud, 2010a, p. 20.)
    ibid      *Ibid.*, p. 80.        mesma obra da nota anterior
    idem      *Id.*, 2012, p. 30.    mesmo autor da nota anterior, outra obra
    opcit     FREUD, *op. cit.*, p. 40.
    loccit    FREUD, *loc. cit.*
    """
    if forma not in FORMAS_NOTA:
        raise ValueError(f"forma de nota desconhecida: {forma} (use {', '.join(FORMAS_NOTA)})")
    loc = localizador(pagina, ", ")
    if forma == "completa":
        base = {k: v for k, v in ref.items() if k not in ("doi", "url", "acesso", "nota")}
        dentro = ref.get("tipo") in ("livro", "capitulo") and pagina
        if dentro:
            base["_localizador"] = localizador(pagina)
        if ano_de_data(ref) and sufixo_ano:
            base["ano"] = f"{ano_de_data(ref)}{sufixo_ano}"
        texto = formatar_referencia(base, estilo=estilo, edicao_6023=edicao_6023, max_autores=max_autores)
        return juntar(texto, (localizador(pagina) + ".") if pagina and not dentro else "", eletronico(ref),
                      (ref["nota"].rstrip(".") + ".") if ref.get("nota") else "")
    if forma == "ibid":
        return italico("Ibid.", estilo) + (loc + "." if loc else "")
    if forma == "idem":
        return italico("Id.", estilo) + f", {ano_de(ref)}{sufixo_ano}{loc}."
    abreviada = chamada(ref, None, edicao_10520="2002" if maiusculas else "2023", sufixo_ano=sufixo_ano)[1:-1]
    autor = abreviada.rsplit(", ", 1)[0]
    if forma == "opcit":
        return f"{autor}, {italico('op. cit.', estilo)}" + (loc + "." if loc else "")
    if forma == "loccit":
        return f"{autor}, {italico('loc. cit.', estilo)}"  # a expressão já termina em ponto
    return f"{abreviada}{loc}."


def _primeiro_autor(ref):
    autores = ref.get("autores") or []
    if not autores:
        return None
    a = autores[0]
    return sem_acento(a.get("entidade") or a.get("sobrenome", "")).lower()


def notas_em_sequencia(refs, itens, estilo="md", edicao_6023=EDICAO_6023_PADRAO, max_autores=None,
                       latinas=False, maiusculas=True):
    """Numera as notas: primeira citação de cada obra completa, as seguintes abreviadas.

    itens: [{"id": "freud2010luto", "pagina": "20"}, ...] na ordem do texto.
    latinas=True usa *Ibid.* (mesma obra da nota anterior) e *Id.* (mesmo autor, outra obra).
    Devolve [{"n": 1, "id": ..., "forma": ..., "nota": ...}] ou levanta KeyError com o id desconhecido.
    """
    por_id = {r["id"]: r for r in refs}
    sufixos = sufixos_mesmo_autor_ano(refs)
    vistos, anterior, saida = set(), None, []
    for n, item in enumerate(itens, 1):
        rid = item["id"]
        if rid not in por_id:
            raise KeyError(rid)
        ref = por_id[rid]
        if rid not in vistos:
            forma = "completa"
        elif latinas and anterior == rid:
            forma = "ibid"
        elif latinas and anterior and _primeiro_autor(por_id[anterior]) and \
                _primeiro_autor(por_id[anterior]) == _primeiro_autor(ref):
            forma = "idem"
        else:
            forma = "curta"
        texto = nota_referencia(ref, forma, item.get("pagina") or item.get("localizador"), estilo, edicao_6023,
                                max_autores, sufixos.get(rid, ""), maiusculas)
        saida.append({"n": n, "id": rid, "forma": forma, "nota": texto})
        vistos.add(rid)
        anterior = rid
    return saida


# ---------------------------------------------------------------- ordenação e validação

def chave_ordenacao(ref):
    """Ordem alfabética das referências (sistema autor-data), sem acento e sem caixa."""
    autores = ref.get("autores") or []
    if autores:
        a = autores[0]
        base = a.get("entidade") or f"{a.get('sobrenome', '')} {a.get('nome', '')}"
    else:
        base = ref.get("titulo") or ""
    return (sem_acento(base).lower(), str(ano_de_data(ref) or ""), sem_acento(ref.get("titulo") or "").lower())


def ordenar(refs):
    return sorted(refs, key=chave_ordenacao)


def sufixos_mesmo_autor_ano(refs):
    """Mesmo autor e mesmo ano: 2020a, 2020b (NBR 10520). Devolve {id: sufixo}."""
    grupos = {}
    for r in ordenar(refs):
        autores = r.get("autores") or []
        primeiro = (autores[0].get("entidade") or autores[0].get("sobrenome", "")) if autores else r.get("titulo", "")
        chave = (sem_acento(primeiro).lower(), str(ano_de_data(r)))
        grupos.setdefault(chave, []).append(r.get("id"))
    saida = {}
    for ids in grupos.values():
        if len(ids) > 1:
            for i, rid in enumerate(ids):
                saida[rid] = "abcdefghijklmnopqrstuvwxyz"[i]
    return saida


OBRIGATORIOS = {
    "livro": ["autores|titulo", "titulo", "ano"],
    "capitulo": ["titulo", "titulo_obra", "ano", "paginas"],
    "artigo": ["titulo", "periodico", "ano"],
    "tese": ["titulo", "ano", "tipo_trabalho", "instituicao", "local"],
    "site": ["titulo", "url", "acesso"],
    "evento": ["titulo", "evento", "ano"],
    "jornal": ["titulo", "periodico", "data|mes"],
    "legislacao": ["epigrafe"],
}


def faltantes(ref):
    """Campos obrigatórios ausentes para o tipo."""
    falta = []
    for campo in OBRIGATORIOS.get(ref.get("tipo"), []):
        opcoes = campo.split("|")
        if not any(ref.get(c) for c in opcoes):
            falta.append(campo)
    # sem_local / sem_editora: o usuário conferiu a obra e ela não traz o dado; o aviso não volta
    com_editora = ("livro", "capitulo", "evento")  # os que passam por local_editora
    if not ref.get("local") and not ref.get("sem_local") and ref.get("tipo") in com_editora:
        falta.append("local (sairá [S. l.]; se a obra não traz, grave sem_local: true)")
    if not ref.get("editora") and not ref.get("sem_editora") and ref.get("tipo") in com_editora:
        falta.append("editora (sairá [s. n.]; se a obra não traz, grave sem_editora: true)")
    local = sem_acento(str(ref.get("local") or "")).lower().strip()
    if local in {sem_acento(c) for c in LOCAIS_HOMONIMOS}:
        falta.append(f"local '{ref['local']}' tem homônimos: acrescente estado ou país (Cambridge, MA)")
    if ref.get("tipo") == "artigo" and eh_eloc(ref.get("paginas")) and not ref.get("eloc"):
        falta.append(f"'{ref['paginas']}' parece e-localização: mova de paginas para eloc")
    return falta


# Problemas em referências já escritas (texto), para o checador e o conferidor.
PADROES_TEXTO = [
    (r"<https?://[^>]+>", "URL entre < >: a NBR 6023 atual não usa sinais de menor e maior"),
    (r"\bAcesso em:\s*\d{1,2}\s+(janeiro|fevereiro|março|abril|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
     "mês por extenso em 'Acesso em': abrevie (jan., fev., mar., abr., maio, jun., jul., ago., set., out., nov., dez.)"),
    (r"\b[Ss]\.\s?d\.", "'s.d.' não é aceito: indique ano provável entre colchetes, como [2020?]"),
    (r"\bdoi:\s*10\.", "DOI no formato antigo 'doi:10.': use 'DOI: https://doi.org/10.'"),
    (r"\bDisponível em:\s*https?://\S+\s*$", "'Disponível em' sem 'Acesso em' (obrigatório para documento online)"),
    (r"(?i)\[\s*S\.l\.\s*[\]:]|[\[:]\s*s\.n\.\s*\]", "use [S. l.] e [s. n.], com espaço depois do ponto"),
    (r"\[S\. l\.\]:\s*\[s\. n\.\]", "sem local e sem editora: use [S. l.: s. n.], num colchete só"),
    (r"\bet\. al\b", "grafia 'et. al': o correto é 'et al.'"),
    (r"\bAnais\s*\.\.\.", "'Anais...' é forma antiga: use 'Anais [...]'"),
    (r"\b(mai|Jan|Fev|Mar|Abr|Jun|Jul|Ago|Set|Out|Nov|Dez)\.\s*\d{4}",
     "mês abreviado errado: meses em minúsculas e 'maio' por extenso"),
    (r"\bAcesso em:\s*0\d\s", "dia com zero à esquerda em 'Acesso em' (use 7 abr., não 07 abr.)"),
    (r"\bs/d\b|\[s\.\s?d\.\]", "'s/d' ou '[s.d.]' não é aceito: indique ano provável entre colchetes, como [2020?]"),
]


def problemas_texto(referencia_texto):
    """Lista de problemas de forma numa referência já escrita."""
    achados = []
    for padrao, msg in PADROES_TEXTO:
        if re.search(padrao, referencia_texto, flags=re.I if "Acesso" in padrao else 0):
            achados.append(msg)
    if "Disponível em" in referencia_texto and "Acesso em" not in referencia_texto:
        if not any("sem 'Acesso em'" in a for a in achados):
            achados.append("'Disponível em' sem 'Acesso em' (obrigatório para documento online)")
    # Anos de 1000 a 2099 (manuscritos e edições antigas também), ano provável entre colchetes ou [VERIFICAR]
    if not re.search(r"\b(1\d{3}|20\d{2})[a-z]?\b|\[\d{3,4}\??\]|\[ca\. \d{3,4}\]|\[VERIFICAR", referencia_texto):
        achados.append("ano não encontrado")
    return achados


# ---------------------------------------------------------------- leitura de referência em texto

RE_DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)
RE_ANO = re.compile(r"\b(1[5-9]\d{2}|20\d{2})[a-z]?\b")


def ler_referencia_texto(texto):
    """Extrai o mínimo de uma referência ABNT já escrita: autores, título, ano, DOI.

    É heurístico: serve ao checador para buscar a obra nas bases, não para
    reformatar. Campos que não deu para extrair ficam ausentes.
    """
    original = " ".join(texto.split())
    limpo = original.replace("**", "").replace("<strong>", "").replace("</strong>", "")
    ref = {"texto": original}
    m = RE_DOI.search(limpo)
    if m:
        ref["doi"] = m.group(0).rstrip(".,;")
    sem_links = re.sub(r"https?://\S+|DOI:\s*\S+|10\.\d{4,9}/\S+|ISBN[\s:]*[\d\-X]+|ISSN[\s:]*[\d\-X]+", " ", limpo)
    anos = RE_ANO.findall(sem_links.split("Acesso em")[0])
    if anos:
        ref["ano"] = anos[-1][:4]
        m_suf = re.search(r"\b" + anos[-1] + r"([a-z])\b", sem_links.split("Acesso em")[0])
        if m_suf:
            ref["sufixo_ano"] = m_suf.group(1)
    # Autores: segmentos "SOBRENOME, Prenome" no início, separados por ";"
    autores = []
    resto = limpo
    m_aut = re.match(r"^((?:[A-ZÀ-Ý][A-ZÀ-Ý'\- ]+,\s*[^;.]+(?:\.[^;.]+)*?(?:;\s*|\.\s+|\s+et al\.\s*))+)", limpo)
    if m_aut:
        bloco = m_aut.group(1)
        resto = limpo[len(bloco):]
        for parte in re.split(r";\s*", bloco.replace(" et al.", "")):
            parte = parte.strip().rstrip(".")
            if "," in parte:
                sob, _, nome = parte.partition(",")
                autores.append({"sobrenome": sob.strip().title(), "nome": nome.strip()})
    else:
        m_ent = re.match(r"^([A-ZÀ-Ý][A-ZÀ-Ý0-9 \-]{3,})\.\s+", limpo)
        if m_ent:
            autores.append({"entidade": m_ent.group(1).strip().title()})
            resto = limpo[m_ent.end():]
    if autores:
        ref["autores"] = autores
    # Título: até o primeiro ". " ou ": " relevante
    m_tit = re.match(r"\s*(.+?)(?:\.\s|:\s)", resto)
    titulo = (m_tit.group(1) if m_tit else resto).strip()
    titulo = re.sub(r"^In:\s*", "", titulo)
    if titulo:
        ref["titulo"] = titulo
    return ref
