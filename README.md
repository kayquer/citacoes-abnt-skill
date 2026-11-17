# Citações ABNT para Claude: biblioteca, checador de referências e normas de 50 universidades

[![Página](https://img.shields.io/badge/página-kayquer.github.io%2Fcitacoes--abnt--skill-1f5f4a)](https://kayquer.github.io/citacoes-abnt-skill/)
[![Licença MIT](https://img.shields.io/badge/licença-MIT-blue)](LICENSE)
[![ABNT](https://img.shields.io/badge/NBR%206023%3A2025%20%C2%B7%2010520%3A2023%20%C2%B7%2014724%3A2024-ABNT-555)](https://kayquer.github.io/citacoes-abnt-skill/normas-abnt-vigentes.html)

Plugin com três skills para Claude Code, Claude na web, ChatGPT, Gemini e outros agentes:
- organiza suas referências numa biblioteca;
- descobre referência inventada por IA;
- aplica a ABNT vigente com as regras do manual da sua universidade.

Feito para quem escreve TCC, dissertação, tese, projeto de pesquisa ou artigo no Brasil.

**Página com as regras de cada instituição:** https://kayquer.github.io/citacoes-abnt-skill/

## Sumário

- [Sobre](#sobre)
- [Instalação](#instalação)
- [Uso](#uso)
- [Instituições](#instituições)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Testes](#testes)
- [Contribuindo](#contribuindo)
- [Fontes](#fontes)
- [Créditos](#créditos)
- [Licença](#licença)

---

## Sobre

| Skill | O que faz |
|---|---|
| `biblioteca-citacoes` | Adiciona obras por DOI, ISBN ou URL e importa .bib, .ris e CSL-JSON. Remove duplicatas. Gera a chamada `(Silva, 2020, p. 15)` e exporta a lista em ABNT, BibTeX, RIS ou CSL-JSON (Zotero, Mendeley, Pandoc). |
| `checador-citacoes` | Procura cada referência no Crossref, OpenAlex, Semantic Scholar, Open Library e Google Books. Aponta referência inexistente, quimera (título real com autor errado), DOI que leva a outra obra, chamada sem referência e referência nunca citada. |
| `abnt-formatacao` | Aplica NBR 14724:2024, 10520:2023, 6023:2025 (ou 2018), 6024, 6027 e 6028 com o perfil da instituição. Gera um modelo .docx com margens, fonte, espaçamento, estilos e paginação. |

Três regras valem para todas as skills:

1. **Nada é inventado.** Dado ausente vira `[VERIFICAR: campo]`.
2. **Uma referência só é "verificada" quando duas bases independentes confirmam título e autoria.**
3. **O manual da instituição vem antes da norma, e a norma antes do costume.** Quando o manual cita uma edição antiga da norma, a skill avisa e pergunta.

Os scripts são Python 3 e usam só a biblioteca padrão. Funcionam também sem o Claude.

## Instalação

As skills seguem o padrão aberto [Agent Skills](https://agentskills.io) e funcionam fora do Claude Code. Os pacotes ficam em [`dist/`](dist/) e são gerados por `tools/build.py`. O passo a passo com links de download está na [página do projeto](https://kayquer.github.io/citacoes-abnt-skill/#instalar).

| Onde | Como |
|---|---|
| **Claude Code** | `/plugin marketplace add kayquer/citacoes-abnt-skill` e depois `/plugin install citacoes-abnt@citacoes-abnt-skill` |
| **Claude na web e no app** | Envie [`checador-citacoes.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/claude-ai/checador-citacoes.zip), [`biblioteca-citacoes.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/claude-ai/biblioteca-citacoes.zip) e [`abnt-formatacao.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/claude-ai/abnt-formatacao.zip) em *Configurações › Capacidades › Skills*, com a execução de código ativada |
| **ChatGPT** (GPT ou Projeto) | Cole [`instrucoes.txt`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/chat/instrucoes.txt) nas instruções. Anexe [`conhecimento-instituicoes.md`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/chat/conhecimento-instituicoes.md) e [`conhecimento-normas.md`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/chat/conhecimento-normas.md). Ative a busca na web. Para usar os scripts, anexe [`citacoes-abnt-scripts.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/chat/citacoes-abnt-scripts.zip) e ative a análise de código |
| **Gemini** (Gem) | Igual ao ChatGPT: instruções mais os dois arquivos de conhecimento |
| **Gemini CLI** | `gemini extensions install https://github.com/kayquer/citacoes-abnt-skill` |
| **Hermes** | `hermes plugins install kayquer/citacoes-abnt-skill` e depois `hermes plugins enable citacoes-abnt`. O Hermes lê o `plugin.json` da raiz (formato [Agent Plugins](https://agent-plugins.org/) v1) e instala o plugin desativado. Como skill avulsa: descompacte [`citacoes-abnt-skills.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/citacoes-abnt-skills.zip) em `~/.hermes/skills/` |
| **Codex, Copilot CLI, OpenClaw** | Como plugin, pelo mesmo `.claude-plugin/plugin.json` do Claude Code. Como skill: descompacte [`citacoes-abnt-skills.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/citacoes-abnt-skills.zip) em `.agents/skills/` no projeto ou em `~/.agents/skills/` (o OpenClaw também lê `~/.openclaw/skills/`) |
| **OpenCode, Cursor** | Descompacte [`citacoes-abnt-skills.zip`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/citacoes-abnt-skills.zip) em `.agents/skills/` no projeto (o OpenCode também lê `.opencode/skills/` e `~/.config/opencode/skills/`). O OpenCode não instala plugin de manifesto, só skill. Sem suporte a skills, salve [`citacoes-abnt-agents.md`](https://github.com/kayquer/citacoes-abnt-skill/raw/main/dist/citacoes-abnt-agents.md) como `AGENTS.md`, `GEMINI.md` ou regra do Cursor |
| **Perplexity, Copilot e outros chats** | Cole `instrucoes.txt` nas instruções do espaço e anexe os arquivos de conhecimento |

No Claude Code, as skills aparecem a partir da sessão seguinte à instalação. Depois de instalar ou atualizar, reinicie o Claude Code ou abra uma nova sessão.

A checagem de existência depende de acesso à internet: busca na web no chat, ou os scripts com rede. Sem acesso, o assistente avisa que não conseguiu verificar e não marca nenhuma referência como verificada. Formatar e conferir citação × referência funcionam sem internet.

Para usar só os scripts:

```bash
git clone https://github.com/kayquer/citacoes-abnt-skill
cd citacoes-abnt-skill
python3 scripts/biblioteca.py --help      # no Windows: py -3
```

## Uso

### Pedidos ao Claude

- "Confira se as referências deste TCC existem." (anexe o .docx)
- "Formate estas referências no padrão da UFMG."
- "Adiciona o DOI 10.1038/nature14539 na bibliografia e me dá a citação da página 438."
- "Gera o modelo Word de dissertação da USP."
- "Qual a margem e a fonte exigidas pela PUC-Rio?"

### Antes e depois

Chamadas pela NBR 10520:2023:

```diff
- Segundo SILVA (2020) a escola é diálogo (SOUZA; LIMA, 2019, s.p.).
+ Segundo Silva (2020), a escola é diálogo (Souza; Lima, 2019).
```

Referência pela NBR 6023:

```diff
- IBGE. Censo 2022. Disponível em: <https://censo2022.ibge.gov.br>. Acesso em: 10 janeiro 2024.
+ INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. **Censo 2022**. Rio de Janeiro, 2023. Disponível em: https://censo2022.ibge.gov.br. Acesso em: 10 jan. 2024.
```

### Humanidades: tradução, obras completas, jornal e notas de rodapé

O formatador tem campos para os casos que mais aparecem em livros de humanidades. Não é preciso escrever código por fora nem pôr esses dados em `nota`. O exemplo completo está em [`tests/fixtures/biblioteca-humanidades.json`](tests/fixtures/biblioteca-humanidades.json). Os dados desse arquivo servem para testar a forma: confira cada obra antes de usar como referência.

| Caso | Saída |
|---|---|
| Capítulo nas obras completas do próprio autor (`in_mesmo_autor`, `volume_obra`) | `FREUD, Sigmund. Luto e melancolia. In: FREUD, Sigmund. **Obras completas**. Tradução: Paulo César de Souza. São Paulo: Companhia das Letras, 2010a. v. 12, p. 170-194. Publicação original: 1917.` |
| Clássico com organizador da edição (`organizacao`, `tradutor`, `ano_original`) | `HOBBES, Thomas. **Leviatã**: [...]. Tradução: João Paulo Monteiro e Maria Beatriz Nizza da Silva. Organização: Richard Tuck. São Paulo: Martins Fontes, 2003. Título original: Leviathan. Publicação original: 1651.` |
| Artigo com e-localização (`eloc`) e título interrogativo | `BENTO, Berenice. Necrobiopoder: quem pode habitar o Estado-nação? **Cadernos Pagu**, Campinas, n. 53, e185305, 2018. DOI: [...]` |
| Jornal com data completa (tipo `jornal`) | `OTTA, Lu Aiko. Parcela do Tesouro [...]. **O Estado de S. Paulo**, São Paulo, ano 131, n. 42656, 1 ago. 2010. Economia & Negócios, p. B1.` |
| Obra sem título (`titulo_atribuido`) | `SWIFT, Jonathan. [Sobre a mentira política]. **The Examiner**, London, n. 14, 9 nov. 1710.` |
| Entidade citada pela sigla | `INDEPENDENT INVESTIGATIVE MECHANISM FOR MYANMAR (IIMM). **Annual report**. [S. l.], 27 mar. 2024. [...]` e `(IIMM, 2024)` |

Notas de rodapé: a primeira citação de cada obra sai completa, e as seguintes saem abreviadas.

```
$ python3 scripts/biblioteca.py --arquivo biblioteca.json notas "freud2010luto:172, freud2010luto:180, hobbes2003leviata:cap. XIII"
1. FREUD, Sigmund. Luto e melancolia. In: FREUD, Sigmund. **Obras completas**. [...] 2010a. v. 12, p. 172. Publicação original: 1917.
2. FREUD, 2010a, p. 180.
3. HOBBES, Thomas. **Leviatã**: [...]. Organização: Richard Tuck. São Paulo: Martins Fontes, 2003. cap. XIII. [...]
```

Com `--expressoes-latinas`, a segunda nota vira `*Ibid.*, p. 180.` O conferidor lê as notas do .docx e do Markdown (`[^n]:`), conta como citada a obra que só aparece em nota e avisa quando a primeira citação vem abreviada.

### Checador

```
$ python3 scripts/checar_referencias.py tests/fixtures/referencias-mistas.md
[1] VERIFICADA: LECUN, Yann; BENGIO, Yoshua; HINTON, Geoffrey. Deep learning. ...
    confirmada em: crossref, openalex, openlibrary
[6] DOI_DIVERGENTE: KOWALCZYK, Martin; ODUYA, Grace. Recursive transformer distillation ...
    - DOI não existe no Crossref
[7] QUIMERA: SOUZA, Marcos Antônio; PEREIRA, Juliana Costa. Attention is all you need. ...
    - o título existe, mas a autoria não bate com nenhuma base
```

| Status | Significa |
|---|---|
| `verificada` | 2 ou mais bases confirmam título e autoria |
| `parcial` | só 1 base achou (comum em livro nacional) |
| `nao_encontrada` | nenhuma base achou: possível referência inventada |
| `quimera` | título real, autoria errada (no mesmo ano e tipo) |
| `homonimo` | só há obra de mesmo título de outro autor, em outro ano ou tipo: não indica invenção |
| `doi_divergente` | DOI inexistente ou de outra obra |
| `url_verificada` / `url_divergente` / `url_inacessivel` | notícia ou site: o link responde e bate, leva a outra página, ou não respondeu |
| `nao_verificavel` | notícia sem URL ou título atribuído entre colchetes |
| `fora_de_cobertura` | obra anterior a 1800 sem resultado nas bases |
| `inconclusiva` / `erro_rede` | as bases não responderam |

Em lista longa, `--saida checagem.jsonl` grava cada obra assim que termina e mostra o progresso (`[12/92] verificada: ...`). Se a rodada cair ou esbarrar no limite das bases, `--retomar` refaz só o que faltou. As respostas ficam em cache por 30 dias em `~/.cache/citacoes-abnt`.

### Scripts

```bash
python3 scripts/biblioteca.py adicionar --doi 10.1590/0102-4698214500
python3 scripts/biblioteca.py citar <id> --pagina 45
python3 scripts/biblioteca.py notas "id:pág, id:pág" [--expressoes-latinas]
python3 scripts/biblioteca.py [--edicao-6023 2018] [--et-al] exportar --formato abnt|bib|ris|csl --saida refs.md
python3 scripts/checar_referencias.py trabalho.docx [--json] [--saida checagem.jsonl [--retomar]]
python3 scripts/conferir_citacoes.py trabalho.docx [--edicao-10520 2002] [--sem-notas]
python3 scripts/gerar_modelo_docx.py --instituicao usp --tipo tcc|dissertacao|tese|artigo|projeto --saida modelo.docx
```

As opções globais (`--arquivo`, `--edicao-6023`, `--edicao-10520`, `--et-al`) vão antes do subcomando.

Variáveis opcionais:

- `CROSSREF_MAILTO`: pool educado do Crossref;
- `OPENALEX_API_KEY`: chave gratuita do OpenAlex. Sem ela, o OpenAlex usa uma cota diária dividida por todos no mesmo IP. Quando a cota acaba, a base fica de fora da rodada;
- `S2_API_KEY`: limite maior no Semantic Scholar;
- `GOOGLE_BOOKS_KEY`: o Google Books limita consultas anônimas;
- `CITACOES_ABNT_CACHE` e `CITACOES_ABNT_SEM_CACHE=1`: mudam a pasta do cache e o desligam.

Sem as chaves, nada é enviado além da própria consulta.

## Instituições

As 50 instituições têm perfil de formatação. São 40 universidades, entre as maiores e as mais bem avaliadas, e 10 instituições técnicas (institutos federais e Fatec). Para 40 delas, o perfil foi levantado no manual oficial, com o link e a data da consulta. O que o manual não especifica vem do padrão ABNT, e o perfil indica isso.

<!-- instituicoes:inicio -->
| Instituição | Tipo | Norma principal | Manual oficial |
|---|---|---|---|
| [USP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/usp.html) | Pública (Estadual) | ABNT (com diretrizes próprias USP) | [2024](https://www.livrosabertos.abcd.usp.br/portaldelivrosUSP/catalog/book/1353) |
| [UNICAMP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unicamp.html) | Pública (Estadual) | ABNT | [2023](https://www.iar.unicamp.br/wp-content/uploads/2023/10/Manual-de-Normalizacao.pdf) |
| [UFRJ](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufrj.html) | Pública (Federal) | ABNT (Vancouver em Biomédicas) | [2023](https://ppgci.ibict.br/media/uploads/2024/05/Manual-para-elaboracao-e-normalizacao-de-trabalhos-academicos-SiBI-UFRJ-2023.pdf) |
| [UFMG](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufmg.html) | Pública (Federal) | ABNT | [2025](https://repositorio.ufmg.br/assets/public_html/diretrizes-para-normalizacao-de-trabalhos-academicos-da-UFMG.pdf) |
| [UFRGS](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufrgs.html) | Pública (Federal) | ABNT | não encontrado |
| [UFSC](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufsc.html) | Pública (Federal) | ABNT | [link](https://repositorio.ufsc.br/handle/123456789/180829) |
| [UnB](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unb.html) | Pública (Federal) | ABNT / APA (Psicologia) | não encontrado |
| [UNIFESP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unifesp.html) | Pública (Federal) | Vancouver / ABNT | [2024](https://unifesp.br/campus/gua/images/Biblioteca/tutoriais/Manual_de_normalizacao._Atualizacao_2024.pdf) |
| [UFPR](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpr.html) | Pública (Federal) | ABNT | [2024](https://litoral.ufpr.br/lecampo/wp-content/uploads/sites/10/2025/04/Manual_de_Normalizacao-2024-1.pdf) |
| [UNESP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unesp.html) | Pública (Estadual) | ABNT | não encontrado |
| [UFSCar](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufscar.html) | Pública (Federal) | ABNT | [2023](https://www.bco.ufscar.br/arquivos/manual-bco-nbr-14724-2023.pdf) |
| [PUC-Rio](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/puc-rio.html) | Privada (Filantrópica) | ABNT / APA | [2020](https://www.puc-rio.br/ensinopesq/ccpg/download/normas%20teses%20revisado%202020.pdf) |
| [UFPE](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpe.html) | Pública (Federal) | ABNT | [2023](https://www.ufpe.br/documents/39058/3620106/manual_normalizacao_ufpe_09_08_2023.pdf/a12437cc-d38e-4c58-b503-571f5327bf7f) |
| [UFC](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufc.html) | Pública (Federal) | ABNT | [2022](https://biblioteca.ufc.br/wp-content/uploads/2022/05/guianormalizacaotrabalhosacademicos-17.05.2022.pdf) |
| [UFBA](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufba.html) | Pública (Federal) | ABNT | não encontrado |
| [UFV](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufv.html) | Pública (Federal) | ABNT | [2025](https://www.bbt.ufv.br/wp-content/uploads/2025/01/Normalizacao-de-trabalhos-academicos-2025.pdf) |
| [UFF](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/uff.html) | Pública (Federal) | ABNT | [2012](https://dda.uff.br/wp-content/uploads/sites/66/2021/03/ManualTCCUFF.pdf) |
| [PUCRS](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/pucrs.html) | Privada (Filantrópica) | ABNT / APA | [link](https://biblioteca.pucrs.br/apoio-a-pesquisa/modelos-de-normas-tecnicas-de-documentacao/trabalhos-academicos-abnt/) |
| [UFSM](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufsm.html) | Pública (Federal) | ABNT | [2021](https://repositorio.ufsm.br/handle/1/24203) |
| [UFPel](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpel.html) | Pública (Federal) | ABNT | [2023](https://wp.ufpel.edu.br/sisbi/files/2023/11/Manual-versao-final-novembro-1.pdf) |
| [UNESA](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unesa.html) | Privada (Lucrativa) | ABNT | [2019](https://cdn.portal.estacio.br/2019_estacio_normas_para_trabalhos_academicos_doc_15_de_julho_de_2019_dc5fde9251.pdf) |
| [UNIP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unip.html) | Privada (Lucrativa) | ABNT | [2025](https://unip.br/servicos/biblioteca/assets/download/manual_de_normalizacao_abnt.pdf) |
| [UNOPAR](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unopar.html) | Privada (Lucrativa) | ABNT | não encontrado |
| [UFMA](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufma.html) | Pública (Federal) | ABNT | não encontrado |
| [UFPA](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpa.html) | Pública (Federal) | ABNT | [2023](https://facore.ufpa.br/Documentos/TCC/GTA2023.pdf) |
| [UFG](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufg.html) | Pública (Federal) | ABNT | [2016](https://files.cercomp.ufg.br/weby/up/366/o/Normaliza%C3%A7%C3%A3o.pdf) |
| [UFRN](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufrn.html) | Pública (Federal) | ABNT / Vancouver | [2022](https://arquivos.info.ufrn.br/arquivos/2022228061c9d011918632c7f1f84237c2/Orientao_uso_template_Mon_Dissert_Tese.pdf) |
| [UNICSUL](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unicsul.html) | Privada (Lucrativa) | ABNT | não encontrado |
| [UNINOVE](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/uninove.html) | Privada (Lucrativa) | ABNT / Vancouver (Medicina) | [2025](https://img.uninove.br/static/2025/0/0/0/0/0/2/5/7/8/3/4/25783446/manual-abnt-2025-1.pdf) |
| [UFAM](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufam.html) | Pública (Federal) | ABNT | [2017](https://edoc.ufam.edu.br/bitstream/123456789/9331/1/Manual_de_Normalizacao_de_trabalhos_academicos_UFAM.20-06-17.pdf) |
| [UFU](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufu.html) | Pública (Federal) | ABNT | [2025](https://repositorio.ufu.br/bitstream/123456789/47665/14/GuiaParaNormalizacao.pdf) |
| [UFPI](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpi.html) | Pública (Federal) | ABNT | [2025](https://ufpi.br/images/Biblioteca/Manual_Oficial.pdf) |
| [UFPB](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufpb.html) | Pública (Federal) | ABNT | [2023](https://repositorio.ufpb.br/jspui/bitstream/123456789/34249/1/Manual%20TCC%20-%20Documento%20unico%20revisado%20-%20vers%c3%a3o%2021082023.pdf) |
| [UFAL](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufal.html) | Pública (Federal) | ABNT | [2025](https://www.repositorio.ufal.br/jspui/bitstream/123456789/10627/3/Manual%20para%20normaliza%c3%a7%c3%a3o%20de%20trabalhos%20acad%c3%aamicos%20da%20UFAL%20-%202.ed.2025.pdf) |
| [UFMT](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ufmt.html) | Pública (Federal) | ABNT | não encontrado |
| [UEM](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/uem.html) | Pública (Estadual) | ABNT | não encontrado |
| [UEL](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/uel.html) | Pública (Estadual) | ABNT | [2025](https://sites.uel.br/bibliotecas/wp-content/uploads/2025/02/ABNT-fev.-2025.pdf) |
| [UERJ](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/uerj.html) | Pública (Estadual) | ABNT | [2012](https://www.rsirius.uerj.br/extras/downloads/roteiro_de_teses_e_dissertacoes.pdf) |
| [Anhembi Morumbi](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/anhembi-morumbi.html) | Privada (Lucrativa) | ABNT / APA | [2024](https://repositorio.animaeducacao.com.br/assets/dspace/docs/ebook_anima.pdf) |
| [UNISINOS](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/unisinos.html) | Privada (Filantrópica) | ABNT | [2024](https://unisinos.br/biblioteca/images/abnt/2024-2/MANUAL_ABNT_BIBLIOTECA_2024-2.pdf) |
| [IFSP](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifsp.html) | Instituto Federal | ABNT (Geral) / APA (Áreas Tecnológicas específicas) | [2011](https://spo.ifsp.edu.br/images/arquivos/documentos_institucionais/Guia_de_Normalizacao.pdf) |
| [FATEC](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/fatec.html) | Faculdade de Tecnologia | ABNT | [2024](https://bkpsitecpsnew.blob.core.windows.net/uploadsitecps/sites/70/2024/05/2024-ABR-Manual-de-Normatizacao-Trabalhos-Academico-Fatec-Ipiranga.pdf) |
| [IFRJ](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifrj.html) | Instituto Federal | ABNT / Vancouver (Cursos da área de Saúde) | [2025](https://portal.ifrj.edu.br/sites/default/files/IFRJ/ConSup/Resolucoes2025/resolucao_consup_ifrj_no_236-2025_-_completa.pdf) |
| [IFMG](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifmg.html) | Instituto Federal | ABNT | [2020](https://plone.ifmg.edu.br/portal/ensino/bibliotecas/arquivos-bibliotecas/copy_of_ManualdeNormalizaoIFMG2020.pdf) |
| [IFRS](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifrs.html) | Instituto Federal | ABNT | [2019](https://ifrs.edu.br/caxias/wp-content/uploads/sites/8/2022/04/Manual-para-elaboracao-de-trabalhos-academicos.pdf) |
| [IFSC](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifsc.html) | Instituto Federal | ABNT | [2025](https://liferay-balanceador.ifsc.edu.br/documents/d/documentos-uteis/manual-de-normalizacao_rev_08abr25-pdf) |
| [IFPR](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifpr.html) | Instituto Federal | ABNT | [2023](https://editora.ifpr.edu.br/aeditora/catalog/view/72/34/407) |
| [IFCE](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifce.html) | Instituto Federal | ABNT | [2020](https://h-portal.ifce.edu.br/documents/3795/Manual_de_normalizacao.pdf) |
| [IFPE](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifpe.html) | Instituto Federal | ABNT | não encontrado |
| [IFB](https://kayquer.github.io/citacoes-abnt-skill/instituicoes/ifb.html) | Instituto Federal | ABNT | [2017](https://www.ifb.edu.br/attachments/article/15820/Manual%20de%20normaliza%C3%A7%C3%A3o%20de%20trabalhos%20acad%C3%AAmicos.pdf) |
<!-- instituicoes:fim -->

Os dados estão em [`data/instituicoes.json`](data/instituicoes.json). Os perfis lidos pela skill ficam em [`skills/abnt-formatacao/references/instituicoes/`](skills/abnt-formatacao/references/instituicoes/).

## Estrutura do Projeto

```
citacoes-abnt-skill/
├── .claude-plugin/          marketplace.json e plugin.json
├── skills/
│   ├── biblioteca-citacoes/SKILL.md
│   ├── checador-citacoes/SKILL.md
│   └── abnt-formatacao/
│       ├── SKILL.md
│       └── references/
│           ├── normas/          NBR 6023, 10520, 14724 e vigência
│           └── instituicoes/    um perfil por instituição (gerado)
├── scripts/                 abnt_lib, biblioteca, metadados, checar_referencias,
│                            conferir_citacoes, documento, gerar_modelo_docx
├── data/                    instituicoes.json (gerado), base dos CSVs e pesquisa nos manuais
├── tools/                   build.py (perfis, site e tabela do README), site_gen.py, og_image.py
├── docs/                    GitHub Pages (gerado)
├── dist/                    pacotes para Claude.ai, ChatGPT, Gemini, Codex e outros (gerado)
├── portatil/instrucoes.md   instruções para chats, base do pacote dist/chat/
├── gemini-extension.json    manifesto da extensão do Gemini CLI
└── tests/                   testes de unidade e fixtures
```

`py -3 tools/build.py` gera os perfis, o site, os pacotes de `dist/` e a tabela acima a partir de `data/`. `--verificar` falha se algum arquivo gerado estiver defasado.

## Testes

```bash
python3 -m unittest discover tests     # 89 testes, sem rede (as bases são simuladas)
python3 tools/build.py --verificar
python3 scripts/checar_referencias.py tests/fixtures/referencias-mistas.md   # teste real, com rede
```

A fixture `referencias-mistas.md` traz 3 referências reais, 3 inventadas, 1 quimera e 1 DOI de outra obra. Nenhuma das falsas pode sair como `verificada`.

## Contribuindo

Manuais mudam. Se o perfil da sua instituição está errado ou desatualizado, abra uma issue com o link do manual oficial. Para editar direto:

1. Altere a entrada em `data/pesquisa/grupo*.json`, com a URL do manual e o campo `conferido_em`.
2. Rode `py -3 tools/build.py` e `py -3 -m unittest discover tests`.
3. Abra o pull request.

Para incluir uma instituição, acrescente uma linha ao CSV de origem, rode `tools/importar_csv.py` e depois inclua a pesquisa.

## Fontes

- Edições vigentes: catálogo Target (histórico de edições) e folhas de rosto das normas. Detalhes em [`vigencia.md`](skills/abnt-formatacao/references/normas/vigencia.md).
- Regras práticas: guias das bibliotecas da ECA-USP, UFU, UFSCar, UFV, UNESP, IFCE e Unifor.
- Perfis: manuais oficiais de cada instituição, com o link em cada perfil.

As normas ABNT são pagas. Este repositório resume as regras com palavras próprias e não reproduz o texto das normas. Não há vínculo com a ABNT nem com as instituições listadas.

## Créditos

O projeto foi escrito do zero. As ideias vieram destas skills, que recebem a atribuição também nos SKILL.md e na página:

- [PHY041/claude-skill-citation-checker](https://github.com/PHY041/claude-skill-citation-checker): verificação em várias bases, critério de duas bases e detecção de quimera.
- [K-Dense-AI/claude-scientific-writer, `citation-management`](https://github.com/K-Dense-AI/claude-scientific-writer/blob/main/.claude/skills/citation-management/SKILL.md) (MIT): metadado externo tratado como dado não confiável, deduplicação e exportação.
- [viniciusvcgprofssional/claude-skills-academic](https://github.com/viniciusvcgprofssional/claude-skills-academic) (MIT) e [ABNT Word Template Generator](https://mcpmarket.com/tools/skills/abnt-word-template-generator): papel da referência no argumento e modelo Word ABNT.
- [DevAlissu/pesquisador-br-skill](https://github.com/DevAlissu/pesquisador-br-skill) (MIT): um arquivo por norma, etapa bloqueante de integridade, DOI para ABNT e declaração de uso de IA.
- [carlosafjr-dev/abnt-academico-skill](https://github.com/carlosafjr-dev/abnt-academico-skill) (MIT): quadro de normas vigentes, prioridade instituição > norma > costume e conferência citação × referência.

Licenças e detalhes em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Para citar este projeto, use o [CITATION.cff](CITATION.cff).

## Licença

MIT, ver [LICENSE](LICENSE). Feito por [Kayque Rotondo](https://github.com/kayquer).
