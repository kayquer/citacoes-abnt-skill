"""Gera o site do GitHub Pages (docs/) com SEO e GEO.

SEO: title/description por página, canonical, Open Graph, Twitter Card, sitemap, robots, HTML semântico.
GEO (motores generativos): JSON-LD (SoftwareSourceCode, Dataset, FAQPage, CollegeOrUniversity, BreadcrumbList),
respostas diretas no topo de cada página, data de atualização visível, fontes citadas, llms.txt e llms-full.txt.
"""
import html
import json

BASE = "https://kayquer.github.io/citacoes-abnt-skill/"
REPO = "https://github.com/kayquer/citacoes-abnt-skill"
DIST = REPO + "/raw/main/dist/"
AUTOR = {"@type": "Person", "name": "Kayque Rotondo", "url": "https://github.com/kayquer"}
ATUALIZADO = "2026-11-01"
ATUALIZADO_TXT = "1º de novembro de 2026"
NOME = "Citações ABNT para Claude"

CREDITOS = [
    ("PHY041/claude-skill-citation-checker", "https://github.com/PHY041/claude-skill-citation-checker",
     "ideia da verificação em várias bases e da detecção de citação quimérica"),
    ("K-Dense-AI/claude-scientific-writer (citation-management)",
     "https://github.com/K-Dense-AI/claude-scientific-writer/blob/main/.claude/skills/citation-management/SKILL.md",
     "metadado externo como dado não confiável, deduplicação e exportação"),
    ("viniciusvcgprofssional/claude-skills-academic", "https://github.com/viniciusvcgprofssional/claude-skills-academic",
     "classificação de referências pelo papel no texto e modelo Word ABNT"),
    ("ABNT Word Template Generator (MCP Market)", "https://mcpmarket.com/tools/skills/abnt-word-template-generator",
     "geração de modelo .docx/.dotx"),
    ("DevAlissu/pesquisador-br-skill", "https://github.com/DevAlissu/pesquisador-br-skill",
     "uma referência por norma, etapa bloqueante de integridade e DOI para ABNT"),
    ("carlosafjr-dev/abnt-academico-skill", "https://github.com/carlosafjr-dev/abnt-academico-skill",
     "quadro de normas vigentes e conferência citação × referência"),
]

NORMAS = [
    ("NBR 6023", "Referências", "2025 (3ª ed.)", "21/05/2025", "substitui a 2018; ISSN deixa de ser essencial em coleção de periódico; "
     "suplemento e número especial obrigatórios; e-localização em artigo online; cidade do evento só se houver; "
     "jurisprudência com \"julgado em\""),
    ("NBR 10520", "Citações", "2023", "07/2023", "autor em maiúsculas e minúsculas dentro dos parênteses: (Silva, 2020, p. 15); "
     "sigla continua em maiúsculas; não existe s.p.; et al. com quatro ou mais autores; recuo de 4 cm na citação longa vira "
     "recomendação; ponto final só depois da chamada"),
    ("NBR 14724", "Trabalhos acadêmicos", "2024 (4ª ed.)", "16/12/2024", "organização em seções, não em capítulos; verso da folha "
     "de rosto não é contado; fonte obrigatória em ilustrações e tabelas, inclusive \"elaborado pelo próprio autor\""),
    ("NBR 15287", "Projeto de pesquisa", "2025 (3ª ed.)", "18/03/2025", "revisão técnica; estrutura mantida"),
    ("NBR 6028", "Resumo", "2021", "05/2021", "palavras-chave separadas por ponto e vírgula e com inicial minúscula; "
     "150 a 500 palavras em trabalho acadêmico"),
    ("NBR 6024", "Numeração progressiva", "2012", "02/2012", "sem mudança; emenda em consulta nacional até 09/11/2026"),
    ("NBR 6027", "Sumário", "2012", "12/2012", "sem mudança; revisão em consulta nacional até 30/11/2026"),
    ("NBR 6022", "Artigo científico", "2018", "05/2018", "sem mudança; revisão em consulta nacional até 26/11/2026"),
    ("NBR 6034", "Índice", "2026", "09/2026", "substitui a 2004; mudanças ainda sem resumo público"),
    ("NBR 12225", "Lombada", "2023", "04/2023", "substitui a 2004"),
]

