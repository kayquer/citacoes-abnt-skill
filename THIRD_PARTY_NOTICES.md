# Atribuições e avisos de terceiros

O código e o texto deste repositório foram escritos do zero. Nenhum arquivo foi copiado das skills abaixo. Elas inspiraram as ideias listadas e recebem crédito aqui, nos SKILL.md, no README e no rodapé da página.

| Projeto | Licença | Ideia aproveitada |
|---|---|---|
| [PHY041/claude-skill-citation-checker](https://github.com/PHY041/claude-skill-citation-checker) | README declara MIT; o repositório não tem arquivo LICENSE | consulta em Crossref, Semantic Scholar e OpenAlex; critério de 2 bases para "verificada"; detecção de citação quimérica; códigos de saída |
| [K-Dense-AI/claude-scientific-writer](https://github.com/K-Dense-AI/claude-scientific-writer) (`citation-management`) | MIT, Copyright (c) 2025-2026 K-Dense Inc. | metadado externo como dado não confiável; deduplicação por chave; exportação em vários formatos |
| [viniciusvcgprofssional/claude-skills-academic](https://github.com/viniciusvcgprofssional/claude-skills-academic) | MIT, Copyright (c) 2026 @Viniciusvcgprofssional | classificação de referências pelo papel no argumento; modelo Word ABNT com campos em azul |
| [ABNT Word Template Generator](https://mcpmarket.com/tools/skills/abnt-word-template-generator) (MCP Market, mesma skill `word-personalize` acima) | MIT | geração de modelo .docx/.dotx |
| [DevAlissu/pesquisador-br-skill](https://github.com/DevAlissu/pesquisador-br-skill) | MIT, Copyright (c) 2026 Alison Silva (DevAlissu) | um arquivo de referência por norma; etapa bloqueante de integridade; DOI para ABNT; proteção contra SSRF; declaração de uso de IA |
| [carlosafjr-dev/abnt-academico-skill](https://github.com/carlosafjr-dev/abnt-academico-skill) | MIT, Copyright (c) 2026 Carlos Alberto Ferreira, Agência Ojuobá | quadro de normas vigentes com data de conferência; prioridade instituição > norma > costume; `[VERIFICAR]`; conferência citação × referência |

## Normas e manuais

- As normas da ABNT (NBR 6023, 10520, 14724, 6024, 6027, 6028, 6022, 15287, 6034, 12225) pertencem à Associação Brasileira de Normas Técnicas e são vendidas por ela. Este projeto não reproduz o texto das normas. Os arquivos em `skills/abnt-formatacao/references/normas/` resumem, com palavras próprias, guias públicos de bibliotecas universitárias, listados em `vigencia.md`.
- Os perfis em `data/instituicoes.json` e em `skills/abnt-formatacao/references/instituicoes/` resumem os manuais oficiais de cada instituição. Cada perfil traz a URL do manual consultado. O projeto não tem vínculo com a ABNT nem com as instituições listadas.
- A lista inicial de instituições (nome, tipo, categoria, fomento e norma predominante) veio de duas planilhas preparadas pelo autor.

## Serviços consultados pelos scripts

Crossref, OpenAlex, Semantic Scholar, Open Library e Google Books são consultados pelas APIs públicas, sem chave, conforme os termos de cada serviço. Os scripts esperam 1 segundo entre chamadas à mesma base.
