"""Testes de regressão.

Três frentes:

1. **Estrutura das skills**: as regras de compatibilidade entre agentes (Hermes,
   OpenClaw, Copilot) e a coerência entre o que o SKILL.md manda rodar e o que
   os scripts aceitam. Uma flag renomeada num script quebra a skill em silêncio.
2. **Snapshots**: a saída das CLIs sobre os fixtures, comparada com
   `tests/fixtures/esperado/`. Qualquer mudança de formatação aparece aqui.
   Depois de uma mudança intencional, regenere com
   `REGRESSAO_ATUALIZAR=1 py -3 -m unittest tests.test_regressao` e revise o diff.
3. **Correções do CHANGELOG** que ainda não tinham teste próprio.

Tudo roda offline: rede e DNS são simulados.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
FIX = RAIZ / "tests" / "fixtures"
ESPERADO = FIX / "esperado"
SKILLS = ("abnt-formatacao", "biblioteca-citacoes", "checador-citacoes")
ATUALIZAR = os.environ.get("REGRESSAO_ATUALIZAR") == "1"

sys.path.insert(0, str(SCRIPTS))
import abnt_lib as A  # noqa: E402
import biblioteca as B  # noqa: E402
import checar_referencias as C  # noqa: E402
import conferir_citacoes as F  # noqa: E402
import metadados as M  # noqa: E402


def frontmatter(nome):
    texto = (RAIZ / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", texto, re.DOTALL)
    return m.group(1), texto


def ajuda(script, *sub):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *sub, "--help"], capture_output=True,
                       text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout


# ------------------------------------------------------------------ 1. estrutura das skills

class TestEstruturaDasSkills(unittest.TestCase):
    def test_frontmatter_compativel_com_os_agentes(self):
        for nome in SKILLS:
            with self.subTest(skill=nome):
                frente, _ = frontmatter(nome)
                self.assertRegex(frente, rf"(?m)^name: {re.escape(nome)}$")
                self.assertNotRegex(frente, r"(?m)^version:", "version de topo não é campo Agent Skills")
                desc = re.search(r'(?m)^description: "(.*)"$', frente).group(1)
                self.assertLessEqual(len(desc), 1024, "Copilot e Hermes descartam description acima de 1024")
                self.assertTrue(desc.startswith("Use quando"), "o Hermes só mostra ~60 caracteres")
                self.assertNotIn('\\"', desc, "aspas duplas internas viram &quot; no Copilot/OpenClaw")
                bloco = re.search(r"(?ms)^metadata:\n((?:  .*\n?)+)", frente).group(1)
                for linha in bloco.strip("\n").splitlines():
                    self.assertRegex(linha, r'^  [a-z_]+: ".*"$', f"metadata só com texto (Hermes): {linha}")

    def test_tamanhos_para_o_openclaw(self):
        for nome in SKILLS:
            pasta = RAIZ / "skills" / nome
            _, texto = frontmatter(nome)
            self.assertLess(len(texto), 15000, f"{nome}/SKILL.md")
            for arq in (pasta / "references").rglob("*") if (pasta / "references").exists() else []:
                if arq.is_file():
                    self.assertLess(arq.stat().st_size, 16 * 1024, str(arq.relative_to(RAIZ)))

    def test_referencias_citadas_existem(self):
        for nome in SKILLS:
            _, texto = frontmatter(nome)
            for caminho in set(re.findall(r"references/[\w./-]+\.md", texto)):
                with self.subTest(skill=nome, caminho=caminho):
                    achou = [s for s in SKILLS if (RAIZ / "skills" / s / caminho).exists()]
                    self.assertTrue(achou, f"{caminho} não existe em nenhuma skill")

    def test_comandos_do_skill_md_batem_com_os_scripts(self):
        """Cada `$SCRIPTS/x.py [sub] --flag` citado precisa existir no argparse do script."""
        ajudas = {}
        for nome in SKILLS:
            _, texto = frontmatter(nome)
            for linha in re.findall(r'\$SCRIPTS/([a-z_]+\.py)"?([^\n`]*)', texto):
                script, resto = linha
                with self.subTest(skill=nome, comando=f"{script}{resto}"):
                    self.assertTrue((SCRIPTS / script).exists(), script)
                    if not resto.strip() or script == "abnt_lib.py":
                        continue
                    resto = resto.split("#")[0]
                    if script not in ajudas:
                        ajudas[script] = ajuda(script)[1]
                    geral = ajudas[script]
                    subs = re.search(r"\{([a-z,-]+)\}", geral)
                    subs = subs.group(1).split(",") if subs else []
                    tokens = resto.replace("[", " ").replace("]", " ").split()
                    sub = next((t for t in tokens if t in subs), None)
                    texto_sub = ""
                    if sub:
                        chave = f"{script} {sub}"
                        if chave not in ajudas:
                            ajudas[chave] = ajuda(script, sub)[1]
                        texto_sub = ajudas[chave]
                    antes_do_sub = True
                    for i, t in enumerate(tokens):
                        if t == sub:
                            antes_do_sub = False
                        if not t.startswith("--"):
                            continue
                        alvo = geral if (antes_do_sub or not sub) else texto_sub
                        self.assertIn(t, alvo, f"{t} não aparece no --help de {script} {sub or ''}")
                        # --forma completa|curta|...: todas as opções existem
                        if i + 1 < len(tokens) and "|" in tokens[i + 1]:
                            for opcao in tokens[i + 1].split("|"):
                                self.assertIn(opcao, alvo, f"{t} {opcao}")


# ------------------------------------------------------------------ 2. snapshots

class TestSnapshots(unittest.TestCase):
    """Saída completa das CLIs sobre os fixtures. Falha mostra o diff do que mudou."""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.bib = Path(cls.tmp.name) / "biblioteca.json"
        shutil.copy(FIX / "biblioteca-humanidades.json", cls.bib)
        cls.env = {**os.environ, "PYTHONIOENCODING": "utf-8", "CITACOES_ABNT_SEM_CACHE": "1"}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _cli(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True,
                           encoding="utf-8", env=self.env, cwd=self.tmp.name)
        return r.stdout.replace(self.tmp.name, "<tmp>").replace("\r\n", "\n")

    def _comparar(self, nome, saida):
        arq = ESPERADO / nome
        if ATUALIZAR or not arq.exists():
            arq.parent.mkdir(exist_ok=True)
            arq.write_text(saida, encoding="utf-8", newline="\n")
            if not ATUALIZAR:
                self.skipTest(f"snapshot criado: {arq.name}")
            return
        self.assertEqual(saida, arq.read_text(encoding="utf-8"), f"{nome} mudou")

    def test_exportar_abnt_2025(self):
        self._comparar("exportar-abnt-2025.md", self._cli("biblioteca.py", "--arquivo", str(self.bib), "exportar"))

    def test_exportar_abnt_2018_et_al(self):
        self._comparar("exportar-abnt-2018-et-al.md", self._cli(
            "biblioteca.py", "--arquivo", str(self.bib), "--edicao-6023", "2018", "--et-al", "exportar"))

    def test_exportar_bib_ris_csl(self):
        for formato in ("bib", "ris", "csl"):
            with self.subTest(formato=formato):
                self._comparar(f"exportar.{formato}.txt", self._cli(
                    "biblioteca.py", "--arquivo", str(self.bib), "exportar", "--formato", formato))

    def test_notas_com_expressoes_latinas(self):
        seq = "freud2010luto:172, freud2010luto:180, freud2010mal:20, freud2010luto:190, hobbes2003leviata:cap. XIII"
        self._comparar("notas-latinas.json", self._cli(
            "biblioteca.py", "--arquivo", str(self.bib), "notas", seq, "--expressoes-latinas"))
        self._comparar("notas-minusculas.json", self._cli(
            "biblioteca.py", "--arquivo", str(self.bib), "notas", seq, "--minusculas"))

    def test_conferir_citacoes(self):
        for fixture in ("trabalho-com-erros.md", "livro-com-notas.md"):
            with self.subTest(fixture=fixture):
                self._comparar(f"conferir-{fixture}.json", self._cli(
                    "conferir_citacoes.py", str(FIX / fixture), "--json"))

    def test_conferir_citacoes_2002(self):
        self._comparar("conferir-trabalho-com-erros-2002.json", self._cli(
            "conferir_citacoes.py", str(FIX / "trabalho-com-erros.md"), "--json", "--edicao-10520", "2002"))

    def test_checar_sem_rede(self):
        self._comparar("checar-sem-rede.json", self._cli(
            "checar_referencias.py", str(FIX / "referencias-mistas.md"), "--sem-rede", "--json", "--silencioso"))

    def test_biblioteca_nao_e_alterada_pela_leitura(self):
        antes = (FIX / "biblioteca-humanidades.json").read_bytes()
        self._cli("biblioteca.py", "--arquivo", str(self.bib), "exportar")
        self._cli("biblioteca.py", "--arquivo", str(self.bib), "faltantes")
        self.assertEqual(json.loads(self.bib.read_bytes()), json.loads(antes))


# ------------------------------------------------------------------ 3. correções do CHANGELOG

def _dns(ip):
    return lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


class TestSSRF(unittest.TestCase):
    """1.2.0: a leitura de URL recusa endereço interno, inclusive depois de redirecionamento."""

    def test_recusa_enderecos_internos(self):
        for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0", "::1", "fe80::1"):
            with self.subTest(ip=ip), mock.patch.object(M.socket, "getaddrinfo", _dns(ip)):
                with self.assertRaises(M.ErroRede):
                    M._host_publico("https://exemplo.org/artigo")

    def test_aceita_endereco_publico(self):
        with mock.patch.object(M.socket, "getaddrinfo", _dns("200.144.0.1")):
            M._host_publico("https://www.scielo.br/j/x")

    def test_recusa_esquema_que_nao_e_http(self):
        for url in ("file:///etc/passwd", "ftp://exemplo.org/x", "gopher://exemplo.org"):
            with self.subTest(url=url), self.assertRaises(M.ErroRede):
                M._host_publico(url)

    def test_redirecionamento_para_endereco_interno(self):
        req = urllib.request.Request("https://publico.org/x")
        with mock.patch.object(M.socket, "getaddrinfo", _dns("169.254.169.254")), self.assertRaises(M.ErroRede):
            M._RedirecionamentoPublico().redirect_request(req, None, 302, "Found", {}, "http://metadata.interno/")


class TestCota(unittest.TestCase):
    """1.2.0: 429 com Retry-After longo tira a base da rodada em vez de atrasar cada obra."""

    BASE = "base-de-teste"

    def tearDown(self):
        M._bloqueada.pop(self.BASE, None)
        M._falhas_429.pop(self.BASE, None)

    def test_retry_after_longo_bloqueia_a_base(self):
        def abrir(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {"Retry-After": "3600"}, None)
        req = urllib.request.Request("https://api.exemplo.org/x")
        with mock.patch.object(M.time, "sleep") as dormir:
            with self.assertRaisesRegex(M.ErroRede, "cota esgotada"):
                M._get_serial(req, self.BASE, abrir)
            self.assertFalse(any(c.args and c.args[0] >= 60 for c in dormir.call_args_list),
                             "não deve esperar o Retry-After longo")
        chamado = mock.Mock()
        with mock.patch.object(M.urllib.request, "urlopen", chamado), self.assertRaises(M.ErroRede):
            M._get("https://api.exemplo.org/y", self.BASE)
        chamado.assert_not_called()

    def test_404_nao_e_erro(self):
        def abrir(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        self.assertEqual(M._get_serial(urllib.request.Request("https://x.org"), self.BASE, abrir), (None, ""))


class TestCrossref(unittest.TestCase):
    """1.2.0: o Crossref preenche `eloc` pelo article-number e `tradutor` pelo translator."""

    ITEM = {"type": "journal-article", "title": ["Exemplo"], "container-title": ["PNAS"],
            "author": [{"given": "Ana", "family": "Souza"}], "issued": {"date-parts": [[2021, 3]]},
            "volume": "118", "issue": "9", "article-number": "e2023301118",
            "translator": [{"given": "Paulo César de", "family": "Souza"}], "DOI": "10.1073/pnas.2023301118"}

    def test_article_number_vira_eloc(self):
        ref = M.crossref_para_ref(self.ITEM)
        self.assertEqual(ref["eloc"], "e2023301118")
        self.assertEqual(ref["tradutor"], ["Paulo César de Souza"])
        self.assertEqual(ref["periodico"], "PNAS")
        self.assertNotIn("p. e2023301118", A.formatar_referencia(ref))

    def test_paginas_tem_prioridade_sobre_article_number(self):
        ref = M.crossref_para_ref(dict(self.ITEM, page="10-20"))
        self.assertNotIn("eloc", ref)
        self.assertIn("p. 10-20", A.formatar_referencia(ref))


class TestLocalizador(unittest.TestCase):
    """1.1.1: `p.` só para número, intervalo ou romano minúsculo."""

    def test_localizador_proprio_fica_como_esta(self):
        for loc in ("cap. V", "B 75", "local. 264", "9min 41s", "art. 5", "f. 3"):
            with self.subTest(loc=loc):
                self.assertEqual(A.localizador(loc), loc)

    def test_numero_intervalo_e_romano(self):
        self.assertEqual(A.localizador("45"), "p. 45")
        self.assertEqual(A.localizador("45–50"), "p. 45-50")
        self.assertEqual(A.localizador("xiv"), "p. xiv")

    def test_paginas_salteadas_levam_p(self):
        # 1.3.1: antes "45, 47" e "45 e 47" saíam sem "p."
        self.assertEqual(A.localizador("45, 47"), "p. 45, 47")
        self.assertEqual(A.localizador("45 e 47"), "p. 45 e 47")
        self.assertEqual(A.localizador("12-14, 20"), "p. 12-14, 20")
        self.assertEqual(A.chamada({"autores": [{"sobrenome": "Silva"}], "ano": 2020}, pagina="45, 47"),
                         "(Silva, 2020, p. 45, 47)")
        self.assertEqual(A.localizador("cap. V, VI"), "cap. V, VI")  # localizador próprio continua intocado


class TestPreprint(unittest.TestCase):
    """1.2.0: DOI de preprint é recusado como sugestão."""

    def test_prefixos_conhecidos(self):
        self.assertEqual(C.preprint("10.2139/ssrn.123"), "SSRN")
        self.assertEqual(C.preprint("10.48550/arXiv.1706.03762"), "arXiv")
        self.assertEqual(C.preprint("10.1590/SciELOPreprints.1234"), "SciELO Preprints")

    def test_doi_comum_nao_e_preprint(self):
        self.assertIsNone(C.preprint("10.1038/nature14539"))
        self.assertIsNone(C.preprint("10.1590/0102-4698214500"))

    def test_prefixo_mais_longo_nao_casa(self):
        # 1.3.1: preprint() comparava o começo do DOI sem a barra, então qualquer registrante
        # 10.1101x, 10.2139x ou 10.48550x virava "preprint" e a sugestão de DOI era recusada.
        for doi in ("10.11019/abc", "10.21390/x.1", "10.485501/y"):
            self.assertIsNone(C.preprint(doi), doi)


class TestCorrecoes131(unittest.TestCase):
    """Bugs achados na análise de 2026-11-17 e corrigidos na 1.3.1."""

    def test_sem_local_e_sem_editora_combinados(self):
        # nbr-6023-referencias.md: "Sem local e sem editora: [S. l.: s. n.]". Antes saía "[S. l.]: [s. n.]".
        self.assertEqual(A.local_editora({}), "[S. l.: s. n.]")
        self.assertEqual(A.local_editora({"local": "Recife"}), "Recife: [s. n.]")
        self.assertEqual(A.local_editora({"editora": "Vozes"}), "[S. l.]: Vozes")
        livro = {"tipo": "livro", "autores": [{"sobrenome": "Silva", "nome": "Ana"}], "titulo": "T", "ano": 2020}
        self.assertEqual(A.formatar_referencia(livro), "SILVA, Ana. **T**. [S. l.: s. n.], 2020.")

    def test_conferidor_aponta_colchetes_separados(self):
        self.assertTrue(any("num colchete só" in p for p in A.problemas_texto("SILVA, Ana. **T**. [S. l.]: [s. n.], 2020.")))
        self.assertTrue(any("com espaço" in p for p in A.problemas_texto("SILVA, Ana. **T**. [S.l.: s.n.], 2020.")))
        self.assertEqual(A.problemas_texto("SILVA, Ana. **T**. [S. l.: s. n.], 2020."), [])

    def test_checador_converte_csl_json(self):
        # A biblioteca importava CSL-JSON do Zotero, mas o checador lia .json só como biblioteca.json.
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "zotero.json"
            arq.write_text(json.dumps([{"type": "book", "title": "Pedagogia do oprimido",
                                        "author": [{"family": "Freire", "given": "Paulo"}],
                                        "issued": {"date-parts": [[1987]]}}]), encoding="utf-8")
            refs = C.carregar_refs(arq)
            self.assertEqual(refs[0].get("titulo"), "Pedagogia do oprimido")
            self.assertEqual(refs[0].get("tipo"), "livro")
            # biblioteca.json continua lido como antes
            shutil.copy(FIX / "biblioteca-humanidades.json", Path(tmp) / "biblioteca.json")
            self.assertTrue(all("tipo" in r for r in C.carregar_refs(Path(tmp) / "biblioteca.json")))

    def test_faltantes_respeita_confirmacao_do_usuario(self):
        # A skill mandava apagar `revisar` e rodar `faltantes` de novo, mas o aviso de local/editora
        # era recalculado pelos campos e nunca sumia: o agente podia ficar em laço.
        ref = {"tipo": "livro", "autores": [{"sobrenome": "Silva"}], "titulo": "T", "ano": 2020}
        self.assertEqual(len(A.faltantes(ref)), 2)
        self.assertEqual(A.faltantes(dict(ref, sem_local=True, sem_editora=True)), [])
        self.assertEqual(A.formatar_referencia(dict(ref, sem_local=True, sem_editora=True)),
                         A.formatar_referencia(ref))

    def test_perfil_legado_aceita_o_que_a_tabela_aceita(self):
        # regras-do-validador.md: no perfil 10520:2002 o ponto dobrado e as palavras-chave da 6028:2003 são aceitos.
        corpo = ['Palavras-chave: Educação. Leitura. Escola.',
                 'Ele disse que "a educação é comunicação e diálogo sempre"." (Freire, 1987).']
        refs = ["FREIRE, Paulo. **Pedagogia do oprimido**. Rio de Janeiro: Paz e Terra, 1987."]
        tipos = lambda ed: {a["tipo"] for a in F.conferir(corpo, refs, ed)["achados"]}  # noqa: E731
        self.assertLessEqual({"ponto_duplicado", "palavras_chave"}, tipos("2023"))
        self.assertFalse({"ponto_duplicado", "palavras_chave"} & tipos("2002"))

    def test_mensagens_citam_a_edicao_escolhida(self):
        corpo = ["Outros autores divergem (Souza; Lima, 2019, s.p.)."]
        msgs = [a["mensagem"] for a in F.conferir(corpo, [], "2002")["achados"]]
        self.assertTrue(any("NBR 10520:2002" in m for m in msgs), msgs)
        self.assertFalse(any("10520:2023" in m for m in msgs), msgs)
        self.assertTrue(any(m.startswith("Souza; Lima, 2019") for m in msgs), msgs)

    def test_aviso_de_maiusculas_some_com_minusculas(self):
        with tempfile.TemporaryDirectory() as tmp:
            bib = Path(tmp) / "b.json"
            shutil.copy(FIX / "biblioteca-humanidades.json", bib)
            r = subprocess.run([sys.executable, str(SCRIPTS / "biblioteca.py"), "--arquivo", str(bib), "notas",
                                "freud2010luto:1, freud2010luto:2", "--minusculas"], capture_output=True,
                               text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertNotIn("aviso", json.loads(r.stdout))


def _cli_json(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8", "CITACOES_ABNT_SEM_CACHE": "1"})
    return json.loads(r.stdout)


class TestCorrecoes131Rodada2(unittest.TestCase):
    """Achados da segunda revisão da 1.3.1."""

    def test_nota_abreviada_cita_a_edicao_escolhida(self):
        for ed in ("2023", "2002"):
            with self.subTest(edicao=ed):
                r = _cli_json("conferir_citacoes.py", str(FIX / "livro-com-notas.md"), "--json", "--edicao-10520", ed)
                msgs = [a["mensagem"] for a in r["achados"] if a["tipo"] == "nota_abreviada_antes_da_completa"]
                self.assertTrue(msgs)
                self.assertTrue(all(f"NBR 10520:{ed}" in m for m in msgs), msgs)

    def test_romano_so_quando_e_numero_romano(self):
        for palavra in ("civil", "mil", "dim", "iiii"):
            self.assertEqual(A.localizador(palavra), palavra)
        self.assertEqual(A.localizador("xiv"), "p. xiv")
        self.assertEqual(A.localizador("iv-vi"), "p. iv-vi")

    def test_notas_curtas_com_paginas_salteadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            bib = Path(tmp) / "b.json"
            shutil.copy(FIX / "biblioteca-humanidades.json", bib)
            r = _cli_json("biblioteca.py", "--arquivo", str(bib), "notas",
                          "freud2010luto:45, 47, hobbes2003leviata:12, freud2010luto:50")
        self.assertEqual([n["id"] for n in r["notas"]], ["freud2010luto", "hobbes2003leviata", "freud2010luto"])
        self.assertIn("p. 45, 47.", r["notas"][0]["nota"])
        self.assertEqual(r["notas"][2]["nota"], "FREUD, 2010a, p. 50.")

    def test_preprint_recusado_em_qualquer_tipo_salvo_quando_citado(self):
        cand = {"doi": "10.48550/arXiv.1706.03762", "ano": 2017}
        for ref in ({"tipo": "tese", "ano": "2017"}, {"tipo": "evento", "ano": "2017"}, {"tipo": "site", "ano": "2017"}):
            with self.subTest(tipo=ref["tipo"]):
                self.assertIsNone(C.avaliar_sugestao_doi(ref, cand)[0])
        citado = {"tipo": "artigo", "ano": "2017", "periodico": "arXiv"}
        self.assertEqual(C.avaliar_sugestao_doi(citado, cand)[0], "10.48550/arXiv.1706.03762")
        # "Research Policy" não pode passar por "Research Square"
        rs = {"doi": "10.21203/rs.3.rs-1/v1", "ano": 2021}
        self.assertIsNone(C.avaliar_sugestao_doi({"tipo": "artigo", "ano": "2021", "periodico": "Research Policy"}, rs)[0])

    def test_evento_sem_local_e_editora_avisa(self):
        ev = {"tipo": "evento", "titulo": "T", "evento": "CONGRESSO X", "ano": 2020}
        self.assertEqual(len(A.faltantes(ev)), 2)
        self.assertEqual(A.faltantes(dict(ev, sem_local=True, sem_editora=True)), [])

    def test_checador_aceita_json_sem_chave_referencias(self):
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "x.json"
            arq.write_text(json.dumps({"versao": 1}), encoding="utf-8")
            self.assertEqual(C.carregar_refs(arq), [])

    def test_sem_espaco_em_qualquer_caixa(self):
        for texto in ("[s.l.]: [s.n.]", "[S.L.: S.N.]"):
            with self.subTest(texto=texto):
                self.assertTrue(any("com espaço" in p for p in A.problemas_texto(f"SILVA, A. **T**. {texto}, 2020.")))


if __name__ == "__main__":
    unittest.main()