FAQ_INDEX = [
    ("O que é o Citações ABNT para Claude?",
     "É um plugin aberto (MIT) com três skills para o Claude Code: uma biblioteca de citações, um checador que detecta "
     "referência inventada ou com autoria trocada e um aplicador da ABNT (NBR 6023:2025, NBR 10520:2023 e NBR 14724:2024) "
     "com os perfis de formatação de 50 universidades e institutos brasileiros."),
    ("Como instalar no Claude Code?",
     "No Claude Code, rode /plugin marketplace add kayquer/citacoes-abnt-skill e depois "
     "/plugin install citacoes-abnt@citacoes-abnt-skill. Os scripts usam só Python 3 e a biblioteca padrão."),
    ("Como o checador descobre uma referência inventada por IA?",
     "Ele procura cada referência no Crossref, no OpenAlex, no Semantic Scholar, no Open Library e no Google Books. "
     "Só marca como verificada a obra encontrada em duas ou mais bases com título e autoria batendo. Título real com autores "
     "errados sai como quimera, e DOI que leva a outra obra sai como DOI divergente."),
    ("Qual edição da NBR 6023 está em vigor?",
     "A NBR 6023:2025 (3ª edição, publicada em 21 de maio de 2025), que substitui a de 2018. Muitos manuais de universidade "
     "ainda citam a 2018; o plugin formata nas duas e usa a que o perfil da instituição indicar."),
    ("O que mudou na NBR 10520:2023?",
     "A principal mudança: o sobrenome dentro dos parênteses passa a ser escrito em maiúsculas e minúsculas, como "
     "(Silva, 2020, p. 15), e não mais (SILVA, 2020, p. 15). Sigla continua em maiúsculas (IBGE, 2011). A forma s.p. deixou "
     "de existir e o ponto final vem só depois da chamada."),
    ("Quais universidades estão incluídas?",
     "40 universidades, entre elas USP, Unicamp, UFRJ, UFMG, UFRGS, UFSC, UnB e UNESP, e 10 instituições técnicas (institutos "
     "federais e Fatec). Cada perfil traz margens, fonte, espaçamento, recuo, paginação, sistema de chamada e o link do manual "
     "oficial consultado."),
    ("Funciona no ChatGPT, no Gemini e no Claude na web?",
     "Sim. No Claude.ai, envie os três arquivos .zip da pasta dist/claude-ai como Skills. No ChatGPT (GPT ou Projeto), "
     "no Gemini (Gem), no Copilot e no Perplexity, cole o arquivo instrucoes.txt nas instruções e anexe os dois arquivos de "
     "conhecimento. No Gemini CLI, instale como extensão; no Codex e em outros agentes compatíveis com Agent Skills, "
     "descompacte as skills em .agents/skills. A verificação de existência das referências precisa de busca na web ou dos scripts."),
    ("Funciona com notas de rodapé e livros de humanidades?",
     "Sim. A skill gera as notas de referência da NBR 10520: a primeira citação de cada obra completa e as seguintes "
     "abreviadas, com Ibid. e Id. opcionais. O conferidor lê as notas do Word e do Markdown. O formatador tem campos para "
     "tradução, organização da edição, capítulo nas obras completas do próprio autor, volume, artigo de jornal com data "
     "completa, e-localização e título atribuído entre colchetes."),
    ("Preciso do Claude para usar?",
     "Não. Os scripts de Python funcionam sozinhos: formatar referência, exportar para BibTeX, RIS ou CSL-JSON, checar "
     "existência das obras, conferir citação contra referência e gerar um modelo .docx com o perfil da instituição."),
]


