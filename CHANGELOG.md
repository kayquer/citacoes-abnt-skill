# Changelog

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
