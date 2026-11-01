"""Núcleo ABNT: modelo de referência, formatação (NBR 6023) e chamadas (NBR 10520).

Só usa a biblioteca padrão. Os demais scripts importam este módulo.

Modelo de referência (dict, campos opcionais exceto "tipo"):
    id, tipo (livro | capitulo | artigo | tese | site | evento | legislacao),
    autores: [{"sobrenome": "Silva", "nome": "João Carlos"} | {"entidade": "Universidade de São Paulo"}],
    titulo, subtitulo, edicao, local, editora, ano, mes, volume, numero, paginas,
    periodico, doi, url, acesso (AAAA-MM-DD), isbn, issn,
    organizadores (lista de autores) + papel_org ("org." | "ed." | "coord."), titulo_obra, subtitulo_obra,
    tradutor ("Ivo Korytowski" ou lista), titulo_original, ano_original (obra traduzida ou reeditada),
    tipo_trabalho ("Tese" | "Dissertação" | "Trabalho de Conclusão de Curso"), grau ("Doutorado em Educação"),
    unidade ("Faculdade de Educação"), instituicao, evento, evento_numero, evento_ano, evento_local,
    titulo_anais ("Anais"), jurisdicao, epigrafe, ementa, publicacao, nota.

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
TIPOS = ("livro", "capitulo", "artigo", "tese", "site", "evento", "legislacao")


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
        return caixa_alta(autor["entidade"])
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


def titulo_completo(titulo, subtitulo, estilo, destaque=True):
    """Título em destaque; o subtítulo vem depois de dois-pontos e sem destaque."""
    t = titulo or verificar("título")
    t = destacar(t, estilo) if destaque else t
    return f"{t}: {subtitulo}" if subtitulo else t


def entrada_por_titulo(titulo):
    """Sem autoria, a entrada é pelo título com a primeira palavra em maiúsculas."""
    titulo = titulo or verificar("título")
    partes = titulo.split(" ", 1)
    primeira = caixa_alta(partes[0])
    return primeira + (" " + partes[1] if len(partes) > 1 else "")


def local_editora(ref):
    local = ref.get("local") or "[S. l.]"
    editora = ref.get("editora") or "[s. n.]"
    return f"{local}: {editora}"


def ano_de(ref):
    ano = ref.get("ano")
    return str(ano) if ano else verificar("ano")


def data_acesso(iso):
    try:
        d = date.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return verificar("data de acesso (AAAA-MM-DD)")
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


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
    return re.sub(r"\s+", " ", texto).strip()


def responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=True):
    """Devolve (abertura, titulo) conforme haja autoria ou não."""
    autores = ref.get("autores")
    if autores:
        abertura = formatar_autores(autores, abreviar, max_autores)
        if not abertura.endswith("."):
            abertura += "."
        tit = titulo_completo(ref.get("titulo"), ref.get("subtitulo"), estilo, titulo_destacado)
        return abertura, tit
    tit = entrada_por_titulo(ref.get("titulo"))
    if ref.get("subtitulo"):
        tit += ": " + ref["subtitulo"]
    return "", tit


# ---------------------------------------------------------------- tipos

def traducao(ref):
    """'Tradução: Nome.' logo depois do título e antes da edição (NBR 6023)."""
    t = ref.get("tradutor")
    if not t:
        return ""
    if isinstance(t, (list, tuple)):
        t = " e ".join([", ".join(t[:-1]), t[-1]]) if len(t) > 1 else t[0]
    return f"Tradução: {str(t).rstrip('.')}."


def complementos_originais(ref):
    """Elementos complementares no fim: título original e data da publicação original."""
    partes = []
    if ref.get("titulo_original"):
        partes.append(f"Título original: {str(ref['titulo_original']).rstrip('.')}.")
    if ref.get("ano_original"):
        partes.append(f"Publicação original: {ref['ano_original']}.")
    return " ".join(partes)


def _livro(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores)
    return juntar(abertura, tit + ".", traducao(ref), edicao(ref), local_editora(ref) + ",", ano_de(ref) + ".",
                  f"{ref['paginas_total']} p." if ref.get("paginas_total") else "", complementos_originais(ref),
                  eletronico(ref))


def _capitulo(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    orgs = ref.get("organizadores")
    if orgs:
        papel = ref.get("papel_org", "org.")
        quem = formatar_autores(orgs, abreviar, max_autores) + f" ({papel})."
    else:
        quem = ""
    obra = titulo_completo(ref.get("titulo_obra") or verificar("título da obra"), ref.get("subtitulo_obra"), estilo)
    return juntar(abertura, tit + ".", "In:", quem, obra + ".", traducao(ref), edicao(ref), local_editora(ref) + ",",
                  ano_de(ref) + ".", (paginas(ref) + ".") if ref.get("paginas") else verificar("páginas do capítulo") + ".",
                  complementos_originais(ref), eletronico(ref))


def _artigo(ref, estilo, abreviar, max_autores):
    abertura, tit = responsavel(ref, estilo, abreviar, max_autores, titulo_destacado=False)
    if ref.get("subtitulo") and ref.get("autores"):
        tit = f"{ref.get('titulo')}: {ref['subtitulo']}"
    elif ref.get("autores"):
        tit = ref.get("titulo") or verificar("título")
    per = destacar(ref.get("periodico") or verificar("periódico"), estilo)
    meio = [per]
    if ref.get("local"):
        meio.append(ref["local"])
    if ref.get("volume"):
        meio.append(f"v. {ref['volume']}")
    if ref.get("numero"):
        meio.append(f"n. {ref['numero']}")
    if ref.get("paginas"):
        meio.append(paginas(ref))
    data = ano_de(ref)
    if ref.get("mes"):
        try:
            data = f"{MESES[int(ref['mes']) - 1]} {data}"
        except (ValueError, IndexError):
            pass
    meio.append(data)
    return juntar(abertura, tit + ".", ", ".join(meio) + ".", eletronico(ref))


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
    return juntar(abertura, tit + ".", meio, ano_de(ref) + ".", eletronico(ref))


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
    "livro": _livro, "capitulo": _capitulo, "artigo": _artigo, "tese": _tese,
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
        primeira = (ref.get("titulo") or verificar("título")).split(" ")[0]
        nomes = (caixa_alta(primeira) if edicao_10520 == "2002" else primeira.capitalize()) + " [...]"
    ano = ano_de(ref) + sufixo_ano
    if ano_original and ref.get("ano_original"):
        # Costume em filosofia e clássicos: (Kant, 2015 [1781]). A NBR 10520:2023 não prevê; use só se o curso aceitar.
        ano += f" [{ref['ano_original']}]"
    loc = ""
    if pagina:
        pagina = str(pagina)
        # "p." só para número ou intervalo; o resto já é localizador próprio (B 75, local. 264, cap. V, 9min 41s)
        loc = f", p. {pagina}" if re.fullmatch(r"\d+([-–]\d+)?|[ivxlcdm]+", pagina) else f", {pagina}"
    if narrativa:
        if len(autores) > 1 and len(autores) <= 3:
            ultimos = [_nome_chamada(a, edicao_10520) for a in autores]
            nomes = ", ".join(ultimos[:-1]) + " e " + ultimos[-1]
        return f"{nomes} ({ano}{loc})"
    return f"({nomes}, {ano}{loc})"


# ---------------------------------------------------------------- ordenação e validação

def chave_ordenacao(ref):
    """Ordem alfabética das referências (sistema autor-data), sem acento e sem caixa."""
    autores = ref.get("autores") or []
    if autores:
        a = autores[0]
        base = a.get("entidade") or f"{a.get('sobrenome', '')} {a.get('nome', '')}"
    else:
        base = ref.get("titulo") or ""
    return (sem_acento(base).lower(), str(ref.get("ano") or ""), sem_acento(ref.get("titulo") or "").lower())


def ordenar(refs):
    return sorted(refs, key=chave_ordenacao)


def sufixos_mesmo_autor_ano(refs):
    """Mesmo autor e mesmo ano: 2020a, 2020b (NBR 10520). Devolve {id: sufixo}."""
    grupos = {}
    for r in ordenar(refs):
        autores = r.get("autores") or []
        primeiro = (autores[0].get("entidade") or autores[0].get("sobrenome", "")) if autores else r.get("titulo", "")
        chave = (sem_acento(primeiro).lower(), str(r.get("ano")))
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
    "legislacao": ["epigrafe"],
}


def faltantes(ref):
    """Campos obrigatórios ausentes para o tipo."""
    falta = []
    for campo in OBRIGATORIOS.get(ref.get("tipo"), []):
        opcoes = campo.split("|")
        if not any(ref.get(c) for c in opcoes):
            falta.append(campo)
    if not ref.get("local") and ref.get("tipo") in ("livro", "capitulo"):
        falta.append("local (sairá [S. l.])")
    if not ref.get("editora") and ref.get("tipo") in ("livro", "capitulo"):
        falta.append("editora (sairá [s. n.])")
    return falta


# Problemas em referências já escritas (texto), para o checador e o conferidor.
PADROES_TEXTO = [
    (r"<https?://[^>]+>", "URL entre < >: a NBR 6023 atual não usa sinais de menor e maior"),
    (r"\bAcesso em:\s*\d{1,2}\s+(janeiro|fevereiro|março|abril|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
     "mês por extenso em 'Acesso em': abrevie (jan., fev., mar., abr., maio, jun., jul., ago., set., out., nov., dez.)"),
    (r"\b[Ss]\.\s?d\.", "'s.d.' não é aceito: indique ano provável entre colchetes, como [2020?]"),
    (r"\bdoi:\s*10\.", "DOI no formato antigo 'doi:10.': use 'DOI: https://doi.org/10.'"),
    (r"\bDisponível em:\s*https?://\S+\s*$", "'Disponível em' sem 'Acesso em' (obrigatório para documento online)"),
    (r"\[\s*S\.l\.\s*\]|\[\s*s\.n\.\s*\]", "use [S. l.] e [s. n.], com espaço depois do ponto"),
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
    if not re.search(r"\b(1[5-9]\d{2}|20\d{2})\b|\[\d{4}\??\]|\[VERIFICAR", referencia_texto):
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