def esc(t):
    return html.escape(str(t if t is not None else ""), quote=True)


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1c1a;--muted:#5f5b53;--line:#e4e0d6;--card:#ffffff;--accent:#1f5f4a;--accent-fg:#ffffff;--code:#f1eee6;--warn:#8a5a00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151614;--fg:#ecebe6;--muted:#a7a397;--line:#2c2e2a;--card:#1c1e1b;--accent:#6cc4a1;--accent-fg:#0d1a14;--code:#23251f;--warn:#e0b45a}}
:root[data-theme="dark"]{--bg:#151614;--fg:#ecebe6;--muted:#a7a397;--line:#2c2e2a;--card:#1c1e1b;--accent:#6cc4a1;--accent-fg:#0d1a14;--code:#23251f;--warn:#e0b45a}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}a:hover{text-decoration-thickness:2px}
.wrap{max-width:980px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line)}header.top .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px;padding-top:14px;padding-bottom:14px;flex-wrap:wrap}
.marca{font-weight:700;text-decoration:none;color:var(--fg)}nav a{margin-left:16px;font-size:15px}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;line-height:1.25;font-weight:700}
h1{font-size:clamp(28px,5vw,44px);margin:36px 0 12px}h2{font-size:26px;margin:48px 0 12px}h3{font-size:19px;margin:24px 0 8px}
.lead{font-size:19px;color:var(--muted);max-width:720px}
.resposta{border-left:4px solid var(--accent);background:var(--card);padding:14px 18px;margin:20px 0;border-radius:0 8px 8px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}.card h3{margin-top:0}
pre,code{font-family:ui-monospace,"Cascadia Code",Consolas,monospace;font-size:14px}
code{background:var(--code);padding:1px 5px;border-radius:4px}
pre{background:var(--code);padding:14px;border-radius:8px;overflow-x:auto;white-space:pre}
.tabela{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;background:var(--code)}tr:last-child td{border-bottom:0}
input[type=search]{width:100%;max-width:420px;font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);margin:8px 0 14px}
.selo{display:inline-block;font-size:13px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
.aviso{color:var(--warn)}.muted{color:var(--muted)}
.btn{display:inline-block;background:var(--accent);color:var(--accent-fg);padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600}
details{border-bottom:1px solid var(--line);padding:10px 0}summary{cursor:pointer;font-weight:600}
footer{margin-top:64px;border-top:1px solid var(--line);padding:24px 0 40px;font-size:14px;color:var(--muted)}
footer ul{padding-left:18px}
"""


def pagina(titulo, descricao, caminho, corpo, jsonld, tipo_og="website"):
    url = BASE + caminho
    blocos_ld = "\n".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    prefixo = "../" if "/" in caminho else ""
    creditos = "".join(f'<li><a href="{esc(u)}" rel="noopener">{esc(n)}</a>: {esc(d)}</li>' for n, u, d in CREDITOS)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descricao)}">
<meta name="author" content="Kayque Rotondo">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{esc(url)}">
<link rel="alternate" hreflang="pt-BR" href="{esc(url)}">
<meta name="theme-color" content="#1f5f4a">
<meta property="og:type" content="{tipo_og}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{NOME}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(descricao)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{BASE}og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Citações ABNT para Claude: biblioteca, checador e normas de 50 instituições">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(titulo)}">
<meta name="twitter:description" content="{esc(descricao)}">
<meta name="twitter:image" content="{BASE}og.png">
<meta property="article:modified_time" content="{ATUALIZADO}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%231f5f4a'/%3E%3Ctext x='32' y='44' font-family='Georgia' font-size='34' fill='white' text-anchor='middle'%3E%E2%80%9C%3C/text%3E%3C/svg%3E">
<link rel="alternate" type="text/plain" title="llms.txt" href="{BASE}llms.txt">
<style>{CSS}</style>
{blocos_ld}
</head>
<body>
<header class="top"><div class="wrap">
<a class="marca" href="{prefixo}index.html">“ {NOME}</a>
<nav aria-label="principal"><a href="{prefixo}index.html#instituicoes">Instituições</a><a href="{prefixo}normas-abnt-vigentes.html">Normas vigentes</a><a href="{REPO}">GitHub</a></nav>
</div></header>
<main class="wrap">
{corpo}
</main>
<footer><div class="wrap">
<p><strong>{NOME}</strong> · feito por <a href="https://github.com/kayquer">Kayque Rotondo</a> · licença <a href="{REPO}/blob/main/LICENSE">MIT</a> · atualizado em <time datetime="{ATUALIZADO}">{ATUALIZADO_TXT}</time>.</p>
<p>Atribuição: o projeto foi escrito do zero, inspirado nestas skills:</p>
<ul>{creditos}</ul>
<p>As normas ABNT são documentos pagos. Este site resume, com palavras próprias, guias públicos de bibliotecas universitárias e os manuais oficiais citados em cada página. Confira sempre o manual do seu programa. Sem vínculo com a ABNT nem com as instituições listadas.</p>
</div></footer>
</body>
</html>
"""


def _faq_ld(pares):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pares]}


def _faq_html(pares):
    return "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in pares)


def _cm(v):
    return f"{v:g}".replace(".", ",") + " cm"


def _margens(p):
    m = p["margens_cm"]
    return f"superior {_cm(m['sup'])}, esquerda {_cm(m['esq'])}, inferior {_cm(m['inf'])} e direita {_cm(m['dir'])}"


def _fonte(p):
    alt = p["fonte_alternativas"]
    return (" ou ".join(alt) if len(alt) > 1 else p["fonte_familia"]) + f" {p['fonte_pt']}"


