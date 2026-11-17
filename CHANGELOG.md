# Changelog

## 1.3.0 (2026-11-16)

Compatibilidade com mais agentes e ajustes apontados pelo [SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) da NVIDIA.

- **Hermes:** `plugin.json` na raiz, no formato [Agent Plugins](https://agent-plugins.org/) v1. `hermes plugins install kayquer/citacoes-abnt-skill` e depois `hermes plugins enable citacoes-abnt`.
- **OpenClaw, OpenCode e Copilot CLI:** instruções de instalação no README e na página. O `.claude-plugin/plugin.json` já servia Codex, Copilot CLI e OpenClaw como plugin; o OpenCode instala as skills de `dist/citacoes-abnt-skills.zip`.
- A `description` de cada skill abre com o gatilho (`Use quando…`). O Hermes mostra só os primeiros ~60 caracteres na lista de skills.
- `metadata` no frontmatter (autor, versão e tags, todos como texto, que é o que o Hermes aceita).
- Seções Requisitos, Limites e Problemas comuns nas três skills.
- `tests/test_versao.py` exige a mesma versão em `.claude-plugin/plugin.json`, `plugin.json`, `gemini-extension.json`, `CITATION.cff` e no `metadata` das skills.

## 1.2.0 (2026-11-01)

Correções e campos novos a partir do relatório de uso num livro de humanidades: 92 obras, 122 notas de rodapé, conversão de Chicago para ABNT.

**Correções**
- A lista exportada em ABNT leva o mesmo `2010a`/`2010b` da chamada. Antes, só a chamada recebia o sufixo.
- Título que termina em `?` ou `!` não ganha ponto depois (`...X/Twitter?.` vira `...X/Twitter?`).
- Capítulo na obra do próprio autor: com `in_mesmo_autor: true`, o autor se repete depois de `In:` sem `(org.)`.
- Entrada pelo título com artigo ou monossílabo inicial: `A SOCIEDADE do espetáculo`, `(A sociedade [...], 1997)`.
- Entidade com `sigla` sai `NOME (SIGLA)` na referência, para casar com a chamada `(SIGLA, ano)`.
- `problemas_texto` aceita ano com sufixo (`2010a`) e anos de 1000 a 1499.
- A leitura de URL confere também o destino dos redirecionamentos (SSRF).

**Campos novos no formatador**
- `eloc` (e-localização): `v. 118, n. 9, e2023301118, 2021.`, sem `p.`. O Crossref preenche pelo `article-number`. Identificador gravado em `paginas` também sai sem `p.`.
- Tipo `jornal`, com `data` (AAAA-MM-DD) e `caderno`: `**Jornal**, Local, ano 131, n. 42656, 1 ago. 2010. Caderno, p. B1.` Site e artigo também aceitam `data`.
- `volume_obra`: `2010. v. 12, p. 170-194.` Livro com `volume` também sai com `v.`.
- Responsabilidades: `organizacao`, `revisao`, `prefacio`, `introducao`, `notas_de`, `ilustracao` ou a lista `responsabilidades`, no lugar da tradução. O Crossref preenche `tradutor`.
- `titulo_atribuido`: título entre colchetes.
- `faltantes` avisa sobre local com homônimo (Cambridge, Birmingham) e sobre identificador gravado como página.
- BibTeX (`date`, `eid`, `section`, `entrysubtype = newspaper`, `foreword`, `introduction`, `annotator`), RIS (`NEWS`, `DA`) e CSL-JSON (`article-newspaper`, data completa, `section`) levam os campos novos.

**Notas de rodapé**
- `biblioteca.py notas "id:pág, id:pág"`: a primeira citação de cada obra sai completa, com o localizador no lugar das páginas; as seguintes, abreviadas (`FREUD, 2010a, p. 180.`). `--expressoes-latinas` usa *Ibid.* e *Id.*, e `--minusculas` produz a forma abreviada em caixa baixa.
- `biblioteca.py nota id --forma completa|curta|ibid|idem|opcit|loccit`.
- O conferidor lê as notas do .docx (rodapé e fim) e do Markdown (`[^n]:`). A obra citada só em nota conta como citada. Ele também avisa quando a primeira citação vem abreviada, quando a nota cita autor fora da lista e quando há *Ibid.* sem nota anterior.

**Checador de existência**
- Progresso no stderr (`[12/92] verificada: ...`), `--saida checagem.jsonl` gravado a cada obra e `--retomar`, que refaz só o que caiu ou esbarrou no limite de taxa.
- Cache em disco de 30 dias (`~/.cache/citacoes-abnt`, `--sem-cache`).
- Bases consultadas em paralelo, cada uma com uma chamada por vez.
- Cota esgotada: com `Retry-After` longo ou 429 seguidos, a base sai da rodada em vez de atrasar cada obra.
- `OPENALEX_API_KEY`: sem chave, o OpenAlex agora usa uma cota diária dividida por IP.
- `homonimo`: mesmo título com outro autor em outro ano (mais de 5) ou tipo (livro × artigo) não vira mais `quimera`.
- A comparação de título aceita a base com só o título principal ("Get the message").
- Um sobrenome comum numa lista longa não confirma autoria sozinho: precisa ser o do primeiro autor de um dos lados.
- `sugestao_doi` só sai com ano compatível e mesmo periódico. DOI de preprint (SSRN, arXiv, bioRxiv...) e de reedição é recusado com alerta.
- Notícia, site e lei não vão para as bases acadêmicas: o checador confere o link (`url_verificada`, `url_divergente`, `url_inacessivel`, `nao_verificavel`). Sem resultado nas bases, o link também conta como evidência.
- Título atribuído `[entre colchetes]` sai `nao_verificavel`, e obra anterior a 1800 sem resultado sai `fora_de_cobertura`.

**Documentação**
- README: aviso para reiniciar o Claude Code depois de instalar, exemplos de humanidades e as variáveis de ambiente. O fixture `tests/fixtures/biblioteca-humanidades.json` cobre esses casos.

## 1.1.1 (2026-11-01)

- **Obra traduzida.** O formatador ganhou os campos `tradutor` (texto ou lista), `titulo_original` e `ano_original`. Pela NBR 6023, `Tradução: Nome.` vem depois do título e antes da edição; o título original e a publicação original entram no fim. Os três campos passam por BibTeX (biblatex: `translator`, `origtitle`, `origdate`) e por CSL-JSON nos dois sentidos.
- `biblioteca.py citar --ano-original` gera `(Kant, 2015 [1781], p. 75)`. É costume, não está na NBR 10520:2023, e o script avisa isso.
- `p.` só entra quando o localizador é número ou intervalo. Localizador próprio fica como está: `B 75`, `local. 264`, `cap. V`.
- Fontes em LF, com `.gitattributes`, para os pacotes de `dist/` saírem iguais em qualquer sistema.

## 1.1.0 (2026-11-01)

- Funciona fora do Claude Code. `tools/portatil.py` gera os pacotes de `dist/`:
  - **skills autocontidas**, com scripts, dados e referências dentro de cada pasta: uma por zip, para o Claude.ai, e as três juntas, para `.agents/skills` (Codex, Gemini CLI, Cursor, Copilot);
  - **pacote de chat** para ChatGPT, Gemini, Copilot e Perplexity: instruções com no máximo 8.000 caracteres, dois arquivos de conhecimento e os scripts para quem tem análise de código;
  - **`citacoes-abnt-agents.md`**, para salvar como `AGENTS.md` ou `GEMINI.md`.
- `gemini-extension.json`: extensão do Gemini CLI, que carrega as skills da pasta `skills/`.
- Sem acesso à internet, as instruções mandam declarar a referência como não verificada.

## 1.0.0 (2026-11-01)

- Três skills: `biblioteca-citacoes`, `checador-citacoes` e `abnt-formatacao`.
- Scripts em Python, só com a biblioteca padrão:
  - `abnt_lib` formata pela NBR 6023 (2025 e 2018) e cita pela NBR 10520 (2023 e 2002);
  - `biblioteca` gerencia o biblioteca.json e exporta em ABNT, BibTeX, RIS e CSL-JSON;
  - `metadados` busca em Crossref, OpenAlex, Semantic Scholar, Open Library, Google Books e meta tags citation_*;
  - `checar_referencias` confere a existência das obras em duas ou mais bases e detecta quimera e DOI divergente;
  - `conferir_citacoes` compara citação e referência;
  - `gerar_modelo_docx` gera o modelo Word da instituição.
- Perfis de 50 instituições: 40 universidades e 10 técnicas. Cada um traz a URL do manual consultado e a data da conferência.
- Página no GitHub Pages: uma página por instituição, quadro das normas vigentes, JSON-LD, sitemap e llms.txt.
