# Regras de conferência por perfil

> Resumo com palavras próprias de guias públicos de bibliotecas (as normas ABNT são pagas). Conferido em 2026-11-01; tabela revista em 2026-11-17. Fontes em `vigencia.md`.

Perfil **atual**: NBR 10520:2023 e NBR 6023:2025. Perfil **legado**: NBR 10520:2002 e NBR 6023:2018, usado quando o usuário confirma que o curso o exige (o manual da instituição sozinho não basta). No perfil legado, as palavras-chave seguem a NBR 6028:2003.

No `conferir_citacoes.py`, a coluna **legado** só vale com `--edicao-10520 2002`. Instituição que mistura edições (6023:2018 com 10520:2023, como a UFPR) usa a coluna **atual** no conferidor; a edição da 6023 só muda a lista exportada pela `biblioteca.py`. As linhas de NBR 14724 abaixo são para conferência manual.

A coluna **Script** diz se `conferir_citacoes.py` confere a regra. Quando a resposta é "não", confira à mão e **não** diga ao usuário que o script verificou.

| Regra | Perfil atual | Perfil legado | Script |
|---|---|---|---|
| Chamada sem referência na lista | erro | erro | sim |
| Referência na lista que nunca é citada, nem no texto nem em nota (decorativa) | aviso | aviso | sim |
| Primeira citação de uma obra em nota já na forma abreviada | aviso | aviso | sim |
| Nota que cita autor ausente da lista (`DELEUZE, 2018`) | aviso | aviso | sim |
| *Ibid.* ou *Id.* sem nota anterior com obra | aviso | aviso | sim |
| *Ibid.* em página diferente da nota a que se refere | aviso | aviso | não (o .docx não guarda a paginação final) |
| Sobrenome em caixa alta dentro dos parênteses | erro (sigla é aceita) | correto | sim |
| `s.p.`, `[s.p.]` ou `s/p` na chamada | erro | erro | sim |
| Mesmo autor e ano sem `a`/`b` | erro | erro | sim |
| `[s.d.]`, `s/d` ou referência sem ano | erro | erro | sim |
| `Disponível em: <URL>` com `< >` | erro | erro | sim |
| Mês por extenso em "Acesso em" (`10 janeiro 2024`) | erro | erro | sim |
| Mês abreviado errado em qualquer data (`mai. 2020`, `Jun. 2020`) | erro | erro | sim |
| Mês por extenso na data de publicação (`janeiro 2024`) | erro | erro | não |
| `Disponível em` sem `Acesso em` | erro | erro | sim |
| Grafia `et. al` em vez de `et al.` | erro | erro | sim |
| `Anais...` em vez de `Anais [...]` | erro | erro | sim |
| `doi:10.` em vez de `DOI: https://doi.org/10.` | erro | erro | sim |
| `[S.l.]` e `[s.n.]` sem espaço | erro | erro | sim |
| `[S. l.]: [s. n.]` em colchetes separados (o certo é `[S. l.: s. n.]`) | erro | erro | sim |
| Dia com zero à esquerda em "Acesso em" (`07 abr.`) | aviso | aviso | sim |
| Citação direta (entre aspas) sem localizador | aviso | aviso | sim |
| Ponto final dobrado: `." (Autor, ano).` | aviso | aceitar | sim |
| Mistura de et al. com lista de quatro ou mais autores | aviso | aviso | sim |
| Palavras-chave separadas por ponto (NBR 6028:2021) | erro | correto | sim |
| Palavra-chave com inicial maiúscula (pode ser nome próprio) | aviso | correto | sim |
| `et al.` sem itálico na chamada | aviso | aceitar | não |
| Citação longa com aspas ou recuo diferente do perfil | erro (aspas); aviso (recuo) | erro (recuo ≠ 4 cm) | não |
| Mistura de sistema numérico com autor-data | erro | erro | não |
| Ilustração ou tabela sem "Fonte:" (NBR 14724:2024) | erro | aviso | não |
| ISSN obrigatório em coleção de periódico | não exigir | exigir | não |
| Cidade obrigatória em evento | não exigir se ausente | exigir | não (o formatador já segue a regra) |
| Jurisprudência sem "julgado em" antes da data | aviso | aceitar | não |

Pontos sem confirmação nas fontes: itálico em "ca." na 6023:2025, notas abreviadas (Id., Ibid.) em maiúsculas e minúsculas, `In:` em itálico. Trate como aviso, nunca como erro.