def pagina_index(dados):
    linhas = []
    for i in dados:
        p = i["perfil"]
        linhas.append(
            f'<tr data-busca="{esc((i["nome"] + " " + i["sigla"] + " " + (i.get("uf") or "")).lower())}">'
            f'<td><a href="instituicoes/{i["id"]}.html">{esc(i["sigla"])}</a><br><span class="muted">{esc(i["nome"])}</span></td>'
            f'<td>{esc(i["tipo"])}</td><td>{esc(i["norma_csv"])}</td>'
            f'<td>{_cm(p["margens_cm"]["sup"])} / {_cm(p["margens_cm"]["esq"])} / {_cm(p["margens_cm"]["inf"])} / {_cm(p["margens_cm"]["dir"])}</td>'
            f'<td>{"sim" if i["tem_manual"] else "<span class=aviso>não encontrado</span>"}</td></tr>')
    total_manual = sum(1 for i in dados if i["tem_manual"])
    corpo = f"""
<h1>Citações e ABNT no Claude: biblioteca, checador de referências e normas de 50 instituições</h1>
<p class="lead">Plugin aberto para o Claude Code que organiza suas referências, detecta citação inventada por IA e aplica a ABNT vigente com as regras do manual da sua universidade.</p>
<div class="resposta"><strong>Resposta curta:</strong> instale com <code>/plugin marketplace add kayquer/citacoes-abnt-skill</code>.
O plugin formata referências pela NBR 6023:2025 (ou 2018), cita pela NBR 10520:2023, confere cada obra em cinco bases abertas e traz os perfis de {len(dados)} instituições ({total_manual} com manual oficial lido).</div>
<p><a class="btn" href="{REPO}">Ver no GitHub</a></p>

<h2 id="skills">O que o plugin faz</h2>
<div class="grid">
<div class="card"><h3>Biblioteca de citações</h3><p>Adiciona obras por DOI, ISBN ou URL, remove duplicatas, gera a chamada (Silva, 2020, p. 15) e exporta em ABNT, BibTeX, RIS ou CSL-JSON (Zotero, Mendeley, Pandoc).</p></div>
<div class="card"><h3>Checador de citações</h3><p>Procura cada referência no Crossref, OpenAlex, Semantic Scholar, Open Library e Google Books. Aponta referência inexistente, quimera (título real com autor errado), DOI de outra obra e citação sem referência.</p></div>
<div class="card"><h3>Aplicação da ABNT</h3><p>Aplica NBR 14724:2024, 10520:2023, 6023:2025, 6024, 6027 e 6028 com o perfil da instituição e gera um modelo .docx com margens, fonte, espaçamento e paginação já configurados.</p></div>
</div>

<h2 id="instalar">Instalar no Claude, ChatGPT, Gemini e outros</h2>
<p>As skills seguem o padrão aberto <a href="https://agentskills.io">Agent Skills</a>. Os arquivos ficam na pasta <a href="{REPO}/tree/main/dist"><code>dist/</code></a> do repositório.</p>
<div class="grid">
<div class="card"><h3>Claude Code</h3>
<pre>/plugin marketplace add kayquer/citacoes-abnt-skill
/plugin install citacoes-abnt@citacoes-abnt-skill</pre></div>
<div class="card"><h3>Claude na web e no app</h3>
<p>Baixe <a href="{DIST}claude-ai/checador-citacoes.zip">checador-citacoes.zip</a>, <a href="{DIST}claude-ai/biblioteca-citacoes.zip">biblioteca-citacoes.zip</a> e <a href="{DIST}claude-ai/abnt-formatacao.zip">abnt-formatacao.zip</a>. Envie cada um em <em>Configurações › Capacidades › Skills</em>, com a execução de código ativada.</p></div>
<div class="card"><h3>ChatGPT</h3>
<p>Crie um GPT ou um Projeto. Cole <a href="{DIST}chat/instrucoes.txt">instrucoes.txt</a> nas instruções e anexe <a href="{DIST}chat/conhecimento-instituicoes.md">conhecimento-instituicoes.md</a> e <a href="{DIST}chat/conhecimento-normas.md">conhecimento-normas.md</a>. Ative a busca na web, que é o que permite checar se as referências existem. Para formatar e conferir com os scripts, anexe também <a href="{DIST}chat/citacoes-abnt-scripts.zip">citacoes-abnt-scripts.zip</a> e ative a análise de código.</p></div>
<div class="card"><h3>Gemini</h3>
<p><strong>No navegador:</strong> crie um Gem, cole <a href="{DIST}chat/instrucoes.txt">instrucoes.txt</a> e anexe os dois arquivos de conhecimento. <strong>No Gemini CLI:</strong></p>
<pre>gemini extensions install https://github.com/kayquer/citacoes-abnt-skill</pre></div>
<div class="card"><h3>Hermes</h3>
<pre>hermes plugins install kayquer/citacoes-abnt-skill
hermes plugins enable citacoes-abnt</pre>
<p>O Hermes instala o plugin desativado; o segundo comando ativa. Como skill avulsa, descompacte <a href="{DIST}citacoes-abnt-skills.zip">citacoes-abnt-skills.zip</a> em <code>~/.hermes/skills/</code>.</p></div>
<div class="card"><h3>Codex, OpenClaw, OpenCode, Cursor, Copilot e outros agentes</h3>
<p>Descompacte <a href="{DIST}citacoes-abnt-skills.zip">citacoes-abnt-skills.zip</a> em <code>.agents/skills/</code> no projeto ou em <code>~/.agents/skills/</code>. O OpenClaw também lê <code>~/.openclaw/skills/</code>, e o OpenCode, <code>~/.config/opencode/skills/</code>. Codex, Copilot CLI e OpenClaw também instalam o repositório como plugin. Agente sem suporte a skills: salve <a href="{DIST}citacoes-abnt-agents.md">citacoes-abnt-agents.md</a> como <code>AGENTS.md</code>, <code>GEMINI.md</code> ou regra do Cursor.</p></div>
<div class="card"><h3>Copilot, Perplexity e outros chats</h3>
<p>Cole <a href="{DIST}chat/instrucoes.txt">instrucoes.txt</a> nas instruções do espaço ou do agente e anexe os arquivos de conhecimento. Sem busca na web, o assistente avisa que não conseguiu verificar as referências e não as dá como verificadas.</p></div>
</div>
<p>Depois peça, por exemplo: <em>“Confira se as referências deste TCC existem e formate tudo no padrão da UFMG.”</em></p>
<h3>Só os scripts (Python 3, sem dependências)</h3>
<pre>py -3 scripts/biblioteca.py adicionar --doi 10.1590/0102-4698214500
py -3 scripts/checar_referencias.py tcc.docx
py -3 scripts/conferir_citacoes.py tcc.docx
py -3 scripts/gerar_modelo_docx.py --instituicao usp --tipo tcc --saida modelo-usp.docx</pre>

<h2 id="instituicoes">Instituições e regras de formatação</h2>
<p>Margens na ordem superior / esquerda / inferior / direita. Clique na sigla para ver fonte, espaçamento, recuo, paginação, normas por área e o link do manual oficial.</p>
<label for="filtro" class="muted">Filtrar por nome, sigla ou UF</label><br>
<input type="search" id="filtro" placeholder="ex.: UFMG, Instituto Federal, SP" autocomplete="off">
<div class="tabela"><table id="tabela-inst">
<thead><tr><th>Instituição</th><th>Tipo</th><th>Norma principal</th><th>Margens</th><th>Manual</th></tr></thead>
<tbody>{''.join(linhas)}</tbody></table></div>

<h2 id="perguntas">Perguntas frequentes</h2>
{_faq_html(FAQ_INDEX)}

<h2 id="dados">Dados abertos</h2>
<p>Os perfis estão em <a href="{REPO}/blob/main/data/instituicoes.json">data/instituicoes.json</a> (licença MIT), com a URL do manual consultado e a data de conferência. Correções são bem-vindas por issue ou pull request.</p>
<script>
(function(){{var f=document.getElementById('filtro');if(!f)return;var rows=document.querySelectorAll('#tabela-inst tbody tr');
f.addEventListener('input',function(){{var q=f.value.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
rows.forEach(function(r){{var t=r.getAttribute('data-busca').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');r.hidden=q&&t.indexOf(q)<0;}});}});}})();
</script>
"""
    ld = [
        {"@context": "https://schema.org", "@type": "SoftwareSourceCode", "name": NOME,
         "alternateName": "citacoes-abnt-skill", "description": FAQ_INDEX[0][1], "codeRepository": REPO, "url": BASE,
         "programmingLanguage": "Python", "runtimePlatform": ["Claude Code", "Claude.ai", "ChatGPT", "Gemini", "Gemini CLI", "Codex", "Copilot CLI", "OpenCode", "OpenClaw", "Hermes"], "license": "https://opensource.org/licenses/MIT",
         "author": AUTOR, "dateModified": ATUALIZADO, "inLanguage": "pt-BR",
         "keywords": "ABNT, NBR 6023, NBR 10520, NBR 14724, citações, referências bibliográficas, TCC, checador de citações, Claude Code, skill",
         "isBasedOn": [u for _, u, _ in CREDITOS]},
        {"@context": "https://schema.org", "@type": "Dataset", "name": "Regras de formatação de trabalhos acadêmicos de 50 instituições brasileiras",
         "description": "Margens, fonte, espaçamento, recuo, paginação, sistema de chamada e edições das normas ABNT adotadas por 40 universidades e 10 instituições técnicas, com a URL do manual oficial consultado.",
         "url": BASE + "#instituicoes", "license": "https://opensource.org/licenses/MIT", "creator": AUTOR,
         "dateModified": ATUALIZADO, "inLanguage": "pt-BR", "spatialCoverage": {"@type": "Country", "name": "Brasil"},
         "isAccessibleForFree": True, "keywords": ["ABNT", "manual de normalização", "TCC", "universidades brasileiras"],
         "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                           "contentUrl": "https://raw.githubusercontent.com/kayquer/citacoes-abnt-skill/main/data/instituicoes.json"}]},
        {"@context": "https://schema.org", "@type": "WebSite", "name": NOME, "url": BASE, "inLanguage": "pt-BR", "author": AUTOR},
        _faq_ld(FAQ_INDEX),
    ]
    return pagina("Citações ABNT para Claude: checador de referências e normas de 50 universidades",
                  "Plugin aberto para o Claude Code: biblioteca de citações, checador de referência inventada e ABNT vigente "
                  "(NBR 6023:2025, 10520:2023, 14724:2024) com as regras de 50 universidades e institutos brasileiros.",
                  "index.html", corpo, ld)


def pagina_normas():
    linhas = "".join(f"<tr><td><strong>{esc(n)}</strong></td><td>{esc(a)}</td><td>{esc(e)}</td><td>{esc(d)}</td><td>{esc(m)}</td></tr>"
                     for n, a, e, d, m in NORMAS)
    faq = [
        ("Qual a norma ABNT de referências em vigor em 2026?",
         "A NBR 6023:2025, 3ª edição, publicada em 21 de maio de 2025. Ela substitui a NBR 6023:2018. Para livro, capítulo, "
         "artigo e tese, as duas edições quase não diferem."),
        ("Como fica a citação pela NBR 10520:2023?",
         "Dentro dos parênteses, o sobrenome vai em maiúsculas e minúsculas: (Silva, 2020, p. 15). Fora dos parênteses: "
         "Silva (2020, p. 15). Dois ou três autores: (Silva; Souza, 2020). Quatro ou mais: (Silva et al., 2020)."),
        ("A NBR 14724 mudou em 2024?",
         "Sim. A NBR 14724:2024 (4ª edição, de 16 de dezembro de 2024) substitui a de 2011. Margens, fonte 12 e entrelinha de "
         "1,5 continuam; o trabalho passa a ser dividido em seções, e a fonte de ilustrações e tabelas é obrigatória."),
        ("Posso usar [s.d.] quando a obra não tem data?",
         "Não. A NBR 6023 exige uma data. Use uma data provável entre colchetes: [2020?], [ca. 2015], [201-] ou [201-?]."),
    ]
    corpo = f"""
<h1>Normas ABNT vigentes em 2026: NBR 6023:2025, NBR 10520:2023 e NBR 14724:2024</h1>
<p class="lead">Quadro das edições em vigor e do que mudou, para quem escreve TCC, dissertação, tese ou artigo.</p>
<div class="resposta"><strong>Resposta curta:</strong> em novembro de 2026 valem a NBR 6023:2025 (referências), a NBR 10520:2023 (citações) e a NBR 14724:2024 (trabalhos acadêmicos). Muitos manuais de universidade ainda citam a NBR 6023:2018 e a NBR 14724:2011: siga o manual do seu programa e, na dúvida, pergunte à biblioteca.</div>
<div class="tabela"><table><thead><tr><th>Norma</th><th>Assunto</th><th>Edição vigente</th><th>Publicação</th><th>O que muda na prática</th></tr></thead>
<tbody>{linhas}</tbody></table></div>
<h2>Exemplos rápidos</h2>
<h3>Referência (NBR 6023)</h3>
<pre>FREIRE, Paulo. <strong>Pedagogia do oprimido</strong>. 17. ed. Rio de Janeiro: Paz e Terra, 1987.
LECUN, Yann; BENGIO, Yoshua; HINTON, Geoffrey. Deep learning. <strong>Nature</strong>, v. 521, n. 7553,
  p. 436-444, maio 2015. DOI: https://doi.org/10.1038/nature14539.</pre>
<h3>Citação (NBR 10520:2023)</h3>
<pre>(Freire, 1987, p. 45)      Freire (1987, p. 45)      (IBGE, 2023)
(Silva; Souza, 2020)       (Silva et al., 2020)      (Vianna, 1986 apud Segatto, 1995, p. 214)</pre>
<h2>Perguntas frequentes</h2>
{_faq_html(faq)}
<h2>Fontes</h2>
<p>Catálogo de normas Target (histórico de edições), folhas de rosto das normas e guias das bibliotecas da ECA-USP, UFU, UFSCar, UFV, UNESP, IFCE e Unifor, consultados em {ATUALIZADO_TXT}. As NBR 6022, 6024 e 6027 têm revisões em consulta nacional: este quadro será revisto no início de 2027.</p>
"""
    ld = [{"@context": "https://schema.org", "@type": "TechArticle", "headline": "Normas ABNT vigentes em 2026",
           "author": AUTOR, "dateModified": ATUALIZADO, "datePublished": ATUALIZADO, "inLanguage": "pt-BR",
           "about": [{"@type": "Thing", "name": f"ABNT {n}"} for n, *_ in NORMAS], "url": BASE + "normas-abnt-vigentes.html"},
          _faq_ld(faq),
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": NOME, "item": BASE},
              {"@type": "ListItem", "position": 2, "name": "Normas vigentes", "item": BASE + "normas-abnt-vigentes.html"}]}]
    return pagina("Normas ABNT vigentes em 2026: NBR 6023:2025, 10520:2023 e 14724:2024",
                  "Quais edições das normas ABNT valem em 2026 e o que mudou: referências (NBR 6023:2025), citações "
                  "(NBR 10520:2023), trabalhos acadêmicos (NBR 14724:2024), resumo, sumário e numeração.",
                  "normas-abnt-vigentes.html", corpo, ld, "article")


