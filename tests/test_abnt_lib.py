import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import abnt_lib as A  # noqa: E402

SILVA = {"sobrenome": "Silva", "nome": "João Carlos"}
SOUZA = {"sobrenome": "Souza", "nome": "Maria"}
COSTA = {"sobrenome": "Costa", "nome": "Ana"}
LIMA = {"sobrenome": "Lima", "nome": "Pedro"}


class TestNomes(unittest.TestCase):
    def test_separar_simples(self):
        self.assertEqual(A.separar_nome("João Carlos Silva"), {"sobrenome": "Silva", "nome": "João Carlos"})

    def test_separar_agnome(self):
        self.assertEqual(A.separar_nome("José da Silva Neto")["sobrenome"], "Silva Neto")

    def test_separar_com_virgula(self):
        self.assertEqual(A.separar_nome("Freire, Paulo"), {"sobrenome": "Freire", "nome": "Paulo"})

    def test_autor_abreviado(self):
        self.assertEqual(A.formatar_autor({"sobrenome": "Silva", "nome": "João Carlos da"}, abreviar=True), "SILVA, J. C.")

    def test_et_al(self):
        self.assertEqual(A.formatar_autores([SILVA, SOUZA, COSTA, LIMA], max_autores=3), "SILVA, João Carlos et al.")
        self.assertIn("LIMA, Pedro", A.formatar_autores([SILVA, SOUZA, COSTA, LIMA]))


