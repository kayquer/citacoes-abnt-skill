# NBR 10520:2023: citações

> Resumo com palavras próprias de guias públicos de bibliotecas (as normas ABNT são pagas). Conferido em 2026-11-01. Fontes em `vigencia.md`.

## 4. Regras práticas: citações (NBR 10520:2023)

### 4.1 Sistema autor-data

- **Autor no corpo da frase**: maiúsculas e minúsculas, com o ano (e a página) entre parênteses: `Segundo Silva (2009, p. 73), "..."`. Era assim também em 2002.
- **Autor dentro dos parênteses**: maiúsculas e minúsculas (nova regra): `(Silva, 2009, p. 73)`.
  - Perfil 2002 (legado): `(SILVA, 2009, p. 73)`.
  - O validador deve marcar caixa alta em chamada como erro no perfil 2023, a não ser que seja sigla.
- **Separadores dentro da chamada**: vírgula entre autor e ano e entre ano e página (`Autor, ano, p. N`).
- **Dois ou três autores**:
  - Nos parênteses, separados por `;`: `(Juliani; Cavaglieri; Machado, 2016, p. 69)`.
  - Na frase, separados por vírgula e "e": `Juliani, Cavaglieri e Machado (2016, p. 69)`. O exemplo da UFSCar usa só vírgulas, mas o "e" é a forma mais comum nos guias.
- **4 ou mais autores**: `Monteiro et al. (2008, p. 57)` ou `(Monteiro et al., 2008, p. 57)`, com *et al.* em itálico. Listar todos também é permitido. A escolha deve ser a mesma no documento inteiro.
- **Entidade**: nome por extenso em maiúsculas e minúsculas ou sigla em maiúsculas: `(Organização Mundial da Saúde, 2010, p. xi)`, `(IBGE, 2011, p. 3)`, `(Brasil, 2020)`.
- **Sem autoria (entrada pelo título)**: primeira palavra do título seguida de `[...]`, mais o ano: `(Cidade [...], 2002, 9min 41s)`. Se a primeira palavra for um artigo ou monossílabo, ela entra junto com a palavra seguinte.
- **Sem data**: usa-se a mesma data entre colchetes que está na referência: `(Silva, [2020?])`, `(Silva, [ca. 2015])`.
- **Mesmo autor, mesmo ano**: letras minúsculas logo após o ano, sem espaço: `(Passos, 2016a)`, `(Passos, 2016b)`. A mesma letra aparece na referência.
- **Mesmo autor, anos diferentes, na mesma chamada**: anos separados por vírgula: `Passos (2010, 2014, 2017)`, `(Passos; Souza, 2011, 2013, 2016)`.
- **Vários autores na mesma chamada**: obras separadas por `;`, em ordem alfabética: `(Cross, 1974; Knox, 1986; Mezirow, 1991)`.
- **Sobrenomes iguais com o mesmo ano**: acrescenta-se a inicial do prenome: `(Silva, C., 2016)` e `(Silva, H., 2015)`. Se as iniciais também forem iguais, o prenome vai por extenso: `(Silva, Cassio, 2016)`.
- **Página e localizador**:
  - Página: `p. 15`. Intervalo: `p. 214-215`. Folha: `f.`.
  - Livro: volume, tomo e seção antes da página (`v. 4, p. 463`).
  - E-book: `local. 264`.
  - Legislação: `cap. V, art. 49, inc. I`. Vídeo: `9min 41s`.
  - Não existe `s.p.` nem `[s.p.]`. Sem paginação, omite-se o localizador ou usa-se a divisão interna do documento.
  - Em citação **direta**, o localizador é obrigatório se existir. Em citação **indireta**, é opcional.
- **Citação de citação (apud)**: apud significa "citado por". Usa-se só quando não se teve acesso ao original.
  - `(Vianna, 1986, p. 172 apud Segatto, 1995, p. 214-215)`
  - `Slack (2002 apud Alves, 2004, p. 37)`
  - A obra consultada vai na lista de referências. A obra original pode ir em nota de rodapé.
  - O apud aparece sem itálico nos exemplos da UFSCar.