def pagina_instituicao(i):
    p = i["perfil"]
    man = i.get("manual") or {}
    o = p["origem"]

    def nota(campo):
        return "" if o.get(campo) == "manual" else ' <span class="selo">padrão ABNT</span>'

    faq = [
        (f"Quais são as margens exigidas pela {i['sigla']}?",
         f"{_margens(p).capitalize()}." + ("" if o["margens_cm"] == "manual" else
                                            " O manual consultado não especifica; vale o padrão da NBR 14724.")),
        (f"Qual fonte e espaçamento a {i['sigla']} pede?",
         f"{_fonte(p)}, com espaçamento {str(p['espacamento']).replace('.', ',')} no texto e fonte {p['fonte_menor_pt']} em "
         f"citação longa, nota e legenda." + ("" if o["fonte_familia"] == "manual" else
                                               " O manual não fixa a família da fonte; Arial ou Times New Roman é o costume.")),
        (f"Qual norma de citação a {i['sigla']} usa?",
         f"{i['norma_csv']}. Sistema de chamada: {p['sistema_chamada']}. Edições adotadas no perfil: NBR 6023:{p['edicao_6023']} "
         f"e NBR 10520:{p['edicao_10520']}."),
        (f"Onde está o manual oficial da {i['sigla']}?",
         (f"{man.get('titulo')} ({man.get('orgao') or ''} {man.get('ano') or ''}): {man['url']}" if man.get("url") else
          "Não encontramos manual público. Peça à biblioteca ou à coordenação o manual do curso.")),
    ]
    variacoes = "".join(f"<li>{esc(v.get('area'))}: {esc(v.get('norma'))}" +
                        (f' (<a href="{esc(v["fonte"])}" rel="noopener">fonte</a>)' if v.get("fonte") else "") + "</li>"
                        for v in i.get("variacoes_area") or [])
    partic = "".join(f"<li>{esc(x)}</li>" for x in i.get("particularidades") or [])
    modelos = "".join(f'<li>{esc(m.get("tipo"))}: <a href="{esc(m["url"])}" rel="noopener">{esc(m["url"])}</a></li>'
                      for m in i.get("modelos") or [] if m.get("url"))
    fontes = [man] + (i.get("fontes_extras") or [])
    fontes_html = "".join(f'<li><a href="{esc(f["url"])}" rel="noopener">{esc(f.get("titulo") or f["url"])}</a></li>'
                          for f in fontes if f and f.get("url"))
    aviso = ('<p class="aviso">O manual consultado cita edição anterior de alguma norma ABNT. Confirme com o programa se '
             'vale a edição antiga ou a vigente (NBR 6023:2025, 10520:2023, 14724:2024).</p>' if p["manual_desatualizado"] else "")
    sem_manual = ('' if i["tem_manual"] else '<p class="aviso">Não encontramos manual público desta instituição. '
                  'O perfil abaixo usa o padrão da ABNT; peça o manual do curso à biblioteca.</p>')
    corpo = f"""
<p class="muted"><a href="../index.html#instituicoes">Instituições</a> › {esc(i['sigla'])}</p>
<h1>Normas ABNT da {esc(i['sigla'])}: margens, fonte, citações e referências</h1>
<p class="lead">{esc(i['nome'])} · {esc(i['tipo'])}{(' · ' + esc(i['uf'])) if i.get('uf') else ''}</p>
<div class="resposta"><strong>Resposta curta:</strong> a {esc(i['sigla'])} segue {esc(i['norma_csv'])}. Margens: {esc(_margens(p))}. Fonte {esc(_fonte(p))}, espaçamento {str(p['espacamento']).replace('.', ',')}, recuo de parágrafo de {_cm(p['recuo_paragrafo_cm'])} e citação longa com recuo de {_cm(p['citacao_longa_recuo_cm'])}.</div>
{sem_manual}{aviso}
<h2>Perfil de formatação</h2>
<div class="tabela"><table><tbody>
<tr><th>Margens</th><td>{esc(_margens(p))}{nota('margens_cm')}</td></tr>
<tr><th>Fonte</th><td>{esc(_fonte(p))}; {p['fonte_menor_pt']} pt em citação longa, nota e legenda{nota('fonte_familia')}</td></tr>
<tr><th>Espaçamento</th><td>{str(p['espacamento']).replace('.', ',')}{nota('espacamento')}</td></tr>
<tr><th>Recuo de parágrafo</th><td>{_cm(p['recuo_paragrafo_cm'])}{nota('recuo_paragrafo_cm')}</td></tr>
<tr><th>Citação longa</th><td>recuo de {_cm(p['citacao_longa_recuo_cm'])}, fonte menor, espaço simples, sem aspas{nota('citacao_longa_recuo_cm')}</td></tr>
<tr><th>Paginação</th><td>{esc(p['paginacao'])}{nota('paginacao')}</td></tr>
<tr><th>Sistema de chamada</th><td>{esc(p['sistema_chamada'])}{nota('sistema_chamada')}</td></tr>
<tr><th>Edições das normas</th><td>NBR 6023:{p['edicao_6023']}{nota('edicao_6023')} · NBR 10520:{p['edicao_10520']}{nota('edicao_10520')} · NBR 14724:{p['edicao_14724']}{nota('edicao_14724')}</td></tr>
<tr><th>Fomento à pesquisa</th><td>{esc(', '.join(i.get('fomento') or [])) or '—'}</td></tr>
</tbody></table></div>
<p class="muted"><span class="selo">padrão ABNT</span> indica que o manual consultado não especifica aquele item.</p>
{('<h2>Outras normas por área</h2><ul>' + variacoes + '</ul>') if variacoes else ''}
{('<h2>Particularidades</h2><ul>' + partic + '</ul>') if partic else ''}
{('<h2>Modelos oficiais</h2><ul>' + modelos + '</ul>') if modelos else ''}
<h2>Como aplicar com o Claude</h2>
<pre>Formate as referências deste trabalho no padrão da {esc(i['sigla'])}.
py -3 scripts/gerar_modelo_docx.py --instituicao {esc(i['id'])} --tipo tcc --saida modelo-{esc(i['id'])}.docx</pre>
<h2>Perguntas frequentes</h2>
{_faq_html(faq)}
<h2>Fontes</h2>
<ul>{fontes_html or '<li>Planilha de origem do projeto; nenhum manual público encontrado.</li>'}</ul>
<p class="muted">Conferido em {esc(i['conferido_em'])}. {esc(i.get('observacoes') or '')}</p>
"""
    org = {"@type": "CollegeOrUniversity", "name": i["nome"], "alternateName": i["sigla"]}
    if i.get("uf"):
        org["address"] = {"@type": "PostalAddress", "addressRegion": i["uf"], "addressCountry": "BR"}
    ld = [{"@context": "https://schema.org", "@type": "WebPage", "name": f"Normas ABNT da {i['sigla']}",
           "url": f"{BASE}instituicoes/{i['id']}.html", "inLanguage": "pt-BR", "dateModified": ATUALIZADO,
           "author": AUTOR, "about": org, **({"citation": man["url"]} if man.get("url") else {})},
          _faq_ld(faq),
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": NOME, "item": BASE},
              {"@type": "ListItem", "position": 2, "name": "Instituições", "item": BASE + "#instituicoes"},
              {"@type": "ListItem", "position": 3, "name": i["sigla"], "item": f"{BASE}instituicoes/{i['id']}.html"}]}]
    desc = (f"Regras de formatação da {i['sigla']} ({i['nome']}): margens {_margens(i['perfil'])}, fonte {_fonte(p)}, "
            f"espaçamento, citações e referências ABNT, com link do manual oficial.")
    return pagina(f"Normas ABNT da {i['sigla']} (2026): margens, fonte, citações e referências", desc[:300],
                  f"instituicoes/{i['id']}.html", corpo, ld, "article")