class TestReferencias(unittest.TestCase):
    def test_livro(self):
        ref = {"tipo": "livro", "autores": [{"sobrenome": "Freire", "nome": "Paulo"}], "titulo": "Pedagogia do oprimido",
               "edicao": "17", "local": "Rio de Janeiro", "editora": "Paz e Terra", "ano": 1987}
        self.assertEqual(A.formatar_referencia(ref),
                         "FREIRE, Paulo. **Pedagogia do oprimido**. 17. ed. Rio de Janeiro: Paz e Terra, 1987.")

    def test_livro_subtitulo_sem_local(self):
        ref = {"tipo": "livro", "autores": [SILVA], "titulo": "Método", "subtitulo": "um guia", "ano": 2020}
        self.assertEqual(A.formatar_referencia(ref, estilo="texto"),
                         "SILVA, João Carlos. Método: um guia. [S. l.]: [s. n.], 2020.")

    def test_artigo_doi(self):
        ref = {"tipo": "artigo", "autores": [SILVA, SOUZA], "titulo": "Leitura e escrita", "periodico": "Educação em Revista",
               "local": "Belo Horizonte", "volume": 36, "numero": 2, "paginas": "15–30", "mes": 3, "ano": 2020,
               "doi": "doi:10.1590/0102-4698214500"}
        self.assertEqual(A.formatar_referencia(ref),
                         "SILVA, João Carlos; SOUZA, Maria. Leitura e escrita. **Educação em Revista**, Belo Horizonte, "
                         "v. 36, n. 2, p. 15-30, mar. 2020. DOI: https://doi.org/10.1590/0102-4698214500.")

    def test_capitulo(self):
        ref = {"tipo": "capitulo", "autores": [SILVA], "titulo": "O texto", "organizadores": [SOUZA],
               "titulo_obra": "Escrita acadêmica", "local": "São Paulo", "editora": "Contexto", "ano": 2019, "paginas": "10-25"}
        self.assertEqual(A.formatar_referencia(ref),
                         "SILVA, João Carlos. O texto. In: SOUZA, Maria (org.). **Escrita acadêmica**. "
                         "São Paulo: Contexto, 2019. p. 10-25.")

    def test_tese(self):
        ref = {"tipo": "tese", "autores": [SILVA], "titulo": "Leitura na escola", "ano": 2021, "folhas": 210,
               "tipo_trabalho": "Tese", "grau": "Doutorado em Educação", "unidade": "Faculdade de Educação",
               "instituicao": "Universidade de São Paulo", "local": "São Paulo"}
        self.assertEqual(A.formatar_referencia(ref),
                         "SILVA, João Carlos. **Leitura na escola**. 2021. 210 f. Tese (Doutorado em Educação) – "
                         "Faculdade de Educação, Universidade de São Paulo, São Paulo, 2021.")

    def test_site_entidade(self):
        ref = {"tipo": "site", "autores": [{"entidade": "Instituto Brasileiro de Geografia e Estatística"}],
               "titulo": "Censo 2022", "local": "Rio de Janeiro", "ano": 2023, "url": "https://censo2022.ibge.gov.br",
               "acesso": "2024-01-10"}
        self.assertEqual(A.formatar_referencia(ref),
                         "INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. **Censo 2022**. Rio de Janeiro, 2023. "
                         "Disponível em: https://censo2022.ibge.gov.br. Acesso em: 10 jan. 2024.")

    def test_sem_autoria(self):
        ref = {"tipo": "livro", "titulo": "Diagnóstico do setor editorial", "local": "São Paulo", "editora": "CBL", "ano": 1993}
        self.assertEqual(A.formatar_referencia(ref), "DIAGNÓSTICO do setor editorial. São Paulo: CBL, 1993.")

    def test_evento(self):
        ref = {"tipo": "evento", "autores": [SILVA], "titulo": "Bibliotecas digitais", "evento": "Seminário Nacional de Bibliotecas",
               "evento_numero": 10, "evento_ano": 2018, "evento_local": "Salvador", "local": "Salvador", "editora": "UFBA",
               "ano": 2018, "paginas": "1-12"}
        self.assertEqual(A.formatar_referencia(ref),
                         "SILVA, João Carlos. Bibliotecas digitais. In: SEMINÁRIO NACIONAL DE BIBLIOTECAS, 10., 2018, "
                         "Salvador. **Anais** [...]. Salvador: UFBA, 2018. p. 1-12.")

    def test_legislacao(self):
        ref = {"tipo": "legislacao", "jurisdicao": "Brasil", "epigrafe": "Lei nº 9.610, de 19 de fevereiro de 1998",
               "ementa": "Altera, atualiza e consolida a legislação sobre direitos autorais",
               "publicacao": "Diário Oficial da União, Brasília, DF, 20 fev. 1998"}
        self.assertEqual(A.formatar_referencia(ref),
                         "BRASIL. Lei nº 9.610, de 19 de fevereiro de 1998. Altera, atualiza e consolida a legislação "
                         "sobre direitos autorais. **Diário Oficial da União**, Brasília, DF, 20 fev. 1998.")

    KANT = {"tipo": "livro", "autores": [{"sobrenome": "Kant", "nome": "Immanuel"}], "titulo": "Crítica da razão pura",
            "tradutor": "Fernando Costa Mattos", "edicao": "4", "local": "Petrópolis", "editora": "Vozes", "ano": 2015,
            "titulo_original": "Kritik der reinen Vernunft", "ano_original": 1781}

    def test_livro_traduzido(self):
        self.assertEqual(A.formatar_referencia(self.KANT),
                         "KANT, Immanuel. **Crítica da razão pura**. Tradução: Fernando Costa Mattos. 4. ed. "
                         "Petrópolis: Vozes, 2015. Título original: Kritik der reinen Vernunft. Publicação original: 1781.")

    def test_varios_tradutores(self):
        ref = dict(self.KANT, tradutor=["Ana Lima", "Rui Costa"], titulo_original=None, ano_original=None)
        self.assertIn("Tradução: Ana Lima e Rui Costa. 4. ed.", A.formatar_referencia(ref))

    def test_capitulo_traduzido(self):
        ref = {"tipo": "capitulo", "autores": [SILVA], "titulo": "O texto", "titulo_obra": "Ensaios", "tradutor": "Rui Costa",
               "local": "São Paulo", "editora": "Ática", "ano": 2010, "paginas": "1-9"}
        self.assertIn("In: **Ensaios**. Tradução: Rui Costa. São Paulo: Ática, 2010. p. 1-9.", A.formatar_referencia(ref))

    def test_chamada_ano_original_so_quando_pedido(self):
        self.assertEqual(A.chamada(self.KANT, pagina="B 75"), "(Kant, 2015, B 75)")
        self.assertEqual(A.chamada(self.KANT, pagina="214-215"), "(Kant, 2015, p. 214-215)")
        self.assertEqual(A.chamada(self.KANT, pagina="local. 264"), "(Kant, 2015, local. 264)")
        self.assertEqual(A.chamada(self.KANT, pagina=75, ano_original=True), "(Kant, 2015 [1781], p. 75)")
        self.assertEqual(A.chamada(self.KANT, narrativa=True, ano_original=True), "Kant (2015 [1781])")

    def test_nao_inventa_ano(self):
        ref = {"tipo": "livro", "autores": [SILVA], "titulo": "X", "local": "A", "editora": "B"}
        self.assertIn("[VERIFICAR: ano]", A.formatar_referencia(ref))
        self.assertIn("ano", A.faltantes(ref))

    def test_edicao_invalida(self):
        with self.assertRaises(ValueError):
            A.formatar_referencia({"tipo": "livro"}, edicao_6023="2002")