- **Ponto final**: depois da chamada, fechando a frase: `"... inevitável." (Silva, 2009, p. 73).` vira `"... inevitável" (Silva, 2009, p. 73).` A forma recomendada pelo IFCE e pela Unifor é a segunda, sem ponto dobrado.

### 4.2 Citação direta

- **Curta (até 3 linhas)**: no corpo do texto, entre **aspas duplas**. Aspas que já existiam no trecho citado viram **aspas simples**.
- **Longa (mais de 3 linhas)**:
  - Parágrafo destacado, com recuo padronizado da margem esquerda (**4 cm recomendado**, não obrigatório).
  - Fonte menor que a do texto (na prática, 10 ou 11 quando o texto está em 12).
  - Espaço simples, **sem aspas**.
  - A chamada fica no fim do bloco ou o autor é citado na frase que introduz o bloco.
- **Supressão**: `[...]` no início, no meio ou no fim do trecho.
- **Interpolação, acréscimo ou comentário**: entre colchetes `[ ]`.
- **Ênfase ou destaque**: negrito, itálico ou sublinhado, indicado depois do localizador:
  - `(Souto, 1993, p. 46, grifo nosso)` quando o destaque é do autor do trabalho;
  - `(Candido, 1993, p. 12, grifo do autor)` quando o destaque já estava no original. A UFSCar escreve "grifo próprio", então o validador deve aceitar as variantes.
- **Tradução feita pelo autor do trabalho**: `(Rahner, 1962, v. 4, p. 463, tradução nossa)`.
- **Obra traduzida ou reeditada**: a chamada usa o ano da edição consultada: `(Kant, 2015, p. 75)`.
  - A forma com o ano original entre colchetes, `(Kant, 2015 [1781], p. 75)`, é costume em filosofia e em clássicos, mas **não está na NBR 10520:2023**. Use só se o curso ou o orientador pedir, e no documento inteiro (`biblioteca.py citar <id> --ano-original`).
  - A paginação canônica (`B 75`, `A 51`) pode entrar como localizador: `(Kant, 2015, B 75)`.
- **Informação verbal**: `(informação verbal)` no texto, com os dados da fonte em nota de rodapé.
- **Trabalho em elaboração**: `(em fase de elaboração)` no texto, com os dados em nota.

### 4.3 Sistema numérico

- As fontes recebem números arábicos **únicos e consecutivos** no documento inteiro ou em cada parte. A numeração **não recomeça a cada página**.
- A chamada é sobrescrita (`...previvendo"¹`) ou vai entre parênteses (`(1)`). Com página: `(1, p. 30)`.
- A lista de referências segue a **ordem numérica crescente**.
- Uma fonte repetida mantém o mesmo número.
- Não se recomenda usar o sistema numérico junto com notas explicativas numeradas, porque as duas numerações se confundem. Use um sistema só no documento inteiro.

### 4.4 Notas de referência (rodapé)

- A primeira citação de uma obra em nota leva a **referência completa**. As seguintes podem ser abreviadas.
- Expressões latinas, todas em itálico, só em nota, de preferência na mesma página da nota a que se referem:
  - `Id.`: mesmo autor
  - `Ibid.`: mesma obra
  - `op. cit.`: obra citada
  - `loc. cit.`: lugar citado
  - `passim`: em várias passagens
  - `cf.`: confira
  - `et seq.`: seguinte
- Divergência: os exemplos de nota abreviada da UFSCar (2023) ainda usam a entrada em MAIÚSCULAS (`DURKHEIM, 1925, p. 176`). Não é seguro concluir se as notas abreviadas adotam maiúsculas e minúsculas como as chamadas. O validador deve aceitar as duas formas e só avisar.
- Formatação da nota: fonte menor, espaço simples, alinhada abaixo da primeira letra da primeira palavra a partir da segunda linha, sem linha em branco entre as notas, separada do texto por filete de 5 cm (NBR 14724).