def llms_txt(dados):
    linhas = [f"# {NOME}", "",
              "> Plugin aberto (MIT) para o Claude Code com três skills: biblioteca de citações, checador de referências "
              "(detecta referência inventada, quimérica e DOI divergente em Crossref, OpenAlex, Semantic Scholar, Open Library "
              "e Google Books) e aplicação da ABNT vigente (NBR 6023:2025, NBR 10520:2023, NBR 14724:2024) com perfis de "
              f"formatação de {len(dados)} instituições brasileiras. Autor: Kayque Rotondo. Atualizado em {ATUALIZADO}.", "",
              "## Páginas", "",
              f"- [Página inicial]({BASE}index.html): o que o plugin faz, instalação e tabela das instituições",
              f"- [Normas ABNT vigentes em 2026]({BASE}normas-abnt-vigentes.html): edições em vigor e o que mudou",
              f"- [Repositório]({REPO}): código, SKILL.md e dados",
              f"- [Dados em JSON](https://raw.githubusercontent.com/kayquer/citacoes-abnt-skill/main/data/instituicoes.json)",
              f"- [Texto completo para LLMs]({BASE}llms-full.txt)",
              f"- [Instruções para ChatGPT, Gemini e outros chats]({DIST}chat/instrucoes.txt)",
              f"- [Skills autocontidas para .agents/skills]({DIST}citacoes-abnt-skills.zip)", "", "## Instituições", ""]
    for i in dados:
        p = i["perfil"]
        linhas.append(f"- [{i['sigla']}]({BASE}instituicoes/{i['id']}.html): {i['nome']}; {i['norma_csv']}; margens "
                      f"{p['margens_cm']['sup']:g}/{p['margens_cm']['esq']:g}/{p['margens_cm']['inf']:g}/{p['margens_cm']['dir']:g} cm; "
                      f"{_fonte(p)}")
    return "\n".join(linhas) + "\n"


