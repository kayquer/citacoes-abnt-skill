---
name: abnt-formatacao
description: "Formata trabalho acadêmico nas normas da ABNT vigentes (NBR 14724:2024, 10520:2023, 6023:2025 ou 2018) com o perfil de 50 instituições brasileiras (USP, Unicamp, UFMG, UFRJ, PUC, institutos federais, Fatec). Use quando pedirem para formatar ou deixar nas normas da ABNT um TCC, monografia, dissertação, tese, projeto ou artigo; corrigir margens, fonte, espaçamento, recuo, paginação, capa, folha de rosto, resumo, palavras-chave ou sumário; padronizar a forma das citações e referências; gerar modelo Word da universidade; ou perguntarem qual é a regra da universidade X. Para conferir se as obras existem, use checador-citacoes; para montar a bibliografia a partir de DOI ou ISBN, biblioteca-citacoes."
argument-hint: "[instituição] [tipo de trabalho] [arquivo]"
---
# Aplicação da ABNT com perfil da instituição

Normaliza a **forma** do trabalho. Não reescreve o conteúdo nem muda o argumento do autor.

## Ordem de prioridade

1. **Diretrizes da instituição ou do periódico.** Use o perfil em `references/instituicoes/<id>.md` ou as normas da revista.
2. **Norma ABNT vigente.** Os resumos estão em `references/normas/`.
3. **Costume consolidado.** Só quando nem a instituição nem a norma decidem. Diga ao usuário que é costume.

Quando a norma oferece opção (prenome abreviado ou por extenso, et al. ou todos os autores, negrito ou itálico), escolha **uma** forma e aplique em todo o documento.

## Fluxo

1. **Identifique a instituição, o tipo de trabalho e o curso.** Se o usuário não disse, pergunte uma vez. Procure o id em `references/instituicoes/index.md`. Se a instituição não estiver lá, use `references/instituicoes/padrao-abnt.md` e peça o manual do curso.
2. **Leia o perfil da instituição.**
   - Item marcado *padrão ABNT* ou *costume* não vem do manual: diga isso ao usuário.
   - **Edições usadas.** Edição marcada com `*` é a vigente, aplicada porque o manual não informa qual usa. Edição antiga sem `*` (NBR 6023:2018, 10520:2002 ou 14724:2011) vem do manual. Nesse caso, pergunte se o curso ainda a exige. Sem resposta, use a vigente e registre a escolha nas premissas. Se ficar a 10520:2002, rode o conferidor com `--edicao-10520 2002`.
   - **Outra norma por área** (Vancouver em saúde, APA em psicologia): confirme qual norma o programa exige antes de aplicar a ABNT.
3. **Leia só a norma do assunto em pauta.**
   - `references/normas/nbr-14724-estrutura.md`: estrutura, margens, paginação, seções (6024), sumário (6027), resumo (6028), projeto (15287) e artigo (6022).
   - `references/normas/nbr-10520-citacoes.md`: chamadas, citação direta e indireta, apud, notas.
   - `references/normas/nbr-6023-referencias.md`: elementos e pontuação das referências.
   - `references/normas/vigencia.md`: edições em vigor e o que mudou.
   - `references/normas/regras-do-validador.md`: o que é erro e o que é aviso, e o que o script confere sozinho.
4. **Aplique.**
   - Em .docx: edite uma **cópia**, nunca o original, aplicando os estilos do modelo gerado por `gerar_modelo_docx.py`. Se a skill `docx` estiver disponível, use-a para editar com controle de alterações.
   - Em .md ou .txt: corrija direto.
   - Para formatar referências a partir de dados (DOI, ISBN, campos), use `biblioteca.py`. Nenhum script reformata sozinho um .docx existente.
5. **Confira** com `conferir_citacoes.py`. Para saber se as obras existem, acione a skill `checador-citacoes`.
6. **Entregue** com as três seções a seguir.

## Entrega (sempre)

- **Premissas.** Instituição, perfil e edições usadas (por exemplo, NBR 6023:2025 e NBR 10520:2023). As escolhas feitas onde a norma dava opção. O que veio do padrão ABNT por falta de manual.
- **Mudanças.** Lista curta do que foi alterado, agrupada por tipo: margens, citações, referências, estrutura.
- **[VERIFICAR].** O que falta e só o autor sabe: cidade, editora, página citada, data de acesso, orientador, ficha catalográfica.

## Regras que não se negociam

