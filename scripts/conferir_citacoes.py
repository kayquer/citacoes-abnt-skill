"""Confere citações no texto contra a lista de referências (NBR 10520 e NBR 6023).

    py -3 scripts/conferir_citacoes.py trabalho.docx
    py -3 scripts/conferir_citacoes.py trabalho.md --edicao-10520 2002 --json

Lê o corpo e a seção REFERÊNCIAS e aponta:
  erro   citação sem referência correspondente
  erro   sobrenome em MAIÚSCULAS dentro dos parênteses (perfil 10520:2023; sigla é aceita)
  erro   "s.p." / "[s.p.]" na chamada
  erro   mesmo autor e ano com duas obras sem a/b
  erro   palavras-chave separadas por ponto (NBR 6028:2021)
  erro   problemas de forma na referência (URL entre < >, mês por extenso, s.d., Anais...)
  aviso  referência nunca citada no texto ("decorativa")
  aviso  citação direta (entre aspas) sem página
  aviso  ponto final duplicado: ." (Autor, ano).
  aviso  et al. e lista completa de autores misturados
  aviso  palavra-chave com inicial maiúscula (pode ser nome próprio)
  aviso  dia com zero à esquerda em "Acesso em"

Saída: 0 = sem erros; 1 = há erros (avisos não mudam o código).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abnt_lib as A  # noqa: E402
import documento as D  # noqa: E402

ANO = r"(?:1[5-9]\d{2}|20\d{2}|\[\d{3,4}[-?]*\]|\[ca\. \d{4}\])"
RE_PARENTESE = re.compile(r"\(([^()]*?" + ANO + r"[a-z]?[^()]*)\)")
NOME = r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]+"
RE_NARRATIVA = re.compile(
    r"(" + NOME + r"(?:(?:,\s*|\s+e\s+)" + NOME + r")*(?:\s+et al\.)?)\s+\((" + ANO + r")([a-z]?)((?:,\s*" + ANO + r"[a-z]?)*)([^()]*)\)")
PALAVRAS_FALSAS = {"Em", "No", "Na", "De", "Do", "Da", "Segundo", "Conforme", "Para", "Como", "Lei", "Figura", "Tabela",
                   "Quadro", "Gráfico", "Art", "Decreto", "Resolução", "Anexo", "Apêndice", "Seção", "Capítulo", "Entre"}


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", A.sem_acento(t or "").lower()).strip()


def _obras_parentese(conteudo):
    """'Silva; Souza, 2020, p. 3; Lima, 2019a' -> [(['Silva','Souza'], '2020', '', 'p. 3'), (['Lima'], '2019', 'a', '')]"""
    obras, nomes = [], []
    for parte in [p.strip() for p in conteudo.split(";")]:
        m = re.search(r",\s*(" + ANO + r")([a-z]?)((?:,\s*" + ANO + r"[a-z]?)*)(.*)$", parte)
        if m:
            nomes.append(parte[:m.start()].strip())
            extras = re.findall(ANO + r"[a-z]?", m.group(3) or "")
            obras.append((nomes, m.group(1), m.group(2), m.group(4).strip(" ,"), extras))
            nomes = []
        else:
            nomes.append(parte)
    return obras


def extrair_citacoes(corpo):
    citacoes = []
    for i, par in enumerate(corpo):
        texto = par.replace("**", "")
        for m in RE_PARENTESE.finditer(texto):
            conteudo = m.group(1)
            partes = re.split(r"\s+apud\s+", conteudo)
            for idx, trecho in enumerate(partes):
                apud_original = idx < len(partes) - 1  # obra original, não consultada: não exige referência
                for nomes, ano, suf, resto, extras in _obras_parentese(trecho):
                    if not nomes or not nomes[0] or len(nomes[0]) > 120:
                        continue
                    for ano_i in [ano] + extras:
                        citacoes.append({"paragrafo": i + 1, "texto": m.group(0), "nomes": nomes,
                                         "ano": re.sub(r"[a-z]$", "", ano_i), "sufixo": suf if ano_i == ano else ano_i[-1:] if ano_i[-1:].isalpha() else "",
                                         "localizador": resto, "parenteses": True, "apud_original": apud_original,
                                         "pos": m.start(), "trecho_paragrafo": texto})
        for m in RE_NARRATIVA.finditer(texto):
            nomes_txt = m.group(1)
            if nomes_txt.split()[0] in PALAVRAS_FALSAS:
                continue
            nomes = [n.strip() for n in re.split(r",\s*|\s+e\s+", nomes_txt.replace(" et al.", "")) if n.strip()]
            citacoes.append({"paragrafo": i + 1, "texto": m.group(0), "nomes": nomes, "ano": m.group(2), "sufixo": m.group(3),
                             "localizador": m.group(5).strip(" ,"), "parenteses": False, "apud_original": " apud" in m.group(5),
                             "pos": m.start(), "trecho_paragrafo": texto, "et_al": "et al." in nomes_txt})
    return citacoes


def indexar_referencias(refs_texto):
    indice = []
    for t in refs_texto:
        r = A.ler_referencia_texto(t)
        nomes = set()
        for a in r.get("autores", []):
            for w in norm(a.get("sobrenome") or a.get("entidade")).split():
                nomes.add(w)
        cabeca = norm(t.replace("**", "")[:160])
        indice.append({"texto": t, "ano": r.get("ano"), "sufixo": r.get("sufixo_ano", ""), "nomes": nomes,
                       "cabeca": cabeca, "primeira": cabeca.split(" ")[0] if cabeca else "", "citada": False, "ref": r})
    return indice


def _casa(citacao, ref):
    if citacao["ano"].strip("[]?") [:4] != (ref["ano"] or "")[:4] and citacao["ano"] not in ref["texto"]:
        return False
    primeiro = norm(citacao["nomes"][0].replace("[...]", "").replace("et al.", ""))
    if not primeiro:
        return False
    palavras = primeiro.split()
    if ref["nomes"] and palavras[-1] in ref["nomes"]:
        return True
    if A.eh_sigla(citacao["nomes"][0].strip()) and re.search(r"\b" + primeiro + r"\b", ref["cabeca"]):
        return True  # (IBGE, 2023) -> INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE)
    return primeiro in ref["cabeca"][:len(primeiro) + 40] or palavras[0] == ref["primeira"]


def conferir(corpo, refs_texto, edicao_10520="2023"):
    achados = []
    indice = indexar_referencias(refs_texto)
    sobrenomes_pessoais = {w.upper() for r in indice for a in r["ref"].get("autores", []) if "sobrenome" in a
                           for w in [A.sem_acento(a["sobrenome"])]}
    citacoes = extrair_citacoes(corpo)

    def add(nivel, tipo, msg, onde=None):
        achados.append({"nivel": nivel, "tipo": tipo, "mensagem": msg, **({"onde": onde} if onde else {})})

    vistos_formato = set()
    for c in citacoes:
        onde = f"parágrafo {c['paragrafo']}: {c['texto']}"
        alvo = [r for r in indice if _casa(c, r)]
        if c["sufixo"]:
            alvo = [r for r in alvo if r["sufixo"] == c["sufixo"]] or alvo
        if alvo:
            for r in alvo:
                r["citada"] = True
        elif not c["apud_original"]:
            add("erro", "citacao_sem_referencia", f"{' ; '.join(c['nomes'])}, {c['ano']}{c['sufixo']} não tem referência na lista", onde)
        # Caixa alta dentro dos parênteses
        if c["parenteses"] and edicao_10520 == "2023" and c["texto"] not in vistos_formato:
            for n in c["nomes"]:
                n_limpo = n.replace("et al.", "").strip()
                if re.fullmatch(r"[A-ZÀ-Ý][A-ZÀ-Ý'\- ]{2,}", n_limpo) and \
                        (not A.eh_sigla(n_limpo) or A.sem_acento(n_limpo) in sobrenomes_pessoais):
                    add("erro", "caixa_alta_na_chamada",
                        f"NBR 10520:2023 pede maiúsculas e minúsculas: use ({n_limpo.title()}, {c['ano']}) em vez de "
                        f"({n_limpo}, {c['ano']}). Sigla (IBGE, UFMG) continua em maiúsculas.", onde)
                    break
        if re.search(r"\[?\bs\.\s?p\.\]?|\bs/p\b", c["localizador"]):
            add("erro", "sp_na_chamada", "'s.p.' não existe na NBR 10520:2023: sem paginação, omita o localizador", onde)
        vistos_formato.add(c["texto"])

    # Citação direta sem página e ponto duplicado
    for i, par in enumerate(corpo):
        texto = par.replace("**", "")
        for m in re.finditer(r"[\"“]([^\"”]{15,})[\"”]\s*\(([^()]*?" + ANO + r"[a-z]?)([^()]*)\)", texto):
            if not re.search(r"\b(p|f|local|cap|art)\.\s*\w", m.group(3)):
                add("aviso", "direta_sem_pagina", "citação direta sem localizador (p. N), obrigatório quando o documento é paginado",
                    f"parágrafo {i + 1}: …{m.group(0)[-80:]}")
        for m in re.finditer(r"\.[\"”]\s*\([^()]*" + ANO + r"[^()]*\)\.", texto):
            add("aviso", "ponto_duplicado", "ponto antes das aspas e depois da chamada: deixe só o ponto final depois da chamada",
                f"parágrafo {i + 1}: {m.group(0)}")
        m = re.match(r"^\s*(Palavras-chave|Palavras chave)\s*:\s*(.+)$", texto, re.I)
        if m:
            termos = m.group(2).strip().rstrip(".")
            if "." in termos and ";" not in termos:
                add("erro", "palavras_chave", "NBR 6028:2021: separe as palavras-chave por ponto e vírgula", f"parágrafo {i + 1}")
            for termo in [t.strip() for t in termos.split(";")][1:]:
                primeira = termo.split()[0] if termo else ""
                if re.fullmatch(r"[A-ZÀ-Ý][a-zà-ÿ\-]+", primeira):
                    add("aviso", "palavras_chave", f"NBR 6028:2021: palavras-chave com inicial minúscula, exceto nome "
                        f"próprio e sigla ('{termo}')", f"parágrafo {i + 1}")
                    break

    # et al. misturado com lista completa
    com_etal = any(c.get("et_al") or any("et al." in n for n in c["nomes"]) for c in citacoes)
    com_4mais = any(len(c["nomes"]) >= 4 for c in citacoes)
    if com_etal and com_4mais:
        add("aviso", "et_al_misturado", "o documento usa et al. e também lista quatro ou mais autores: escolha uma forma")

    # Referências
    for r in indice:
        for p in A.problemas_texto(r["texto"]):
            add("aviso" if "zero à esquerda" in p else "erro", "forma_referencia", p, r["texto"][:120])
        if not r["citada"]:
            add("aviso", "referencia_nao_citada", "referência não citada no texto (decorativa): cite ou retire", r["texto"][:120])
    grupos = {}
    for r in indice:
        primeiro = sorted(r["nomes"])[0] if r["nomes"] else r["primeira"]
        chave = (r["cabeca"].split(" ")[0], (r["ano"] or "")[:4])
        grupos.setdefault(chave, []).append(r)
    for (autor, ano), rs in grupos.items():
        if len(rs) > 1 and ano and len({r["sufixo"] for r in rs}) < len(rs):
            add("erro", "mesmo_autor_ano", f"{len(rs)} obras de {autor.upper()} em {ano}: diferencie com {ano}a, {ano}b na "
                "referência e na chamada", rs[0]["texto"][:80])
    return {"citacoes": len(citacoes), "referencias": len(indice), "achados": achados}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--edicao-10520", default=A.EDICAO_10520_PADRAO, choices=A.EDICOES_10520)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    corpo, refs = D.ler(args.arquivo)
    if not refs:
        print("Aviso: seção REFERÊNCIAS não encontrada; só o corpo será conferido.", file=sys.stderr)
    res = conferir(corpo, refs, args.edicao_10520)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"{res['citacoes']} citações, {res['referencias']} referências")
        for a in sorted(res["achados"], key=lambda x: x["nivel"] != "erro"):
            print(f"[{a['nivel'].upper()}] {a['mensagem']}")
            if a.get("onde"):
                print(f"    {a['onde']}")
        erros = sum(1 for a in res["achados"] if a["nivel"] == "erro")
        print(f"\n{erros} erro(s), {len(res['achados']) - erros} aviso(s)")
    return 1 if any(a["nivel"] == "erro" for a in res["achados"]) else 0


if __name__ == "__main__":
    for _fluxo in (sys.stdout, sys.stderr):  # acentos certos no console do Windows
        _fluxo.reconfigure(encoding="utf-8")
    sys.exit(main())