def llms_full(dados, perfis_md):
    partes = [llms_txt(dados), "\n## Normas vigentes\n"]
    partes += [f"- {n} ({a}): {e}, publicada em {d}. {m}." for n, a, e, d, m in NORMAS]
    partes.append("\n## Perguntas frequentes\n")
    partes += [f"### {q}\n{a}\n" for q, a in FAQ_INDEX]
    partes.append("\n## Perfis das instituições\n")
    partes += perfis_md
    return "\n".join(partes) + "\n"


def sitemap(caminhos):
    urls = "".join(f"<url><loc>{BASE}{c}</loc><lastmod>{ATUALIZADO}</lastmod></url>\n" for c in caminhos)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'


ROBOTS = f"""User-agent: *
Allow: /

# Motores generativos e assistentes são bem-vindos
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Google-Extended
Allow: /

Sitemap: {BASE}sitemap.xml
"""

PAGINA_404 = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Página não encontrada</title><meta name="robots" content="noindex"><style>body{font:17px/1.6 system-ui,sans-serif;max-width:640px;margin:15vh auto;padding:0 16px;background:#fbfaf7;color:#1d1c1a}a{color:#1f5f4a}@media (prefers-color-scheme:dark){body{background:#151614;color:#ecebe6}a{color:#6cc4a1}}</style></head>
<body><h1>Página não encontrada</h1><p><a href="/citacoes-abnt-skill/">Voltar para Citações ABNT para Claude</a></p></body></html>
"""


def gerar_site(dados, raiz, perfil_md):
    docs = raiz / "docs"
    saidas = {docs / "index.html": pagina_index(dados), docs / "normas-abnt-vigentes.html": pagina_normas(),
              docs / "robots.txt": ROBOTS, docs / ".nojekyll": "", docs / "404.html": PAGINA_404}
    caminhos = ["index.html", "normas-abnt-vigentes.html"]
    for i in dados:
        saidas[docs / "instituicoes" / f"{i['id']}.html"] = pagina_instituicao(i)
        caminhos.append(f"instituicoes/{i['id']}.html")
    saidas[docs / "sitemap.xml"] = sitemap(caminhos)
    saidas[docs / "llms.txt"] = llms_txt(dados)
    saidas[docs / "llms-full.txt"] = llms_full(dados, [perfil_md(i) for i in dados])
    return saidas