class TestChamadas(unittest.TestCase):
    REF = {"autores": [SILVA], "ano": 2020}

    def test_2023(self):
        self.assertEqual(A.chamada(self.REF, pagina=15), "(Silva, 2020, p. 15)")

    def test_2002_caixa_alta(self):
        self.assertEqual(A.chamada(self.REF, pagina=15, edicao_10520="2002"), "(SILVA, 2020, p. 15)")

    def test_narrativa(self):
        self.assertEqual(A.chamada(self.REF, pagina=15, narrativa=True), "Silva (2020, p. 15)")

    def test_dois_tres_autores(self):
        self.assertEqual(A.chamada({"autores": [SILVA, SOUZA], "ano": 2020}), "(Silva; Souza, 2020)")
        self.assertEqual(A.chamada({"autores": [SILVA, SOUZA, COSTA], "ano": 2020}, narrativa=True),
                         "Silva, Souza e Costa (2020)")

    def test_quatro_autores(self):
        self.assertEqual(A.chamada({"autores": [SILVA, SOUZA, COSTA, LIMA], "ano": 2020}), "(Silva et al., 2020)")

    def test_entidade_e_titulo(self):
        self.assertEqual(A.chamada({"autores": [{"entidade": "Universidade de São Paulo"}], "ano": 2019}),
                         "(Universidade de São Paulo, 2019)")
        self.assertEqual(A.chamada({"titulo": "Anteprojeto de lei", "ano": 1987}), "(Anteprojeto [...], 1987)")

    def test_sufixo(self):
        refs = [{"id": "a", "autores": [SILVA], "ano": 2020, "titulo": "B"},
                {"id": "b", "autores": [SILVA], "ano": 2020, "titulo": "A"}]
        self.assertEqual(A.sufixos_mesmo_autor_ano(refs), {"b": "a", "a": "b"})


class TestTexto(unittest.TestCase):
    def test_problemas(self):
        p = A.problemas_texto("SILVA, J. Título. Disponível em: <http://x.org>. Acesso em: 10 janeiro 2020.")
        self.assertTrue(any("< >" in x for x in p))
        self.assertTrue(any("mês por extenso" in x for x in p))

    def test_sem_problemas(self):
        txt = "FREIRE, Paulo. **Pedagogia do oprimido**. 17. ed. Rio de Janeiro: Paz e Terra, 1987."
        self.assertEqual(A.problemas_texto(txt), [])

    def test_ler(self):
        r = A.ler_referencia_texto("SILVA, João Carlos; SOUZA, Maria. Leitura e escrita. **Educação em Revista**, "
                                    "v. 36, p. 15-30, 2020. DOI: https://doi.org/10.1590/0102-4698214500.")
        self.assertEqual([a["sobrenome"] for a in r["autores"]], ["Silva", "Souza"])
        self.assertEqual(r["titulo"], "Leitura e escrita")
        self.assertEqual(r["ano"], "2020")
        self.assertEqual(r["doi"], "10.1590/0102-4698214500")

    def test_ler_et_al(self):
        r = A.ler_referencia_texto("VASWANI, Ashish et al. Attention is all you need. In: ADVANCES IN NEURAL "
                                    "INFORMATION PROCESSING SYSTEMS, 30., 2017, Long Beach. **Anais** [...]. 2017.")
        self.assertEqual(r["autores"][0]["sobrenome"], "Vaswani")
        self.assertEqual(r["titulo"], "Attention is all you need")


if __name__ == "__main__":
    unittest.main()
