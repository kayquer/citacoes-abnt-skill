# Changelog

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
