"""Testes da biblioteca, do conferidor e do checador (sem rede: as bases são simuladas)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import biblioteca as B  # noqa: E402
import checar_referencias as C  # noqa: E402
import conferir_citacoes as F  # noqa: E402
import documento as D  # noqa: E402
import gerar_modelo_docx as G  # noqa: E402

FIX = RAIZ / "tests" / "fixtures"
FREIRE = {"tipo": "livro", "autores": [{"sobrenome": "Freire", "nome": "Paulo"}], "titulo": "Pedagogia do oprimido",
          "local": "Rio de Janeiro", "editora": "Paz e Terra", "ano": 1987, "edicao": "17"}


class TestBiblioteca(unittest.TestCase):
    def test_id_e_duplicata(self):
        dados = {"referencias": []}
        ref, dup = B.adicionar(dados, dict(FREIRE))
        self.assertEqual(ref["id"], "freire1987pedagogia")
        self.assertIsNone(dup)
        _, dup = B.adicionar(dados, dict(FREIRE, titulo="Pedagogia do Oprimido"))
        self.assertIsNotNone(dup)
        self.assertEqual(len(dados["referencias"]), 1)

    def test_revisar_quando_falta(self):
        dados = {"referencias": []}
        ref, _ = B.adicionar(dados, {"tipo": "livro", "titulo": "Sem ano"})
        self.assertIn("ano", ref["revisar"])

    def test_bib_ida_e_volta(self):
        ref = dict(FREIRE, id="freire1987")
        de_volta = B.ler_bib(B.para_bib(ref))[0]
        for campo in ("titulo", "ano", "editora", "local"):
            self.assertEqual(str(de_volta[campo]), str(ref[campo]))
        self.assertEqual(de_volta["autores"][0]["sobrenome"], "Freire")

    def test_ris_ida_e_volta(self):
        ref = {"id": "x", "tipo": "artigo", "autores": [{"sobrenome": "Silva", "nome": "Ana"}], "titulo": "T",
               "periodico": "P", "ano": "2020", "paginas": "10-20", "doi": "10.1/x"}
        de_volta = B.ler_ris(B.para_ris(ref))[0]
        self.assertEqual(de_volta["paginas"], "10-20")
        self.assertEqual(de_volta["periodico"], "P")
        self.assertEqual(de_volta["doi"], "10.1/x")

    def test_cli_exportar_abnt(self):
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, "b.json")
            B.salvar(arq, {"versao": 1, "referencias": [dict(FREIRE, id="freire1987pedagogia")]})
            saida = os.path.join(d, "refs.txt")
            self.assertEqual(B.main(["--arquivo", arq, "exportar", "--formato", "abnt", "--saida", saida]), 0)
            self.assertIn("FREIRE, Paulo. Pedagogia do oprimido. 17. ed.", Path(saida).read_text(encoding="utf-8"))

    def test_importar_csl_e_recusar_tipo_invalido(self):
        with tempfile.TemporaryDirectory() as d:
            arq, origem = os.path.join(d, "b.json"), os.path.join(d, "zotero.json")
            csl = [B.para_csl(dict(FREIRE, id="f")),
                   {"id": "x", "type": "article-journal", "title": "Leitura", "container-title": "Revista",
                    "author": [{"family": "Silva", "given": "Ana"}], "issued": {"date-parts": [[2020]]}},
                   {"id": "ruim", "tipo": "podcast", "titulo": "Sem tipo válido"}]
            Path(origem).write_text(json.dumps(csl), encoding="utf-8")
            self.assertEqual(B.main(["--arquivo", arq, "importar", origem]), 1)  # 1 por causa do recusado
            refs = B.carregar(arq)["referencias"]
            self.assertEqual(len(refs), 2)
            artigo = next(r for r in refs if r["tipo"] == "artigo")
            self.assertEqual(artigo["periodico"], "Revista")
            self.assertEqual(B.main(["--arquivo", arq, "exportar", "--formato", "abnt", "--saida", os.path.join(d, "o.md")]), 0)

    def test_traducao_ida_e_volta(self):
        ref = dict(FREIRE, id="kant", tradutor="Fernando Costa Mattos", titulo_original="Kritik der reinen Vernunft",
                   ano_original="1781")
        for de_volta in (B.ler_bib(B.para_bib(ref))[0], B.ler_csl(B.para_csl(ref))):
            self.assertIn("Fernando Costa Mattos", str(de_volta["tradutor"]))
            self.assertEqual(de_volta["titulo_original"], "Kritik der reinen Vernunft")
            self.assertEqual(str(de_volta["ano_original"]), "1781")

    def test_csl(self):
        item = B.para_csl(dict(FREIRE, id="f"))
        self.assertEqual(item["type"], "book")
        self.assertEqual(item["issued"], {"date-parts": [[1987]]})


class TestConferidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        corpo, refs = D.ler(FIX / "trabalho-com-erros.md")
        cls.res = F.conferir(corpo, refs)
        cls.tipos = [a["tipo"] for a in cls.res["achados"]]

    def test_caixa_alta(self):
        self.assertIn("caixa_alta_na_chamada", self.tipos)

    def test_sigla_aceita_e_casada(self):
        caixa = [a.get("onde", "") for a in self.res["achados"] if a["tipo"] == "caixa_alta_na_chamada"]
        self.assertFalse(any("(IBGE" in o for o in caixa))
        sem_ref = [a["mensagem"] for a in self.res["achados"] if a["tipo"] == "citacao_sem_referencia"]
        self.assertFalse(any(m.startswith("IBGE") for m in sem_ref))

    def test_sem_referencia(self):
        sem = [a for a in self.res["achados"] if a["tipo"] == "citacao_sem_referencia"]
        self.assertEqual(len(sem), 1)
        self.assertIn("Souza", sem[0]["mensagem"])

    def test_apud_original_nao_exige_referencia(self):
        self.assertFalse(any("Vianna" in a["mensagem"] for a in self.res["achados"]))

    def test_decorativa(self):
        nao = [a["onde"] for a in self.res["achados"] if a["tipo"] == "referencia_nao_citada"]
        self.assertEqual(len(nao), 1)
        self.assertIn("TAVARES", nao[0])

    def test_demais(self):
        for t in ("sp_na_chamada", "mesmo_autor_ano", "palavras_chave", "forma_referencia", "ponto_duplicado",
                  "direta_sem_pagina", "et_al_misturado"):
            self.assertIn(t, self.tipos, t)

    def test_perfil_2002_aceita_caixa_alta(self):
        corpo, refs = D.ler(FIX / "trabalho-com-erros.md")
        tipos = [a["tipo"] for a in F.conferir(corpo, refs, "2002")["achados"]]
        self.assertNotIn("caixa_alta_na_chamada", tipos)

    def test_texto_correto_sem_erros(self):
        corpo = ["Segundo Freire (1987, p. 45), a educação é diálogo (Freire, 1987, p. 46)."]
        refs = ["FREIRE, Paulo. **Pedagogia do oprimido**. 17. ed. Rio de Janeiro: Paz e Terra, 1987."]
        self.assertEqual(F.conferir(corpo, refs)["achados"], [])


def _base(achados):
    """Simula metadados.*_buscar devolvendo os candidatos dados para cada base."""
    return lambda *a, **k: achados


class TestChecador(unittest.TestCase):
    REAL = {"titulo": "Deep learning", "autores": [{"sobrenome": "LeCun", "nome": "Yann"}], "ano": "2015"}
    CAND = {"titulo": "Deep learning", "autores": [{"sobrenome": "LeCun", "nome": "Yann"}], "ano": 2015}
    OUTRO = {"titulo": "Deep learning", "autores": [{"sobrenome": "Souza", "nome": "Ana"}], "ano": "2015"}

    def _rodar(self, ref, por_base, doi=None):
        with mock.patch.object(C.M, "crossref_buscar", _base(por_base.get("crossref", []))), \
             mock.patch.object(C.M, "openalex_buscar", _base(por_base.get("openalex", []))), \
             mock.patch.object(C.M, "semantic_buscar", _base(por_base.get("semantic", []))), \
             mock.patch.object(C.M, "openlibrary_buscar", _base([])), \
             mock.patch.object(C.M, "googlebooks_buscar", _base([])), \
             mock.patch.object(C.M, "crossref_doi", lambda d: doi):
            return C.checar(ref, ["crossref", "openalex", "semantic"])

    def test_verificada_exige_duas_bases(self):
        self.assertEqual(self._rodar(self.REAL, {"crossref": [self.CAND], "openalex": [self.CAND]})["status"], "verificada")
        self.assertEqual(self._rodar(self.REAL, {"crossref": [self.CAND]})["status"], "parcial")

    def test_autoria_nao_comparada(self):
        sem_autor = {"titulo": "Deep learning", "ano": "2015"}
        r = self._rodar(sem_autor, {"crossref": [self.CAND], "openalex": [self.CAND]})
        self.assertEqual(r["status"], "verificada")
        self.assertTrue(r.get("autoria_nao_comparada"))

    def test_inventada(self):
        ref = {"titulo": "Redes neurais quânticas na safra de café", "autores": [{"sobrenome": "Mendonça"}], "ano": "2021"}
        self.assertEqual(self._rodar(ref, {"crossref": [self.CAND]})["status"], "nao_encontrada")

    def test_quimera(self):
        self.assertEqual(self._rodar(self.OUTRO, {"crossref": [self.CAND], "openalex": [self.CAND]})["status"], "quimera")

    def test_doi_de_outra_obra(self):
        ref = dict(self.REAL, titulo="Educação ambiental e cidadania", doi="10.1038/nature14539")
        r = self._rodar(ref, {}, doi=self.CAND)
        self.assertEqual(r["status"], "doi_divergente")

    def test_doi_inexistente(self):
        r = self._rodar(dict(self.REAL, doi="10.9999/nao.existe"), {"crossref": [self.CAND], "openalex": [self.CAND]})
        self.assertEqual(r["status"], "doi_divergente")

    def test_erro_de_rede_nao_vira_nao_encontrada(self):
        def falha(*a, **k):
            raise C.M.ErroRede("x: HTTP 429")
        with mock.patch.object(C.M, "crossref_buscar", falha), mock.patch.object(C.M, "openalex_buscar", falha), \
             mock.patch.object(C.M, "semantic_buscar", falha):
            self.assertEqual(C.checar(self.REAL, ["crossref", "openalex", "semantic"])["status"], "erro_rede")

    def test_similaridade(self):
        self.assertGreater(C.similaridade("Pedagogia do oprimido", "Pedagogia do Oprimido"), 0.95)
        self.assertLess(C.similaridade("Pedagogia do oprimido", "Pedagogia da autonomia"), 0.85)
        # A base guarda só o título principal (Crossref: "Get the message")
        self.assertGreaterEqual(C.similaridade("Get the message: the influence of message framing", "Get the Message"),
                                C.LIMIAR_TITULO)

    def test_homonimo_nao_vira_quimera(self):
        livro = {"tipo": "livro", "titulo": "Nietzsche e a filosofia", "ano": "2018",
                 "autores": [{"sobrenome": "Deleuze", "nome": "Gilles"}]}
        artigo = {"tipo": "artigo", "titulo": "Nietzsche e a filosofia", "ano": 2011,
                  "autores": [{"sobrenome": "Marton", "nome": "Scarlett"}]}
        r = self._rodar(livro, {"crossref": [artigo], "openalex": [artigo], "semantic": [artigo]})
        self.assertEqual(r["status"], "homonimo")
        # Mesmo título, outro autor, mesmo ano e tipo: continua quimera
        self.assertEqual(self._rodar(self.OUTRO, {"crossref": [self.CAND], "openalex": [self.CAND]})["status"], "quimera")

    def test_sobrenome_comum_em_lista_longa_nao_confirma(self):
        cand = dict(self.CAND, autores=[{"sobrenome": f"Autor{i}"} for i in range(19)] + [{"sobrenome": "Wang"}])
        ref = dict(self.REAL, autores=[{"sobrenome": "Silva"}, {"sobrenome": "Wang"}])
        self.assertFalse(C.autores_batem(ref, cand))
        self.assertTrue(C.autores_batem(dict(ref, autores=[{"sobrenome": "Wang"}]), cand))

    def test_sugestao_de_doi_conferida(self):
        pre = dict(self.CAND, doi="10.2139/ssrn.123", periodico="SSRN")
        r = self._rodar(dict(self.REAL, periodico="Nature", tipo="artigo"), {"crossref": [pre], "openalex": [self.CAND]})
        self.assertNotIn("sugestao_doi", r)
        self.assertTrue(any("SSRN" in a for a in r["alertas"]))
        reedicao = dict(self.CAND, doi="10.1017/9781316", ano=2015)
        r = self._rodar(dict(self.REAL, ano="1977"), {"crossref": [reedicao]})
        self.assertNotIn("sugestao_doi", r)
        ok = dict(self.CAND, doi="10.1038/nature14539")
        self.assertEqual(self._rodar(self.REAL, {"crossref": [ok]})["sugestao_doi"], "10.1038/nature14539")

    def test_noticia_confere_o_link(self):
        nota = {"tipo": "jornal", "titulo": "Facebook whistleblower testifies", "periodico": "The Washington Post",
                "data": "2021-10-26", "url": "https://www.washingtonpost.com/x"}
        with mock.patch.object(C.M, "conferir_url", lambda u: {"responde": True,
                                                              "titulo": "Facebook whistleblower testifies - The Washington Post"}):
            r = self._rodar(nota, {"crossref": [self.CAND]})
        self.assertEqual(r["status"], "url_verificada")
        self.assertEqual(r["bases"].get("crossref"), None)  # nem consultou as bases acadêmicas
        with mock.patch.object(C.M, "conferir_url", mock.Mock(side_effect=C.M.ErroRede("web: HTTP 403"))):
            self.assertEqual(self._rodar(nota, {})["status"], "url_inacessivel")
        self.assertEqual(self._rodar(dict(nota, url=None), {})["status"], "nao_verificavel")

    def test_titulo_atribuido_e_obra_historica(self):
        swift = {"titulo": "[Sobre a mentira política]", "ano": "1710", "autores": [{"sobrenome": "Swift"}]}
        self.assertEqual(self._rodar(swift, {})["status"], "nao_verificavel")
        hobbes = {"tipo": "livro", "titulo": "Leviathan or the matter forme and power of a commonwealth",
                  "ano": "1651", "autores": [{"sobrenome": "Hobbes"}]}
        self.assertEqual(self._rodar(hobbes, {})["status"], "fora_de_cobertura")

    def test_jsonl_e_retomar(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs = Path(tmp) / "refs.json"
            refs.write_text(json.dumps([dict(self.REAL, id="a", tipo="artigo"), dict(self.OUTRO, id="b", tipo="artigo")]),
                            encoding="utf-8")
            saida = Path(tmp) / "c.jsonl"
            chamadas = []

            def busca(*a, **k):
                chamadas.append(a[0])
                return [self.CAND]
            with mock.patch.object(C.M, "crossref_buscar", busca), mock.patch.object(C.M, "openalex_buscar", busca), \
                    mock.patch("sys.stdout", new=__import__("io").StringIO()), \
                    mock.patch("sys.stderr", new=__import__("io").StringIO()) as err:
                codigo = C.main([str(refs), "--bases", "crossref,openalex", "--saida", str(saida), "--json"])
                self.assertIn("[2/2] quimera", err.getvalue())
                self.assertEqual(codigo, 1)
                linhas = saida.read_text(encoding="utf-8").splitlines()
                self.assertEqual([json.loads(x)["chave"] for x in linhas], ["a", "b"])
                antes = len(chamadas)
                C.main([str(refs), "--bases", "crossref,openalex", "--saida", str(saida), "--retomar", "--json"])
                self.assertEqual(len(chamadas), antes)  # nada refeito


class TestCache(unittest.TestCase):
    def test_cache_em_disco(self):
        import metadados as M
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"CITACOES_ABNT_CACHE": tmp}), \
                mock.patch.object(M, "CACHE_ATIVO", True):
            get = mock.Mock(return_value=(b'{"ok": 1}', "application/json"))
            with mock.patch.object(M, "_get", get):
                self.assertEqual(M._json("https://api.crossref.org/works/x", "crossref"), {"ok": 1})
                self.assertEqual(M._json("https://api.crossref.org/works/x", "crossref"), {"ok": 1})
            self.assertEqual(get.call_count, 1)
            falha = mock.Mock(side_effect=M.ErroRede("crossref: HTTP 429"))
            with mock.patch.object(M, "_get", falha), self.assertRaises(M.ErroRede):
                M._json("https://api.crossref.org/works/y", "crossref")  # erro não entra no cache
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 1)


class TestNotasNoDocumento(unittest.TestCase):
    def test_markdown_com_notas(self):
        corpo, refs = D.ler(FIX / "livro-com-notas.md")
        self.assertEqual(len(refs), 4)  # as definições [^n]: não viram referência
        notas = D.notas(FIX / "livro-com-notas.md")
        self.assertEqual([n["rotulo"] for n in notas], ["1", "2", "3", "4", "5"])
        achados = F.conferir(corpo, refs, notas=notas)["achados"]
        por_tipo = {}
        for a in achados:
            por_tipo.setdefault(a["tipo"], []).append(a)
        self.assertEqual([a["onde"][:6] for a in por_tipo["nota_abreviada_antes_da_completa"]], ["nota 3"])
        self.assertIn("DELEUZE", por_tipo["nota_sem_referencia"][0]["mensagem"])
        decorativas = por_tipo["referencia_nao_citada"]
        self.assertEqual(len(decorativas), 1)  # só O mal-estar; Freud, Hobbes e Swift estão citados em nota
        self.assertIn("mal-estar", decorativas[0]["onde"])
        self.assertNotIn("forma_referencia", por_tipo)  # 2010a/2010b é ano válido

    def test_notas_do_docx(self):
        import zipfile
        w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        doc = (f'<w:document {w}><w:body><w:p><w:r><w:t>Texto.</w:t></w:r>'
               '<w:r><w:footnoteReference w:id="2"/></w:r></w:p></w:body></w:document>')
        notas = (f'<w:footnotes {w}><w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:t>--</w:t></w:r></w:p>'
                 '</w:footnote><w:footnote w:id="2"><w:p><w:r><w:t>FREUD, Sigmund. </w:t></w:r>'
                 '<w:r><w:t>Luto e melancolia.</w:t></w:r></w:p></w:footnote></w:footnotes>')
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "n.docx"
            with zipfile.ZipFile(arq, "w") as z:
                z.writestr("word/document.xml", doc)
                z.writestr("word/footnotes.xml", notas)
            self.assertEqual(D.notas(arq), [{"rotulo": "f2", "texto": "FREUD, Sigmund. Luto e melancolia."}])


class TestBibliotecaHumanidades(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.arq = str(Path(self.tmp.name) / "biblioteca.json")
        B.main(["--arquivo", self.arq, "importar", str(FIX / "biblioteca-humanidades.json")])

    def tearDown(self):
        self.tmp.cleanup()

    def _saida(self, argv):
        import io
        with mock.patch("sys.stdout", new=io.StringIO()) as out:
            B.main(["--arquivo", self.arq] + argv)
        return out.getvalue()

    def test_exportar_leva_sufixo_da_chamada(self):
        lista = self._saida(["exportar"])
        self.assertIn("Companhia das Letras, 2010a. v. 12, p. 170-194.", lista)
        self.assertIn("Companhia das Letras, 2010b.", lista)
        self.assertIn("(Freud, 2010a, p. 172)", self._saida(["citar", "freud2010luto", "--pagina", "172"]))

    def test_notas_em_sequencia(self):
        r = json.loads(self._saida(["notas", "freud2010luto:172, freud2010luto:180, hobbes2003leviata:cap. XIII"]))
        self.assertEqual([n["forma"] for n in r["notas"]], ["completa", "curta", "completa"])
        self.assertEqual(r["notas"][1]["nota"], "FREUD, 2010a, p. 180.")
        r = json.loads(self._saida(["nota", "freud2010luto", "--forma", "ibid", "--pagina", "9"]))
        self.assertEqual(r["nota"], "*Ibid.*, p. 9.")
        self.assertIn("aviso", r)

    def test_ida_e_volta_dos_campos_novos(self):
        dados = B.carregar(self.arq)
        for r in dados["referencias"]:
            for nome, ida, volta, campos in (("bib", B.para_bib, lambda t: B.ler_bib(t)[0],
                                              ("tipo", "data", "eloc", "caderno", "prefacio")),
                                             ("csl", B.para_csl, B.ler_csl, ("tipo", "data", "caderno"))):
                de_volta = volta(ida(r))
                for campo in campos:
                    if r.get(campo):
                        self.assertEqual(str(de_volta.get(campo)), str(r[campo]), f"{nome}: {r['id']}.{campo}")
            if r["tipo"] == "jornal":
                ris = B.ler_ris(B.para_ris(r))[0]
                self.assertEqual((ris["tipo"], ris["data"]), ("jornal", r["data"]))
        com_prefacio = dict(dados["referencias"][2], prefacio="Ana Lima")
        self.assertEqual(B.ler_bib(B.para_bib(com_prefacio))[0]["prefacio"], "Ana Lima")


class TestModeloDocx(unittest.TestCase):
    def test_gera_docx_valido(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            saida = os.path.join(d, "m.docx")
            G.gerar(G.perfil("ufpel"), saida, "tcc")
            with zipfile.ZipFile(saida) as z:
                doc = z.read("word/document.xml").decode("utf-8")
                estilos = z.read("word/styles.xml").decode("utf-8")
            self.assertIn('w:left="1701"', doc)  # 3 cm
            self.assertIn("Arial", estilos)
            self.assertIn("PAGE", z_header(saida))
            corpo, _ = D.ler(saida)
            self.assertTrue(any("INTRODUÇÃO" in p for p in corpo))


def z_header(caminho):
    import zipfile
    with zipfile.ZipFile(caminho) as z:
        return z.read("word/header1.xml").decode("utf-8")


class TestDados(unittest.TestCase):
    def test_instituicoes(self):
        dados = json.loads((RAIZ / "data" / "instituicoes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(dados), 50)
        for i in dados:
            self.assertRegex(i["id"], r"^[a-z0-9-]+$")
            self.assertIn("perfil", i)
            for campo in ("margens_cm", "fonte_familia", "espacamento", "edicao_6023", "edicao_10520"):
                self.assertIn(campo, i["perfil"], i["id"])


class TestPacotesPortateis(unittest.TestCase):
    """dist/ fora do Claude Code: skills autocontidas e pacote de chat."""

    def test_instrucoes_cabem_no_gpt(self):
        texto = (RAIZ / "dist" / "chat" / "instrucoes.txt").read_text(encoding="utf-8")
        self.assertLessEqual(len(texto), 8000)
        self.assertIn("não verificada", texto)

    def test_skill_autocontida(self):
        import zipfile
        for nome in ("biblioteca-citacoes", "checador-citacoes", "abnt-formatacao"):
            with zipfile.ZipFile(RAIZ / "dist" / "claude-ai" / f"{nome}.zip") as z:
                nomes = set(z.namelist())
                skill = z.read(f"{nome}/SKILL.md").decode("utf-8")
            for obrigatorio in ("SKILL.md", "scripts/checar_referencias.py", "data/instituicoes.json",
                                "references/instituicoes/usp.md", "references/normas/vigencia.md", "LICENSE"):
                self.assertIn(f"{nome}/{obrigatorio}", nomes)
            self.assertNotIn("../", skill)
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", skill)

    def test_extensao_gemini(self):
        manifesto = json.loads((RAIZ / "gemini-extension.json").read_text(encoding="utf-8"))
        self.assertEqual(manifesto["name"], "citacoes-abnt-skill")  # igual ao nome da pasta clonada


if __name__ == "__main__":
    unittest.main()