- **Nada é inventado.** Dado ausente vira `[VERIFICAR: campo]`. Não deduza editora, cidade, página, ano nem DOI.
- **Não existe `[s.d.]` nem `s.p.`.** Sem data, peça ao autor uma data provável e use entre colchetes (`[2020?]`, `[ca. 2015]`). Sem resposta, use `[VERIFICAR: ano]`. Sem paginação, omita o localizador.
- **Chamada pela NBR 10520:2023.** Dentro dos parênteses, maiúsculas e minúsculas: `(Silva, 2020, p. 15)`. Sigla continua em maiúsculas: `(IBGE, 2023)`. Use `(SILVA, 2020)` só se o perfil ou o usuário fixar a 10520:2002.
- **Ponto final só depois da chamada:** `"... trecho" (Silva, 2020, p. 15).`
- **Citação longa** (mais de 3 linhas): recuo do perfil (4 cm, salvo outra regra do manual), fonte menor, espaço simples, sem aspas.
- **Paginação** no canto superior direito, contada desde a folha de rosto e mostrada a partir da parte textual, salvo outra regra do manual.
- **Palavras-chave** separadas por ponto e vírgula, com inicial minúscula e ponto final (NBR 6028:2021).
- **Ilustração e tabela** sempre com "Fonte:", mesmo quando for "elaborado pelo próprio autor" (NBR 14724:2024).

## Scripts

Os scripts ficam na pasta `scripts/` da raiz do plugin: `${CLAUDE_PLUGIN_ROOT}/scripts`, ou `../../scripts` a partir da pasta desta skill. Antes de rodar, resolva o caminho absoluto dessa pasta. Os exemplos abaixo o chamam de `$SCRIPTS`. Os scripts usam Python 3 e só a biblioteca padrão: rode com `python3` ou, no Windows, com `py -3`.

```bash
# modelo Word com o perfil da instituição (tcc, dissertacao, tese, artigo, projeto)
python3 "$SCRIPTS/gerar_modelo_docx.py" --instituicao ufmg --tipo dissertacao --saida modelo-ufmg.docx
python3 "$SCRIPTS/gerar_modelo_docx.py" --listar

# conferir citação × referência e forma ABNT (.docx, .md, .txt)
python3 "$SCRIPTS/conferir_citacoes.py" trabalho.docx --json [--edicao-10520 2002]

# lista de referências ABNT a partir da biblioteca (opções globais ANTES do subcomando)
python3 "$SCRIPTS/biblioteca.py" --arquivo biblioteca.json --edicao-6023 2018 --et-al exportar --formato abnt
```

- `conferir_citacoes.py` sai com código 1 quando encontra erros. Isso é resultado, não falha do script: leia o relatório.
- O modelo .docx traz:
  - estilos Normal, Título 1, Título sem número, Citação longa, Referência, Resumo, Legenda e Fonte da ilustração;
  - seções separadas para capa, pré-textuais e parte textual, com a paginação certa;
  - campos a preencher em azul, entre colchetes.
- Para virar modelo do Word, o usuário salva como `.dotx` (Arquivo > Salvar como > Modelo do Word).

## Exemplos

**Pedido:** "Arruma as citações desse parágrafo para a UFPR."

- Antes: `Segundo SILVA (2020) a escola é diálogo (SOUZA; LIMA, 2019, s.p.).`
- Depois: `Segundo Silva (2020), a escola é diálogo (Souza; Lima, 2019).`
- Premissas:
  - perfil `ufpr`, cujo manual segue a NBR 10520:2023 e a NBR 6023:2018;
  - perguntar se o curso aceita a NBR 6023:2025;
  - "s.p." removido porque a norma não usa essa forma.
- `[VERIFICAR: página da citação de Souza e Lima, se for citação direta]`.

**Pedido:** "Qual a margem da PUC-Rio?"

- Superior 2,5 cm, esquerda 3 cm, inferior 2,5 cm, direita 4 cm.
- É o projeto gráfico próprio da pós-graduação, diferente da NBR 14724. A citação longa fica alinhada ao recuo do parágrafo (1 cm).
- Fonte: perfil `puc-rio`, que traz o link do manual.

## Créditos

Ideias de [carlosafjr-dev/abnt-academico-skill](https://github.com/carlosafjr-dev/abnt-academico-skill), [DevAlissu/pesquisador-br-skill](https://github.com/DevAlissu/pesquisador-br-skill) e [viniciusvcgprofssional/claude-skills-academic](https://github.com/viniciusvcgprofssional/claude-skills-academic) (MIT). Texto e código próprios. Detalhes em `THIRD_PARTY_NOTICES.md`, na raiz do plugin.
