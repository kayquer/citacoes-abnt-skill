"""Converte os CSVs de instituições em data/instituicoes-base.json.

Uso: py -3 tools/importar_csv.py <universidades_brasil.csv> <universidades_tecnicas_brasil.csv>

O CSV de universidades tem uma coluna duplicada com erro de digitação
("Recursos para Production Científica"); quando preenchida, ela é somada ao
campo de fomento.
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def sigla_de(nome):
    m = re.search(r"\(([^)]+)\)\s*$", nome)
    if m:
        return m.group(1)
    return nome.replace("Universidade ", "")


def lista(texto):
    return [p.strip() for p in (texto or "").split(",") if p.strip()]


def main(csv_uni, csv_tec):
    saida = []
    with open(csv_uni, encoding="utf-8-sig", newline="") as f:
        for linha in csv.reader(f):
            if linha[0] == "Universidade":
                continue
            nome, tipo, categoria, fomento, norma = linha[:5]
            extra = linha[5] if len(linha) > 5 else ""
            sigla = sigla_de(nome)
            saida.append({
                "id": slug(sigla),
                "sigla": sigla,
                "nome": nome,
                "grupo": "universidade",
                "tipo": tipo,
                "categoria": categoria,
                "uf": None,
                "fomento": lista(fomento) + lista(extra),
                "norma_csv": norma,
            })
    with open(csv_tec, encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f):
            sigla = linha["Sigla"]
            saida.append({
                "id": slug(sigla),
                "sigla": sigla,
                "nome": linha["Instituição"],
                "grupo": "tecnica",
                "tipo": linha["Tipo"],
                "categoria": None,
                "uf": linha["Estado"],
                "fomento": lista(linha["Recursos / Fomento para Produção Científica"]),
                "norma_csv": linha["Norma de Formatação Predominante"],
            })
    ids = [i["id"] for i in saida]
    assert len(ids) == len(set(ids)), "ids duplicados"
    destino = RAIZ / "data" / "instituicoes-base.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(saida)} instituições -> {destino}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
