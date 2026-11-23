# -*- coding: utf-8 -*-
"""Gera docs/Guia_Completo_A2.pdf: guia de execucao + gabarito do Trabalho A2."""
import csv, re, sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image, PageBreak, KeepTogether, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents

# Uso: python scripts/gerar_guia_pdf.py   (requer: pip install reportlab)
RAIZ = Path(__file__).resolve().parent.parent
SHOTS = RAIZ / "docs" / "img"
SAIDA = RAIZ / "docs" / "Guia_Completo_A2.pdf"

F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Arial", F + r"\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-B", F + r"\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-I", F + r"\ariali.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BI", F + r"\arialbi.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + r"\consola.ttf"))
pdfmetrics.registerFont(TTFont("Mono-B", F + r"\consolab.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Arial", normal="Arial", bold="Arial-B", italic="Arial-I", boldItalic="Arial-BI")
registerFontFamily("Mono", normal="Mono", bold="Mono-B", italic="Mono", boldItalic="Mono-B")

# ---------------- paleta ----------------
AZUL = colors.HexColor("#1f4e9c"); AZUL_CL = colors.HexColor("#e8eef9")
VERDE = colors.HexColor("#1b7a4b"); VERDE_CL = colors.HexColor("#e6f4ec")
LARANJA = colors.HexColor("#b26a00"); LARANJA_CL = colors.HexColor("#fdf3e3")
VERM = colors.HexColor("#b3261e"); VERM_CL = colors.HexColor("#fbe9e8")
CINZA = colors.HexColor("#5f6673"); CINZA_CL = colors.HexColor("#f3f4f6"); BORDA = colors.HexColor("#d5d9e0")
CODE_BG = colors.HexColor("#1e2230")

# ---------------- estilos ----------------
S = {}
S["body"] = ParagraphStyle("body", fontName="Arial", fontSize=9.6, leading=13.6, spaceAfter=5, textColor=colors.HexColor("#1d2330"))
S["small"] = ParagraphStyle("small", parent=S["body"], fontSize=8.4, leading=11.2, spaceAfter=2)
S["cell"] = ParagraphStyle("cell", parent=S["body"], fontSize=8.4, leading=11, spaceAfter=0)
S["cellh"] = ParagraphStyle("cellh", parent=S["cell"], fontName="Arial-B", textColor=colors.white)
S["h1"] = ParagraphStyle("h1", fontName="Arial-B", fontSize=19, leading=23, textColor=AZUL, spaceBefore=4, spaceAfter=10)
S["h2"] = ParagraphStyle("h2", fontName="Arial-B", fontSize=13.2, leading=17, textColor=AZUL, spaceBefore=12, spaceAfter=6)
S["h3"] = ParagraphStyle("h3", fontName="Arial-B", fontSize=10.8, leading=14, textColor=colors.HexColor("#1d2330"), spaceBefore=8, spaceAfter=4)
S["code"] = ParagraphStyle("code", fontName="Mono", fontSize=8, leading=10.6, textColor=colors.HexColor("#e6e9ef"))
S["bul"] = ParagraphStyle("bul", parent=S["body"], leftIndent=14, bulletIndent=4, spaceAfter=2.5)
S["q"] = ParagraphStyle("q", parent=S["body"], fontName="Arial-B", textColor=AZUL, spaceBefore=6, spaceAfter=2)
S["toc1"] = ParagraphStyle("toc1", fontName="Arial-B", fontSize=10.5, leading=17, leftIndent=0)
S["toc2"] = ParagraphStyle("toc2", fontName="Arial", fontSize=9.4, leading=13.5, leftIndent=16, textColor=CINZA)

story = []

def H1(t): story.append(Paragraph(t, S["h1"]))
def H2(t): story.append(CondPageBreak(4.5 * cm)); story.append(Paragraph(t, S["h2"]))
def H3(t): story.append(CondPageBreak(3.5 * cm)); story.append(Paragraph(t, S["h3"]))
def P(t, st="body"): story.append(Paragraph(t, S[st]))
def SP(h=6): story.append(Spacer(1, h))
def BR(): story.append(PageBreak())
def C(t): return f'<font face="Mono" color="#b3261e">{esc(t)}</font>'

def BUL(itens):
    for i in itens:
        story.append(Paragraph(i, S["bul"], bulletText="•"))

def CODE(texto, titulo=None):
    linhas = esc(texto.strip("\n")).replace(" ", "&nbsp;").split("\n")
    html = "<br/>".join(linhas)
    # comentarios em cinza, prompts em verde
    html = re.sub(r"(#&nbsp;[^<]*)", r'<font color="#8b93a7">\1</font>', html)
    conteudo = [Paragraph(html, S["code"])]
    t = Table([[conteudo]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                           ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    if titulo:
        story.append(Paragraph(f'<font color="#5f6673" size="8">{titulo}</font>', S["small"]))
    story.append(t); SP(6)

def NOTA(texto, tipo="info", titulo=None):
    cor, fundo = {"info": (AZUL, AZUL_CL), "ok": (VERDE, VERDE_CL), "warn": (LARANJA, LARANJA_CL),
                  "bad": (VERM, VERM_CL)}[tipo]
    conteudo = (f'<font face="Arial-B" color="{cor.hexval()}">{titulo}</font><br/>' if titulo else "") + texto
    t = Table([[Paragraph(conteudo, S["body"])]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fundo),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.2, cor),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t); SP(7)

def TAB(linhas, larguras, alinhar_dir=(), destaque=None):
    """linhas[0] = cabecalho. destaque = {indice_linha: cor_fundo}."""
    dados = []
    for i, l in enumerate(linhas):
        st = S["cellh"] if i == 0 else S["cell"]
        dados.append([c if not isinstance(c, str) else Paragraph(c, st) for c in l])
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1)
    estilo = [("BACKGROUND", (0, 0), (-1, 0), AZUL),
              ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CL]),
              ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
              ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    for (r, cor) in (destaque or {}).items():
        estilo.append(("BACKGROUND", (0, r), (-1, r), cor))
    t.setStyle(TableStyle(estilo))
    story.append(t); SP(8)

def IMG(caminho, largura_cm, legenda=None, max_alt_cm=None):
    p = Path(caminho)
    if not p.exists():
        NOTA(f"Imagem não encontrada: {esc(str(p))}", "warn"); return
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(p)).getSize()
    lw = largura_cm * cm; lh = lw * h / w
    if max_alt_cm and lh > max_alt_cm * cm:
        lh = max_alt_cm * cm; lw = lh * w / h
    img = Image(str(p), width=lw, height=lh)
    bloco = [img]
    if legenda:
        bloco.append(Paragraph(f'<font color="#5f6673" size="8"><i>{legenda}</i></font>',
                               ParagraphStyle("leg", parent=S["small"], alignment=TA_CENTER, spaceBefore=3)))
    story.append(KeepTogether(bloco)); SP(8)

def QA(pergunta, resposta):
    story.append(KeepTogether([Paragraph(pergunta, S["q"]), Paragraph(resposta, S["body"])]))

# ---------------- dados reais ----------------
medias = {}
with open(RAIZ / "results" / "resumo_medio.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        medias[(r["cenario"], r["variante"], int(r["vus"]))] = r

def m(c, v, u, campo, d=2):
    r = medias.get((c, v, u))
    if not r or r[campo] in ("", None): return "-"
    x = float(r[campo])
    s = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s

def ler(rel):
    p = RAIZ / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None

# ======================================================================
# CAPA
# ======================================================================
story.append(Spacer(1, 3.2 * cm))
story.append(Paragraph("Trabalho Prático A2", ParagraphStyle("c0", fontName="Arial", fontSize=13, textColor=CINZA, alignment=TA_CENTER)))
SP(10)
story.append(Paragraph("Otimização de Web Services<br/>por meio de Cache, Consultas<br/>e Testes de Desempenho",
                       ParagraphStyle("c1", fontName="Arial-B", fontSize=26, leading=33, textColor=AZUL, alignment=TA_CENTER)))
SP(18)
story.append(Paragraph("Guia completo: o que o projeto faz, como rodar no terminal e na página,<br/>e gabarito item a item do enunciado",
                       ParagraphStyle("c2", fontName="Arial", fontSize=12.5, leading=18, textColor=colors.HexColor("#1d2330"), alignment=TA_CENTER)))
SP(40)
capa = Table([[Paragraph("<b>Disciplina</b>", S["cell"]), Paragraph("Análise e Otimização de Sistemas — Universidade Veiga de Almeida", S["cell"])],
              [Paragraph("<b>Professor</b>", S["cell"]), Paragraph("André Lucio", S["cell"])],
              [Paragraph("<b>Stack</b>", S["cell"]), Paragraph("Java 21 · Spring Boot 3.5 · JPA/Hibernate · PostgreSQL 16 · Redis 7 · k6 · Docker", S["cell"])],
              [Paragraph("<b>Volume de dados</b>", S["cell"]), Paragraph("300.000 pedidos · 1.050.000 itens · 20.000 clientes · 2.000 produtos · 20 categorias", S["cell"])],
              [Paragraph("<b>Pasta do projeto</b>", S["cell"]), Paragraph(C("a2-otimizacao/"), S["cell"])]],
             colWidths=[4 * cm, 12 * cm])
capa.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, BORDA), ("BACKGROUND", (0, 0), (0, -1), AZUL_CL),
                          ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                          ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
story.append(capa)
SP(40)
story.append(Paragraph("Todos os números deste documento foram medidos no próprio projeto (pasta <b>results/</b> "
                       "e execuções ao vivo). Nenhum valor é estimado.",
                       ParagraphStyle("c3", parent=S["small"], alignment=TA_CENTER, textColor=CINZA)))
BR()

# ======================================================================
# SUMARIO
# ======================================================================
H1("Sumário")
toc = TableOfContents()
toc.levelStyles = [S["toc1"], S["toc2"]]
toc.dotsMinLevel = 0
story.append(toc)
BR()

# ======================================================================
# PARTE 1 - VISAO GERAL
# ======================================================================
H1("1. Visão geral do projeto")
P("O projeto é uma <b>API REST de um sistema de vendas</b>. Ele não existe para vender nada: existe para "
  "<b>medir experimentalmente</b> o efeito de três técnicas de otimização sobre um banco grande. "
  "Cada técnica foi implementada em versões alternativas (sem / com otimização), lado a lado, "
  "para que a única variável entre duas medições seja a técnica.")

H2("1.1 A ideia em uma tabela")
TAB([["Técnica", "Problema que ataca", "O que reduz", "Melhor resultado medido"],
     ["<b>Cache (Redis)</b>", "Ler do banco o mesmo dado repetidas vezes", "Nº de requisições que <b>chegam ao banco</b>",
      "2ª leitura com <b>0 SQL</b>; p95 sob 200 usuários 290 → 47 ms (6,2×)"],
     ["<b>Estratégia de consulta</b>", "N+1: 1 consulta para a lista + 1 por item", "Nº de <b>SQL por requisição</b>",
      "271 → 2 consultas (−99,3%); 1.127 → 22 ms"],
     ["<b>Índice</b>", "Seq Scan: ler 300 mil linhas para achar 15", "<b>Custo de cada SQL</b>",
      "19,13 → 0,257 ms (74×) na consulta-alvo"]],
    [3.2, 4.4, 4.0, 5.4])
NOTA("As três técnicas atacam <b>níveis diferentes</b> do mesmo caminho, por isso <b>se somam</b> em vez de competir: "
     "o cache evita a ida ao banco; a estratégia de consulta decide quantas idas; o índice decide quanto custa cada ida.",
     "info", "Por que três técnicas e não uma?")

H2("1.2 Arquitetura: o caminho de uma requisição")
CODE("""
  navegador / curl / Postman / k6
        |
        v
  [ DiagnosticoFilter ]   <- mede o tempo e conta os SQL da requisição
        |                    e devolve os headers X-Query-Count / X-Response-Time-Ms / X-Cache
        v
  [ Controller ] --> [ Service ] ----------> [ Redis ]     TÉCNICA 1: se está no cache,
        |                 |                   (cache)      termina aqui: 0 SQL
        |                 | (cache MISS)
        |                 v
        |          [ Repository / JPA ]                    TÉCNICA 2: a estratégia decide
        |                 |                                QUANTOS SQL são emitidos
        |                 v
        |          [ datasource-proxy ]   <- intercepta e conta cada SQL
        |                 v
        +----------> [ PostgreSQL ]                        TÉCNICA 3: o índice decide o
                                                           custo de CADA SQL
""", "Diagrama: camadas da aplicação e onde cada técnica atua")

H2("1.3 Tecnologias e por que foram escolhidas")
TAB([["Tecnologia", "Papel", "Justificativa"],
     ["Java 21 + Spring Boot 3.5", "Web Services REST", "Recomendado no enunciado; Spring Cache e Spring Data JPA prontos"],
     ["JPA / Hibernate", "Persistência (ORM)", "Oferece LAZY/EAGER, JOIN FETCH, @EntityGraph, @BatchSize — tudo o que o item 2 compara"],
     ["PostgreSQL 16", "Banco relacional", "EXPLAIN ANALYZE detalhado; json_agg para a variante SQL nativo"],
     ["Redis 7", "Cache", "Externo à aplicação (sobrevive a restart e é compartilhado entre instâncias), TTL nativo por chave, inspecionável com redis-cli"],
     ["datasource-proxy", "Contador de SQL", "Intercepta o JDBC: conta todo SQL, inclusive os gerados pelo Hibernate"],
     ["Grafana k6", "Teste de carga", "Scripts em JavaScript, p95/p99 nativos, exporta JSON, baixo overhead"],
     ["Docker Compose", "Infraestrutura", "Postgres e Redis com CPU/memória limitadas: medições comparáveis entre rodadas"],
     ["Python (pandas, matplotlib)", "Relatórios", "Consolida os JSON do k6 em CSV, gráficos e no painel HTML"]],
    [4.0, 3.4, 9.6])

H2("1.4 Modelo de dados")
CODE("""
  categoria 1 ---- N produto
                        |
                        | N
  cliente 1 ---- N pedido 1 ---- N item_pedido
""")
TAB([["Tabela", "Registros", "Papel no experimento"],
     ["categoria", "20", "Baixa volatilidade → cache com TTL longo (10 min)"],
     ["produto", "2.000", "Preço/estoque voláteis → cache com TTL curto (60 s) + invalidação"],
     ["cliente", "20.000", "Filtro da consulta-alvo do índice"],
     ["pedido", "300.000", "Tabela principal: um Seq Scan aqui custa caro"],
     ["item_pedido", "1.050.000", "Coleção que provoca o N+1"]],
    [3.2, 2.6, 11.2], alinhar_dir=(1,))
P("Os dados são gerados por " + C("db/02-seed.sql") + " com " + C("setseed(0.42)") +
  ": a geração é <b>determinística</b>, então qualquer pessoa que rode o projeto obtém exatamente os mesmos dados. "
  "A tabela " + C("pedido") + " nasce <b>sem índice</b> em " + C("cliente_id") + "/" + C("data_pedido") +
  " de propósito: o PostgreSQL não indexa chaves estrangeiras automaticamente, e era preciso o estado “antes” para medir o ganho.")

H2("1.5 Estrutura de pastas")
CODE("""
a2-otimizacao/
├── docker-compose.yml        Postgres 16 + Redis 7, com CPU/memória limitadas
├── db/                       schema, seed determinístico, criar/remover índice
├── app/src/main/java/br/uva/aos/
│   ├── diag/                 contador de SQL, status do cache, filtro dos headers X-
│   ├── entity/lazy|eager|batch/   as MESMAS tabelas mapeadas de 3 formas
│   ├── repository/           JPQL, JOIN FETCH, EntityGraph, projeção DTO, SQL nativo
│   ├── service/              regras + @Cacheable / @CacheEvict
│   ├── controller/           um endpoint por técnica
│   └── config/               CacheConfig (TTL por cache), WebConfig (CORS do painel)
├── k6/                       3 cenários de carga
├── scripts/                  experimentos, runner de carga, gráficos, painel, demo do vídeo
├── results/                  saídas das execuções (evidências)
├── docs/                     painel HTML, roteiro do vídeo, este PDF, gráficos
└── postman/                  coleção com as requisições prontas
""")

H2("1.6 Como cada número é comprovado")
P("Toda resposta da API carrega três headers, escritos pelo " + C("DiagnosticoFilter") + ":")
TAB([["Header", "Significado", "Exemplo"],
     [C("X-Query-Count"), "Quantos comandos SQL aquela requisição executou", "271 (LAZY) · 2 (JOIN FETCH) · 0 (cache HIT)"],
     [C("X-Response-Time-Ms"), "Tempo medido no servidor, sem latência de rede", "22,4"],
     [C("X-Cache"), "HIT (veio do Redis), MISS (foi ao banco) ou BYPASS (endpoint sem cache)", "HIT"]],
    [4.0, 7.6, 5.4])
NOTA("O contador fica em uma variável " + C("ThreadLocal") + ". No Spring MVC cada requisição é atendida por uma thread, "
     "então cada SQL é atribuído à requisição que o disparou — mesmo com 200 usuários simultâneos.",
     "info", "Por que o contador não mistura requisições?")
BR()

# ======================================================================
# PARTE 2 - COMO RODAR
# ======================================================================
H1("2. Como rodar o projeto")
H2("2.1 Pré-requisitos")
TAB([["Ferramenta", "Para quê", "Instalação (Windows)"],
     ["Docker Desktop", "Postgres e Redis", "docker.com — precisa estar aberto"],
     ["JDK 21", "Rodar a API", C("winget install Microsoft.OpenJDK.21")],
     ["Git Bash", "Rodar os scripts .sh", "Vem com o Git for Windows"],
     ["k6", "Testes de carga (opcional)", C("winget install GrafanaLabs.k6")],
     ["Python + pandas/matplotlib", "Gráficos e painel (opcional)", C("pip install pandas matplotlib")]],
    [3.8, 4.2, 9.0])
P("<b>Maven não é necessário</b>: o projeto usa o wrapper " + C("mvnw") + ", que baixa o Maven sozinho.")

H2("2.2 Passo a passo")
NOTA("Os scripts " + C(".sh") + " devem ser rodados no <b>Git Bash</b>. No PowerShell, o comando " + C("bash") +
     " abre o bash do WSL e falha com <i>execvpe(/bin/bash) failed</i>. No VS Code: seta ao lado do <b>+</b> do terminal → "
     "<b>Git Bash</b>. Alternativa no PowerShell: " + C('& "C:\\Program Files\\Git\\bin\\bash.exe" scripts/...'),
     "warn", "Importante: use o Git Bash")
CODE("""
# 1. entrar na pasta do projeto
cd "/c/Users/<voce>/Downloads/Trabalho A2/a2-otimizacao"

# 2. subir Postgres + Redis (na 1a vez cria as tabelas e gera 1,4 milhão de linhas)
docker compose up -d --wait

# 3. subir a API (compila, sobe em segundo plano e espera ficar pronta)
bash scripts/app-restart.sh
#   >> aplicacao PRONTA

# 4. conferir
curl -s http://localhost:8080/api/admin/stats
#   {"categoria":20,"produto":2000,"cliente":20000,"pedido":300000,
#    "item_pedido":1050000,"indicesPedido":[...]}
""", "Terminal Git Bash")

H2("2.3 Onde a aplicação “aparece”")
TAB([["Parte", "Onde roda", "Como ver"],
     ["Postgres e Redis", "Containers Docker", "Docker Desktop: a2-postgres e a2-redis"],
     ["API Java", "Processo java.exe em segundo plano (fora do Docker)",
      "Navegador em http://localhost:8080/api/admin/stats · log em results/app.log"],
     ["Painel", "Arquivo estático docs/dashboard.html", "Dois cliques no arquivo; não precisa de servidor"]],
    [3.2, 5.8, 8.0])
P("Para ver os logs ao vivo no terminal (em vez de segundo plano), no <b>PowerShell</b>:")
CODE("""
cd app
$env:JAVA_HOME = "C:\\Program Files\\Microsoft\\jdk-21.0.13.102-hotspot"
.\\mvnw.cmd spring-boot:run          # pronto quando aparecer "Started A2OtimizacaoApplication"
                                     # Ctrl+C para parar
""", "PowerShell (alternativa)")

H2("2.4 Problemas comuns")
TAB([["Sintoma", "Causa", "Solução"],
     ["execvpe(/bin/bash) failed", "Rodou bash no PowerShell (abre o WSL)", "Use o terminal Git Bash"],
     ["porta 8080 ainda ocupada", "Uma instância antiga da API ainda roda", "bash scripts/app-restart.sh já a encerra (corrigido); ou feche o java.exe"],
     ["'mvnw.cmd' não é reconhecido", "Windows sem busca no diretório atual", "Corrigido nos scripts (.\\mvnw.cmd)"],
     ["Painel: “Sem conexão com a API”", "API não está no ar", "bash scripts/app-restart.sh e clicar em Reconectar"],
     ["Painel: “headers X- ocultos”", "API antiga, sem o CORS do WebConfig", "Reiniciar a API"],
     ["java -version mostra 1.8", "Java 8 está no PATH", "Normal: o script usa o JDK 21 via JAVA_HOME"],
     ["k6: command not found", "k6 fora do PATH", "Usar \"/c/Program Files/k6/k6.exe\" (o demo-video.sh já usa)"]],
    [4.4, 5.2, 7.4])
BR()

# ======================================================================
# PARTE 3 - TERMINAL
# ======================================================================
H1("3. Como funciona no terminal")
P("Há dois jeitos de demonstrar pelo terminal: comandos avulsos com " + C("curl") +
  " ou o script guiado " + C("scripts/demo-video.sh") + ", que segue o roteiro do vídeo.")

H2("3.1 Script guiado: demo-video.sh")
CODE("""
bash scripts/demo-video.sh        # roteiro inteiro, para no fim de cada passo
bash scripts/demo-video.sh 4      # recomeça a partir do bloco 4
""")
P("Cada comando aparece em azul antes de rodar e o script espera <b>Enter</b> entre os passos — ninguém precisa digitar durante a gravação.")
TAB([["Bloco", "O que mostra", "O que observar"],
     ["1", "Volume de dados", "300.000 pedidos e índices existentes"],
     ["2", "Headers de diagnóstico", "X-Query-Count: 1 · X-Cache: BYPASS"],
     ["3", "Cache: MISS → HIT → PUT → MISS", "HIT com <b>X-Query-Count: 0</b>; após o PUT, TTL = −2 (chave removida) e preço novo"],
     ["4", "N+1 no LAZY", "Consultas crescem com o limite: 55 → 525 → 2.156"],
     ["5", "Todas as estratégias (limite=100)", "LAZY 525 · EAGER 201 · otimizadas <b>2</b>"],
     ["6", "EXPLAIN sem e com índice", "Seq Scan + Sort (~15 ms) → Index Scan (~0,5 ms)"],
     ["7", "k6 ao vivo, 50 usuários, 15 s", "p95 e throughput sem cache × com cache"]],
    [1.3, 5.2, 10.5])

H2("3.2 Comandos avulsos e saídas reais")
H3("Cache: MISS, HIT e invalidação")
CODE("""
curl -s -X DELETE http://localhost:8080/api/admin/cache          # cache frio
curl -si http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"
#   X-Query-Count: 1    X-Cache: MISS     <- foi ao banco
curl -si http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"
#   X-Query-Count: 0    X-Cache: HIT      <- o banco NÃO foi tocado

docker exec a2-redis redis-cli GET "produtos::10"   # o JSON gravado no Redis
docker exec a2-redis redis-cli TTL "produtos::10"   # 59  (segundos restantes)

curl -s -X PUT http://localhost:8080/api/produtos/10 \\
     -H "Content-Type: application/json" -d '{"preco":418.84,"estoque":7}'
docker exec a2-redis redis-cli TTL "produtos::10"   # -2  = chave removida (@CacheEvict)
""")
H3("N+1: contagem de SQL por estratégia (limite=50)")
CODE("""
for e in lazy eager batch dto nativo join-fetch entity-graph lazy-sem-acesso; do
  printf "%-16s " $e; curl -si "http://localhost:8080/api/pedidos/$e?limite=50" | grep -i x-query-count
done
#   lazy             X-Query-Count: 271
#   eager            X-Query-Count: 101
#   batch            X-Query-Count: 5
#   dto              X-Query-Count: 2
#   nativo           X-Query-Count: 2
#   join-fetch       X-Query-Count: 2
#   entity-graph     X-Query-Count: 2
#   lazy-sem-acesso  X-Query-Count: 1
""")
H3("Índice: EXPLAIN ANALYZE")
CODE("""
docker exec -i a2-postgres psql -U a2 -d vendas -q < db/11-drop-index.sql    # remove
docker exec -i a2-postgres psql -U a2 -d vendas -c "EXPLAIN ANALYZE
  SELECT * FROM pedido WHERE cliente_id=150 ORDER BY data_pedido DESC LIMIT 50;"
#   -> Sort  ... Sort Key: data_pedido DESC
#      -> Parallel Seq Scan on pedido ... Rows Removed by Filter: 99996
#   Execution Time: 15.518 ms

docker exec -i a2-postgres psql -U a2 -d vendas -q < db/10-create-index.sql  # cria
#   -> Index Scan using idx_pedido_cliente_data on pedido
#   Execution Time: 0.576 ms        (o nó Sort desapareceu)
""")

H2("3.3 Scripts de experimento (geram as evidências em results/)")
TAB([["Script", "Item", "Gera"],
     [C("experimento-cache.sh"), "3.4", "results/cache/experimento.txt — os 5 passos obrigatórios, com TTL de 10 s"],
     [C("experimento-cache-sem-invalidacao.sh"), "3.4", "results/cache/sem-invalidacao.txt — o risco de NÃO invalidar"],
     [C("experimento-custo-miss.sh"), "3.5", "results/cache/custo-miss.txt — custo do MISS, medido de forma determinística"],
     [C("coletar-queries.sh"), "4.3", "results/queries.txt — X-Query-Count por estratégia e limite"],
     [C("explain-antes-depois.sh"), "5.2/5.3", "results/indices/ — EXPLAIN antes/depois, 5 execuções cada"],
     [C("run-all-tests.sh"), "6", "results/k6/ e resumo.csv — bateria k6 completa (~1 h)"],
     [C("gerar_graficos.py"), "6.6", "results/resumo*.csv e docs/img/*.png"],
     [C("gerar_dashboard.py"), "—", "docs/dashboard.html"]],
    [5.6, 1.5, 9.9])
BR()

# ======================================================================
# PARTE 4 - PAGINA
# ======================================================================
H1("4. Como funciona na página (painel)")
P("O arquivo " + C("docs/dashboard.html") + " é uma página única, sem servidor e sem build: basta abrir no navegador. "
  "Ela é <b>gerada</b> por " + C("scripts/gerar_dashboard.py") + " a partir de " + C("results/") +
  " — para alterar a página, edite o gerador e rode " + C("python scripts/gerar_dashboard.py") + ".")
TAB([["Aba", "Conteúdo"],
     ["Visão geral", "KPIs calculados dos resultados reais + volume de dados"],
     ["<b>Teste ao vivo</b>", "<b>Botões que chamam a API real</b> e mostram X-Query-Count, tempo e X-Cache na tela"],
     ["Como funciona", "Caminho de uma requisição e onde cada técnica atua"],
     ["1. Cache", "Ciclo HIT/MISS/invalidação, TTL por volatilidade, gráfico sob carga"],
     ["2a. LAZY vs EAGER", "SQL por requisição e por que o N+1 ocorre"],
     ["2b. Consultas otimizadas", "As 5 estratégias e seus trade-offs"],
     ["2c. Índices", "EXPLAIN antes/depois e a tabela de nós do plano"],
     ["3. Testes de carga", "Gráficos interativos (métrica e cenário selecionáveis, escala log)"],
     ["O que muda o desempenho", "Cada parâmetro ajustável e o efeito esperado"]],
    [4.4, 12.6])

H2("4.1 A aba “Teste ao vivo”")
P("Exige a API no ar. O indicador no topo fica verde (“API online · 300.000 pedidos”). Cada bloco tem um botão principal azul que roda o experimento inteiro, com pausas para narrar.")
TAB([["Bloco", "Botão principal", "O que aparece"],
     ["1. Cache", "Rodar o ciclo completo", "Cartões coloridos: Limpar → MISS (1 SQL, laranja) → <b>HIT (0 SQL, verde)</b> → HIT → PUT novo preço → MISS com preço novo → HIT → estatísticas (hit ratio)"],
     ["2. N+1", "Comparar todas as estratégias", "Barras de SQL e de tempo: LAZY 271 (vermelho) até EntityGraph 2 (verde), com a frase de conclusão. Botão extra: LAZY com limite 10 → 100 → 500"],
     ["3. Índice", "Comparar sem índice x com índice", "Remove o índice, roda EXPLAIN, recria, roda de novo. Planos lado a lado: Seq Scan/Sort em vermelho, Index Scan em verde; KPI de ganho (~70–170×)"],
     ["4. Mini carga", "Rodar comparação", "Consultas ao banco (ex.: 2.809 → 50), hit ratio (~98%), throughput e p95"]],
    [2.2, 4.4, 10.4])
NOTA("O navegador abre no máximo <b>6 conexões</b> por servidor. Com tão pouca carga o banco não fica sob pressão e a latência quase não muda "
     "(≈1,2×) — exatamente o que o k6 mediu com 10 usuários (1,5×). O número que importa ali é <b>consultas ao banco evitadas</b>. "
     "Os ganhos grandes de latência (6,2× com 200 usuários) estão na aba <b>3. Testes de carga</b>, medidos com k6.",
     "warn", "Sobre o mini teste de carga")
for nome, leg in [("pdf_aovivo_1.png", "Aba Teste ao vivo — ciclo do cache e comparação das estratégias (execução real)"),
                  ("pdf_aovivo_2.png", "Aba Teste ao vivo — EXPLAIN sem/com índice e mini teste de carga (execução real)")]:
    IMG(SHOTS / nome, 16.5, leg, max_alt_cm=21)

H2("4.2 O que mudou no código para a aba funcionar")
TAB([["Arquivo", "Mudança"],
     [C("config/WebConfig.java"), "Libera CORS e <b>expõe</b> os headers X-Query-Count, X-Response-Time-Ms e X-Cache (sem isso o JavaScript não os enxerga)"],
     [C("controller/AdminController.java"), "POST /api/admin/indices/{criar|remover} e GET /api/admin/explain (roda 2× e descarta a 1ª)"],
     [C("scripts/gerar_dashboard.py"), "A aba nova (HTML, CSS e JavaScript)"]],
    [5.6, 11.4])
H2("4.3 Postman")
P("A coleção " + C("postman/A2.postman_collection.json") + " (22 requisições, organizadas por item) pode ser importada no Postman "
  "(<i>Import → arquivo</i>). Os headers X- aparecem na aba <b>Headers</b> da resposta.")
BR()

# ======================================================================
# PARTE 5 - GABARITO
# ======================================================================
H1("5. Gabarito do trabalho (item a item)")
P("Para cada exigência do enunciado: <b>como foi atendida</b>, <b>onde está a evidência</b> e a <b>resposta</b> às perguntas obrigatórias.")

H2("5.1 Requisitos gerais da aplicação (seção 2)")
TAB([["Exigência", "Atendido", "Como / onde"],
     ["Web Services REST", '<font color="#1b7a4b"><b>Sim</b></font>', "Controllers em app/.../controller/ — ver lista de endpoints no Apêndice A"],
     ["Banco relacional", '<font color="#1b7a4b"><b>Sim</b></font>', "PostgreSQL 16 (docker-compose.yml)"],
     ["≥ 3 tabelas relacionadas", '<font color="#1b7a4b"><b>Sim</b></font>', "5 tabelas: categoria, produto, cliente, pedido, item_pedido (db/01-schema.sql)"],
     ["Endpoints de consulta", '<font color="#1b7a4b"><b>Sim</b></font>', "/api/produtos, /api/categorias, /api/pedidos/*, /api/clientes/{id}/pedidos"],
     ["≥ 1 operação de atualização", '<font color="#1b7a4b"><b>Sim</b></font>', "PUT /api/produtos/{id} (altera preço/estoque e invalida o cache)"],
     ["Estratégias alternativas", '<font color="#1b7a4b"><b>Sim</b></font>', "8 variantes de consulta, cache on/off, índice on/off"],
     ["Volume grande (≥ 10.000)", '<font color="#1b7a4b"><b>Sim</b></font>', "300.000 pedidos e 1.050.000 itens, seed determinístico"]],
    [4.4, 1.8, 10.8])

# ---------------- ITEM 1 ----------------
H2("5.2 ITEM 1 — Cache")
H3("3.1 Identificação das informações cacheáveis")
TAB([["Critério", "Detalhe do produto", "Lista de categorias"],
     ["Frequência de acesso", "Muito alta (toda vitrine/carrinho)", "Alta (menus, filtros)"],
     ["Volatilidade", "Média: preço e estoque mudam", "Baixíssima"],
     ["Custo de recuperação", "JOIN produto × categoria", "Varredura da tabela"],
     ["Consequência de dado velho", "<b>Grave</b>: preço errado, vender sem estoque", "Baixa: nome de categoria desatualizado"],
     ["Invalidação", "<b>@CacheEvict</b> no PUT + TTL 60 s", "Somente TTL 10 min"]],
    [4.2, 6.4, 6.4])
P("<b>Justificativa:</b> o TTL é o <b>tamanho máximo da janela de inconsistência</b>. Categoria quase nunca muda, então 10 minutos é seguro. "
  "Preço muda e errar custa dinheiro, então 60 s <b>e</b> invalidação explícita a cada escrita.")
H3("3.2 As duas versões")
TAB([["Cenário", "Endpoint", "Comportamento"],
     ["A — sem cache", C("GET /api/produtos/{id}/sem-cache"), "Sempre consulta o banco (X-Cache: BYPASS, 1 SQL)"],
     ["B — com cache", C("GET /api/produtos/{id}/com-cache"), "Procura no Redis; HIT devolve sem SQL; MISS lê do banco e grava no Redis"],
     ["Categorias", C("GET /api/categorias/sem-cache · /com-cache"), "Mesmo par, TTL de 10 min"]],
    [3.0, 6.6, 7.4])
P("Padrão usado: <b>cache-aside</b> com Spring Cache (" + C("@Cacheable") + "/" + C("@CacheEvict") + ") em " + C("service/") +
  "; TTL por cache em " + C("config/CacheConfig.java") + ".")
H3("3.3 Tecnologia: Redis")
P("Redis é um armazenamento chave-valor em memória, externo à aplicação. Escolhido porque: (1) <b>sobrevive a restart</b> da API e é "
  "<b>compartilhado</b> entre várias instâncias — um cache local (Caffeine) teria uma cópia por instância, cada uma com sua própria "
  "janela de inconsistência; (2) tem <b>TTL nativo por chave</b>; (3) permite inspecionar o conteúdo (" + C("redis-cli GET/TTL") +
  "), o que torna a demonstração verificável; (4) " + C("maxmemory 256mb + allkeys-lru") + " limita a memória com descarte automático. "
  "Custo: uma ida à rede a mais que um cache em memória local.")

H3("3.4 Experimento obrigatório (TTL e invalidação)")
exp = ler("results/cache/experimento.txt")
if exp:
    def trecho(txt, ini, n=8):
        i = txt.find(ini)
        if i < 0: return ""
        bloco = txt[i:].split("\n")[:n]
        return "\n".join(l for l in bloco if l.strip())
    linhas = []
    for l in exp.split("\n"):
        l = l.rstrip("\r")
        if re.match(r"^(===|---|X-Query-Count|X-Cache|TTL|KEYS|\{\"id\"|Nova consulta|Valor em cache|\{\"hits)", l):
            linhas.append(l if len(l) < 118 else l[:115] + "...")
    CODE("\n".join(linhas), "Extrato real de results/cache/experimento.txt (TTL de 10 s para caber na demonstração)")
else:
    NOTA("results/cache/experimento.txt não encontrado — rode scripts/experimento-cache.sh", "warn")
TAB([["Passo do enunciado", "Resultado observado"],
     ["1. Consultar e registrar o cache", "X-Cache: MISS, X-Query-Count: 1 — foi ao banco e gravou no Redis"],
     ["2. Repetir — houve reaproveitamento?", "<b>Sim</b>: X-Cache: HIT, <b>X-Query-Count: 0</b>"],
     ["3. Modificar pela aplicação", "PUT /api/produtos/10 → @CacheEvict remove a chave (TTL = −2)"],
     ["4. Consultar de novo — está atualizado?", "<b>Sim</b>: MISS, 1 SQL, devolve o preço novo"],
     ["5. Demonstrar expiração", "Após o TTL, a chave some sozinha (TTL = −2, KEYS vazio) e a próxima leitura é MISS"]],
    [6.0, 11.0])
seminv = ler("results/cache/sem-invalidacao.txt")
if seminv:
    linhas = [l.rstrip("\r") for l in seminv.split("\n")
              if l.strip() and not re.match(r"^(HTTP|Content|Transfer|Date|Keep|Connection|Vary|Access|=====|FIM)", l.strip())]
    linhas = [l if len(l) < 118 else l[:115] + "..." for l in linhas][:34]
    CODE("\n".join(linhas), "Extrato real de results/cache/sem-invalidacao.txt (profile cache-sem-invalidacao)")
NOTA("Com o profile " + C("cache-sem-invalidacao") + " o PUT grava no banco mas <b>não</b> remove a chave: as leituras seguintes "
     "devolvem o <b>preço antigo</b> até o TTL expirar. É a janela de inconsistência na prática.", "bad", "O risco de não invalidar (demonstrado)")
NOTA("<b>@CachePut</b> gravaria no cache o valor que a aplicação <i>supõe</i> ter salvo. Com trigger, valor default ou escrita "
     "concorrente, o cache serviria um valor que nunca existiu no banco. <b>@CacheEvict</b> apaga, e a próxima leitura reconstrói "
     "a partir da fonte da verdade. Custo: um MISS a mais. Benefício: o cache nunca mente.", "info", "Por que @CacheEvict e não @CachePut")

H3("3.5 Análise de desempenho do cache")
TAB([["Usuários", "p95 sem cache", "p95 com cache", "Ganho p95", "Throughput sem → com", "Erros sem / com"],
     *[[str(v), m("cache", "sem-cache", v, "latencia_p95_ms") + " ms", m("cache", "com-cache-quente", v, "latencia_p95_ms") + " ms",
        f'{float(medias[("cache","sem-cache",v)]["latencia_p95_ms"]) / float(medias[("cache","com-cache-quente",v)]["latencia_p95_ms"]):.1f}×'.replace(".", ","),
        m("cache", "sem-cache", v, "throughput_req_s", 0) + " → " + m("cache", "com-cache-quente", v, "throughput_req_s", 0) + " req/s",
        m("cache", "sem-cache", v, "taxa_erro_pct") + "% / " + m("cache", "com-cache-quente", v, "taxa_erro_pct") + "%"]
       for v in (10, 50, 100, 200)]],
    [1.8, 2.6, 2.6, 2.1, 4.8, 3.1])
miss = ler("results/cache/custo-miss.txt")
if miss:
    i = miss.find("variante")
    linhas = [l.rstrip("\r") for l in miss[i:].split("\n") if l.strip()]
    CODE("\n".join(l if len(l) < 118 else l[:115] + "..." for l in linhas), "Extrato real de results/cache/custo-miss.txt")
IMG(RAIZ / "docs/img/cache_p95.png", 13, "Latência p95 por nível de carga — cache (k6, média de 3 repetições)")

QA("Em quais situações o cache apresentou maior benefício?",
   "Com <b>alta concorrência e alto reaproveitamento</b> das mesmas chaves. O ganho no p95 <b>cresce com a carga</b>: 1,5× com 10 usuários, "
   "4,1× com 50, 4,4× com 100 e <b>6,2× com 200</b> (290 → 47 ms); o throughput sobe 3,3× (1.966 → 6.502 req/s). Com pouca carga o banco "
   "dá conta sozinho e evitar a consulta economiza pouco; sob pressão, cada consulta evitada libera conexão do pool e CPU do Postgres.")
QA("Como a volatilidade dos dados influenciou a escolha do TTL?",
   "O TTL foi tratado como a <b>janela máxima aceitável de dado desatualizado</b>. Categoria (baixíssima volatilidade, erro barato) ficou com "
   "10 min. Produto (preço/estoque voláteis, erro caro) ficou com 60 s <b>mais</b> invalidação explícita no PUT — o TTL vira apenas a rede de "
   "segurança para alterações feitas fora da aplicação.")
QA("Quais são os riscos de utilizar informações desatualizadas?",
   "Vender pelo preço antigo, aceitar pedido sem estoque, exibir dados contraditórios entre telas. Demonstrado em "
   "<i>results/cache/sem-invalidacao.txt</i>: sem invalidação, a leitura devolve o preço antigo até o TTL expirar. Outros riscos: escrita "
   "concorrente gravando no cache um valor que não está no banco (evitado com @CacheEvict) e alterações diretas no banco, que nenhuma "
   "invalidação da aplicação enxerga (cobertas apenas pelo TTL).")
QA("O cache sempre melhorou o desempenho? Justifique.",
   "<b>Não.</b> (1) O <b>MISS é mais caro</b> que não ter cache: são três idas (Redis + banco + Redis) contra uma. Medido em "
   "<i>custo-miss.txt</i> (mediana de 60 requisições): sem cache 8,5 ms; <b>MISS 15,7 ms</b>; HIT 5,9 ms. Cada MISS precisa ser "
   "seguido de <b>~3 HITs</b> para o cache compensar. (2) Com <b>baixa carga</b> o ganho é pequeno (1,5× com 10 usuários). (3) O cache só ajuda dados <b>relidos</b>: "
   "chave lida uma vez paga o MISS e ocupa memória. (4) Acrescenta complexidade e um modo de falha novo — o primeiro bug do projeto foi um "
   "cache que nunca cacheava (self-invocation: método da mesma classe não passa pelo proxy do @Cacheable), sem nenhum erro no log.")
NOTA("A variante chamada inicialmente “cache frio” mediu <b>98,5% de hit ratio</b>: com 2.000 IDs e ~2.300 req/s o cache aquece em 0,86 s de "
     "uma rodada de 25 s. Ela foi renomeada para <i>com-cache-espalhado</i>, e o custo do MISS passou a ser medido de forma determinística "
     "(cache limpo antes de <b>cada</b> requisição). Lição: rótulo de variante não é prova; o hit ratio é.", "warn", "Correção de método (vale citar na apresentação)")
BR()

# ---------------- ITEM 2 ----------------
H2("5.3 ITEM 2 — Otimização de consultas")
P("As mesmas tabelas foram mapeadas três vezes (" + C("entity/lazy") + ", " + C("entity/eager") + ", " + C("entity/batch") +
  "), porque no JPA o " + C("FetchType") + " faz parte do <b>mapeamento</b>: uma classe não pode ser LAZY num endpoint e EAGER em outro. "
  "As entidades são " + C("@Immutable") + " (existem só para o experimento).")
H3("4.1 / 4.2 LAZY, EAGER e o N+1 observado")
CODE("""
1  SELECT * FROM pedido ORDER BY id LIMIT 50          <- a "1"
+  SELECT * FROM cliente     WHERE id = ?        x50   <- os "N"
+  SELECT * FROM item_pedido WHERE pedido_id = ? x50
+  SELECT * FROM produto     WHERE id = ?        x...
= 271 consultas para listar 50 pedidos (LAZY acessando os relacionamentos)
""", "O que o LAZY dispara ao percorrer cliente, itens e produtos")
TAB([["Endpoint", "limite=10", "limite=50", "limite=100", "limite=500", "Comportamento"],
     ["/lazy", "55", "271", "525", "2.156", "<b>N+1</b>: cresce com o limite"],
     ["/eager", "—", "101", "201", "—", "<b>Também N+1</b>, e pago sempre"],
     ["/lazy-sem-acesso", "1", "1", "1", "1 (até 1.000)", "Nada é tocado → 1 consulta"]],
    [3.2, 1.8, 1.8, 1.9, 2.3, 6.0])
NOTA("Em JPQL sem fetch explícito, o Hibernate busca os pedidos e depois resolve cada coleção EAGER com uma consulta por pedido. "
     "A diferença para o LAZY é que o custo é pago <b>sempre</b>, mesmo quando o endpoint não usa os relacionamentos. "
     "Isso confirma o alerta do enunciado: a comparação precisa ser feita pelo comportamento <b>observado</b> (X-Query-Count), não pela anotação.",
     "bad", "Achado: EAGER não resolve o N+1")
H3("4.3 Comparação das estratégias (limite=50, medição pontual)")
TAB([["Estratégia", "SQL / requisição", "Tempo no servidor", "Comportamento"],
     ["LAZY com acesso", "<b>271</b>", "1.127 ms", "cresce com o limite → N+1"],
     ["EAGER", "<b>101</b>", "255 ms", "também N+1, pago sempre"],
     ["@BatchSize(100)", "5", "163 ms", "1 + N/size (arredondado para cima)"],
     ["SQL nativo (json_agg)", "2", "100 ms", "constante"],
     ["Projeção DTO", "2", "219 ms", "constante"],
     ["JOIN FETCH", "2", "26 ms", "constante"],
     ["@EntityGraph", "2", "<b>22 ms</b>", "constante"],
     ["LAZY sem acesso", "1", "8 ms", "nada é tocado"]],
    [4.4, 3.0, 3.4, 6.2])
IMG(RAIZ / "docs/img/persistencia_p95.png", 13, "Latência p95 por estratégia sob carga (k6, limite=20, 5 a 50 usuários)")
QA("Volume de informações recuperadas e efeitos do carregamento desnecessário",
   "O EAGER traz cliente e itens mesmo para quem só precisa do cabeçalho do pedido — mais linhas, mais objetos na memória, mais tempo "
   "de conexão ocupada. O " + C("/lazy-sem-acesso") + " mostra o oposto: 1 consulta para 1.000 pedidos, porque nada além do necessário foi lido.")
QA("Quando LAZY ou EAGER são mais adequados?",
   "<b>LAZY é o bom padrão</b>: só paga o que usa. O erro não é o LAZY, é <b>percorrer relacionamentos sem planejar como carregá-los</b>. "
   "EAGER só faz sentido em associações <i>to-one</i> pequenas, sempre necessárias. Para telas que precisam dos relacionamentos, o certo é "
   "decidir <b>por consulta</b> (JOIN FETCH / EntityGraph), não no mapeamento.")
H3("4.4 Otimização implementada (cinco alternativas)")
TAB([["Estratégia", "Como funciona", "Quando preferir"],
     ["JOIN FETCH", "Uma consulta com join", "Caso geral"],
     ["@EntityGraph", "Mesmo plano, declarado por atributos", "Reaproveitar a query variando o que carregar"],
     ["@BatchSize", "Agrupa proxies em WHERE id IN (...)", "Várias coleções: evita produto cartesiano"],
     ["Projeção DTO", "Colunas soltas, sem entidades gerenciadas", "Telas somente leitura"],
     ["SQL nativo (json_agg)", "O banco monta o array de itens", "Quando o gargalo medido é o volume trafegado"]],
    [3.6, 6.4, 7.0])
NOTA("Com JOIN FETCH de coleção, um pedido vira N linhas; aplicar LIMIT direto cortaria pedidos ao meio. O Hibernate detecta e pagina "
     "<b>em memória</b> (aviso HHH90003004), anulando o ganho. Solução em " + C("PedidoOtimizadoRepository") +
     ": <b>1)</b> buscar só os IDs da página; <b>2)</b> fazer o JOIN FETCH por esses IDs. Por isso as otimizadas fazem <b>2</b> consultas, não 1.",
     "info", "Armadilha: paginação com JOIN FETCH")
QA("Resultado: original × otimizada",
   "LAZY → EntityGraph: <b>271 → 2 consultas (−99,3%)</b> e <b>1.127 → 22 ms (51× mais rápido)</b>, mesmo DTO, mesmo resultado. "
   "Sob carga (limite=20, 50 usuários): throughput LAZY " + m("persistencia", "lazy", 50, "throughput_req_s", 0) +
   " req/s × EntityGraph " + m("persistencia", "entity-graph", 50, "throughput_req_s", 0) + " req/s; p95 " +
   m("persistencia", "lazy", 50, "latencia_p95_ms", 0) + " ms × " + m("persistencia", "entity-graph", 50, "latencia_p95_ms", 0) + " ms.")
QA("O SQL nativo trouxe benefício real? Quais as consequências?",
   "<b>Não de forma relevante.</b> Em número de SQL empata com JOIN FETCH/EntityGraph (2 consultas). Em tempo, ficou atrás do EntityGraph "
   "na medição pontual (100 × 22 ms) e equivalente sob carga (p95 " + m("persistencia", "nativo", 50, "latencia_p95_ms", 0) + " × " +
   m("persistencia", "entity-graph", 50, "latencia_p95_ms", 0) + " ms com 50 usuários). Sua vantagem teórica é trafegar menos dados "
   "(não repete o pedido em cada linha de item). <b>Custos:</b> perde portabilidade (" + C("json_agg") + " é só PostgreSQL), não há "
   "verificação em tempo de compilação, renomear uma coluna deixa de ser refatoração automática e o mapeamento JSON → DTO é manual. "
   "Conclusão: usar apenas quando o gargalo <b>medido</b> for o volume trafegado.")
BR()

H2("5.4 ITEM 2 — Índices")
H3("5.1 Consultas selecionadas")
CODE("""
-- Consulta-alvo 1: filtro por igualdade + ordenação
SELECT * FROM pedido WHERE cliente_id = 150 ORDER BY data_pedido DESC LIMIT 50;
CREATE INDEX idx_pedido_cliente_data ON pedido (cliente_id, data_pedido DESC);

-- Consulta-alvo 2: busca por intervalo + filtro
SELECT * FROM pedido WHERE data_pedido BETWEEN ? AND ? AND status = ?;
CREATE INDEX idx_pedido_data_status ON pedido (data_pedido, status);
""")
H3("5.2 Sem índice × com índice (EXPLAIN ANALYZE, 5 execuções, 1ª descartada)")
TAB([["Consulta-alvo", "Sem índice", "Com índice", "Ganho"],
     ["cliente_id = ? ORDER BY data_pedido DESC", "19,13 ms", "<b>0,257 ms</b>", "<b>74×</b> (−98,7%)"],
     ["data_pedido BETWEEN ? AND ? AND status = ?", "16,96 ms", "<b>0,304 ms</b>", "<b>56×</b> (−98,2%)"]],
    [7.4, 3.0, 3.0, 3.6])
H3("5.3 Evidências do plano de execução")
TAB([["Nó do plano", "Sem índice", "Com índice", "Significado"],
     ["Seq Scan on pedido", "10", "<b>0</b>", "Varredura completa das 300 mil linhas"],
     ["Index Scan using idx_...", "0", "<b>10</b>", "Vai direto às linhas do cliente"],
     ["Sort", "10", "<b>0</b>", "Ordenação em tempo de execução — sumiu"],
     ["Rows Removed by Filter", "99.996 por worker", "—", "Linhas lidas e descartadas"]],
    [4.6, 3.0, 2.6, 6.8])
P("Detalhe: na consulta 2 o plano usa <b>Index Scan Backward</b> — o banco percorre o índice ao contrário para atender a ordenação, "
  "sem precisar de outro índice. Os arquivos completos estão em " + C("results/indices/antes.txt") + " e " + C("depois.txt") + ".")
IMG(RAIZ / "docs/img/indices_p95.png", 13, "Latência p95 sob carga — sem índice × com índice (k6, média de 3 repetições)")
H3("5.4 Respostas")
QA("O índice foi efetivamente utilizado pelo banco?",
   "<b>Sim.</b> O plano passou de “Parallel Seq Scan on pedido” para “Index Scan using idx_pedido_cliente_data” em 10 de 10 execuções "
   "(e Index Scan Backward em idx_pedido_data_status na consulta 2).")
QA("Houve redução no tempo de execução?",
   "<b>Sim:</b> 19,13 → 0,257 ms (74×) e 16,96 → 0,304 ms (56×). Sob carga, o efeito é ainda maior: sem índice o throughput <b>estaciona "
   "em ~50–60 req/s</b> em qualquer nível de carga e o p95 vai de 296 ms a 6,8 s; com índice o throughput acompanha a carga até "
   "~1.900–2.000 req/s (p95 37× menor com 10 usuários).")
QA("Quais fatores influenciaram o resultado?",
   "(1) <b>Seletividade</b>: cada cliente tem ~15 pedidos em 300 mil — o índice descarta 99,99% da tabela. (2) <b>Ordem das colunas</b>: "
   "igualdade primeiro (cliente_id), ordenação depois (data_pedido DESC) — por isso o Sort desapareceu; um índice só em cliente_id não "
   "eliminaria a ordenação. (3) <b>LIMIT</b>: com o índice já ordenado, o banco para após as primeiras linhas. (4) <b>Cache de blocos</b> "
   "(shared_buffers): a 1ª execução lê do disco, por isso foi descartada. (5) Estatísticas atualizadas (" + C("ANALYZE") + ") e "
   + C("random_page_cost=1.1") + " (adequado a SSD) orientam o planner.")
QA("Quais os custos de manter índices adicionais?",
   "<b>Espaço</b> em disco; <b>escrita mais lenta</b> — todo INSERT/UPDATE/DELETE atualiza todos os índices da tabela; mais trabalho de "
   "manutenção (VACUUM, bloat); e mais planos possíveis para o otimizador avaliar.")
QA("Criar índices em todas as colunas consultadas seria uma boa estratégia?",
   "<b>Não.</b> Além do custo de escrita e espaço, índices de <b>baixa seletividade</b> são ignorados: " + C("status") + " tem 5 valores em "
   "300 mil linhas, e ler o índice e depois buscar as linhas sairia mais caro que varrer a tabela — o planner escolhe o Seq Scan. Índices "
   "devem nascer de <b>consultas reais medidas</b>, com colunas na ordem certa (igualdade → intervalo/ordenação), e não coluna a coluna.")
BR()

# ---------------- ITEM 3 ----------------
H2("5.5 ITEM 3 — Testes de desempenho")
H3("6.1 Ferramenta: Grafana k6")
P("Cenários escritos em JavaScript (" + C("k6/cenario1-cache.js") + ", " + C("cenario2-persistencia.js") + ", " + C("cenario3-indices.js") +
  "), execução por linha de comando, p95/p99 nativos e exportação em JSON (" + C("--summary-export") + ") para consolidação automática. "
  "Baixo consumo de recursos do gerador de carga — importante porque ele roda na mesma máquina da aplicação.")
H3("6.2 / 6.3 Cenários e cargas")
TAB([["Cenário", "Variantes", "Cargas (usuários virtuais)"],
     ["1 — Cache", "sem-cache · com-cache-quente (50 IDs) · com-cache-espalhado (2.000 IDs)", "10 · 50 · 100 · 200"],
     ["2 — Persistência", "lazy · eager · join-fetch · entity-graph · batch · dto · nativo", "5 · 10 · 25 · 50 (limite=20)"],
     ["3 — Índices", "sem-índice · com-índice", "10 · 50 · 100 · 200"]],
    [3.0, 9.0, 5.0])
P("<b>Execução registrada</b> (" + C("results/run-all.log") + "): 3 repetições por ponto, 25 s de medição, 8 s de aquecimento descartado. "
  "O cenário de persistência usa carga menor porque a variante LAZY leva ~1,1 s por requisição: com 200 usuários ela <b>satura</b>, a fila "
  "estoura o timeout e a rodada mediria o timeout do k6, não o custo do N+1.")
NOTA("Um usuário virtual dispara requisições em sequência: 10 VUs geraram ~1.600 req/s no cenário de cache. Mais VUs = mais "
     "<b>concorrência</b>, não necessariamente mais vazão.", "info", "VUs ≠ requisições por segundo")
H3("6.4 Métricas obrigatórias (médias de 3 repetições)")
def linha_m(c, v, u, rot):
    return [rot, str(u), m(c, v, u, "latencia_media_ms"), m(c, v, u, "latencia_p95_ms"), m(c, v, u, "latencia_p99_ms"),
            m(c, v, u, "throughput_req_s", 0), m(c, v, u, "taxa_erro_pct") + "%"]
rows = [["Implementação", "VUs", "Média (ms)", "p95 (ms)", "p99 (ms)", "Throughput (req/s)", "Erros"]]
for (c, v, rot) in [("cache", "sem-cache", "Sem cache"), ("cache", "com-cache-quente", "Com cache (quente)"),
                    ("indices", "sem-indice", "Sem índice"), ("indices", "com-indice", "Com índice")]:
    for u in (10, 50, 100, 200):
        rows.append(linha_m(c, v, u, rot))
TAB(rows, [3.6, 1.2, 2.2, 2.2, 2.2, 3.2, 2.4])
rows = [["Estratégia (limite=20)", "VUs", "Média (ms)", "p95 (ms)", "p99 (ms)", "Throughput (req/s)", "Erros"]]
for v in ("lazy", "eager", "join-fetch", "entity-graph", "batch", "dto", "nativo"):
    for u in (10, 50):
        rows.append(linha_m("persistencia", v, u, v))
TAB(rows, [3.6, 1.2, 2.2, 2.2, 2.2, 3.2, 2.4])
P("<b>CPU e memória:</b> " + C("docker stats") + " dos containers registrado em " + C("results/recursos/") +
  " (Postgres ~157 MiB de 1,5 GiB; Redis ~5 MiB de 384 MiB). Ver limitação na seção 6.", "small")
H3("6.5 Cuidados com a execução")
TAB([["Cuidado exigido", "Como foi garantido"],
     ["Ambientes equivalentes", "CPU/memória fixas no docker-compose (Postgres 2 CPUs/1,5 GB; Redis 1 CPU/384 MB); pool Hikari fixo em 20"],
     ["Mesmas cargas", "O runner aplica os mesmos níveis e duração a todas as variantes"],
     ["Registrar volume de dados", "/api/admin/stats consultado e gravado antes da bateria"],
     ["Estado inicial do cache", "Cache limpo ou pré-aquecido explicitamente antes de cada rodada"],
     ["Aquecimento", "Execução separada e <b>descartada</b> (processo k6 próprio, para não entrar nos percentis)"],
     ["Evitar distorções", "Log de SQL desligado; log “Session Metrics” do Hibernate silenciado (gerava 34 MB e entrava no tempo de resposta)"],
     ["Repetições", "3 por ponto, com desvio-padrão do p95 registrado; rodadas com >50% de erro são descartadas como inválidas"],
     ["Ambiente próprio", "Tudo local (localhost), containers isolados"]],
    [4.4, 12.6])
story.append(CondPageBreak(10 * cm)); H3("6.6 Tabelas e gráficos")
IMG(RAIZ / "docs/img/cache_throughput.png", 12.5, "Throughput — cenário de cache")
IMG(RAIZ / "docs/img/indices_throughput.png", 12.5, "Throughput — cenário de índices: sem índice estaciona em ~50–60 req/s")
IMG(RAIZ / "docs/img/persistencia_throughput.png", 12.5, "Throughput — estratégias de persistência")
H3("6.7 Discussão dos resultados")
QA("Qual técnica apresentou os maiores ganhos?",
   "Depende da métrica. <b>Maior redução de trabalho:</b> otimização de consultas (271 → 2 SQL, 51× no tempo). <b>Maior ganho por esforço:</b> "
   "o índice — uma linha de SQL, nenhuma mudança na aplicação, 74× na consulta e 20–37× no p95 sob carga. <b>Cache:</b> 6,2× no p95 e 3,3× "
   "no throughput, mas só sob carga alta.")
QA("Os ganhos foram mantidos quando a carga aumentou?",
   "<b>Cache: cresceram</b> (1,5× → 6,2×) — ele alivia <i>contenção</i>. <b>Índice: decisivo em qualquer carga</b> (37× com 10 usuários, "
   "20× com 200) — ele elimina <i>trabalho</i>; o leve recuo em 200 usuários é a aplicação com índice também começando a saturar (pool de 20 "
   "conexões). <b>Consultas:</b> o LAZY fica preso em ~50 req/s em qualquer carga, enquanto as otimizadas chegam a ~650–950 req/s.")
QA("Houve diferenças relevantes entre média, p95 e p99?",
   "Sim, sobretudo sem otimização. Sem índice com 200 usuários: média " + m("indices", "sem-indice", 200, "latencia_media_ms", 0) +
   " ms, p95 " + m("indices", "sem-indice", 200, "latencia_p95_ms", 0) + " ms, p99 " + m("indices", "sem-indice", 200, "latencia_p99_ms", 0) +
   " ms — 1 em cada 100 usuários esperou ~9 s. Sem cache: média 101, p95 290, p99 452 ms; com cache 30 / 47 / 61 ms. "
   "A distância entre média e p99 indica <b>fila</b> (pool de conexões, CPU do banco). As otimizações encurtam principalmente a cauda.")
QA("Alguma otimização apresentou resultados inferiores aos esperados?",
   "(1) <b>EAGER</b> não eliminou o N+1 (101 SQL). (2) <b>SQL nativo</b> não superou JOIN FETCH/EntityGraph. (3) A variante “cache frio” "
   "não media o MISS (98,5% de hit). (4) Com 200 usuários, até a versão <b>com índice</b> teve 2,75% de erros e p95 de 333 ms — a "
   "aplicação inteira, e não só a consulta, passa a ser o gargalo. (5) Com 10 usuários, o cache ganhou só 1,5×.")
QA("Quais foram os principais gargalos?",
   "Seq Scan consumindo a CPU do Postgres (limitado a 2 CPUs); <b>pool de 20 conexões</b> — requisições lentas seguram a conexão e as demais "
   "esperam na fila; <b>idas e voltas</b> ao banco no N+1 (271 por requisição); e, antes de corrigido, o I/O de log do Hibernate.")
QA("Como a redução das consultas ao banco influenciou o desempenho?",
   "Cada consulta evitada economiza uma ida e volta e, principalmente, <b>tempo de conexão do pool ocupado</b>. Menos tempo por requisição "
   "→ conexões liberadas mais cedo → menos fila → throughput maior e cauda (p99) menor. É por isso que LAZY (271 SQL) fica preso em ~50 req/s "
   "e as variantes de 2 SQL passam de 600 req/s com o mesmo hardware.")
QA("Quais os custos ou riscos das otimizações adotadas?",
   "<b>Cache:</b> dado desatualizado, memória extra, MISS mais caro, complexidade e bugs silenciosos (self-invocation, serialização de "
   "records). <b>Índice:</b> espaço e escrita mais lenta. <b>JOIN FETCH:</b> produto cartesiano com várias coleções e paginação em memória "
   "se mal usado. <b>SQL nativo:</b> portabilidade e manutenção. <b>@BatchSize:</b> ainda faz mais de uma consulta. <b>Geral:</b> cachear "
   "uma consulta mal escrita só esconde o problema até o primeiro MISS — a ordem certa é medir → reduzir consultas → baratear cada consulta → cachear.")
BR()

H2("5.6 Entregáveis (seção 7)")
TAB([["Entregável", "Status", "Onde"],
     ["Código dos Web Services", '<font color="#1b7a4b"><b>Sim</b></font>', "app/"],
     ["Configurações", '<font color="#1b7a4b"><b>Sim</b></font>', "application.yml, docker-compose.yml, CacheConfig, WebConfig"],
     ["Scripts de criação e população do banco", '<font color="#1b7a4b"><b>Sim</b></font>', "db/01-schema.sql, db/02-seed.sql, db/10 e 11 (índices)"],
     ["Implementações alternativas", '<font color="#1b7a4b"><b>Sim</b></font>', "entity/lazy|eager|batch, 8 endpoints de pedidos, sem/com cache"],
     ["Scripts de teste de desempenho", '<font color="#1b7a4b"><b>Sim</b></font>', "k6/ + scripts/run-all-tests.sh"],
     ["Instruções de execução", '<font color="#1b7a4b"><b>Sim</b></font>', "README.md (seção Como executar) e este guia"],
     ["Relatório técnico README.md (7 seções)", '<font color="#1b7a4b"><b>Sim</b></font>', "README.md: intro, arquitetura, cache, consultas, testes, discussão, conclusões"],
     ["Gráficos, tabelas, código, evidências", '<font color="#1b7a4b"><b>Sim</b></font>', "docs/img/, results/, docs/dashboard.html"],
     ["Apresentação / vídeo ≤ 7 min", "Roteiro pronto", "docs/ROTEIRO_VIDEO.md + scripts/demo-video.sh + aba Teste ao vivo"]],
    [6.0, 2.4, 8.6])
H2("5.7 Apresentação prática (seção 7.3) — onde mostrar cada ponto")
TAB([["O enunciado pede", "Terminal (demo-video.sh)", "Página (dashboard.html)"],
     ["Arquitetura simplificada", "—", "Aba Como funciona"],
     ["Funcionamento dos Web Services", "Blocos 1–2", "Teste ao vivo (status + qualquer botão)"],
     ["Cache e mecanismo de atualização", "Bloco 3", "Teste ao vivo → 1. Cache (ciclo completo)"],
     ["Diferenças LAZY × EAGER", "Bloco 4", "Teste ao vivo → 2. N+1"],
     ["Consultas antes/depois das otimizações", "Bloco 5", "Teste ao vivo → Comparar todas as estratégias"],
     ["Uso dos índices", "Bloco 6", "Teste ao vivo → 3. Índice"],
     ["Pelo menos um teste de desempenho", "Bloco 7 (k6 ao vivo)", "Teste ao vivo → 4. Mini carga (ilustrativo)"],
     ["Principais resultados e conclusões", "—", "Abas Visão geral e 3. Testes de carga"]],
    [5.6, 4.4, 7.0])
BR()

# ======================================================================
# PARTE 6 - VIDEO E PENDENCIAS
# ======================================================================
H1("6. Vídeo, limitações e pendências")
H2("6.1 Roteiro do vídeo (≤ 7 min)")
TAB([["Tempo", "Bloco", "Onde"],
     ["0:00–0:45", "Abertura e arquitetura", "Painel → Como funciona"],
     ["0:45–1:15", "A ferramenta de medição (headers X-)", "Terminal bloco 2 ou Teste ao vivo"],
     ["1:15–2:30", "Cache: HIT, MISS e invalidação", "Teste ao vivo → ciclo completo"],
     ["2:30–3:40", "LAZY × EAGER e o N+1", "Teste ao vivo → LAZY com limite crescente"],
     ["3:40–4:30", "Consultas otimizadas", "Teste ao vivo → Comparar todas"],
     ["4:30–5:30", "Índices e EXPLAIN", "Teste ao vivo → Comparar sem × com índice"],
     ["5:30–6:20", "Teste de carga ao vivo", "Terminal: bash scripts/demo-video.sh 7"],
     ["6:20–7:00", "Resultados e conclusão", "Painel → Visão geral e 3. Testes de carga"]],
    [2.6, 6.4, 8.0])
P("Gravação: <b>OBS Studio</b> ou <b>Clipchamp</b> (Windows 11, “Gravar tela”) — ambos gravam a tela inteira com microfone. Evite o Xbox Game Bar, "
  "que grava só uma janela. Fonte do terminal grande (Ctrl + +). O texto completo da narração está em " + C("docs/ROTEIRO_VIDEO.md") + ".")
H2("6.2 Limitações conhecidas (seja honesto se perguntarem)")
BUL(["<b>CPU/memória</b>: o " + C("docker stats") + " foi coletado antes e depois de cada rodada, não durante — vale para memória, não para pico de CPU.",
     "<b>Persistência</b>: cargas menores (5–50 VUs, limite=20) e 2 repetições na maioria dos pontos (1 em alguns de 50 VUs), pela saturação do LAZY.",
     "<b>Mesma máquina</b>: k6, API, Postgres e Redis dividem o mesmo computador; os números absolutos dependem dele, as comparações relativas não.",
     "<b>Taxa de erros com 200 VUs</b>: 10% sem índice e 2,75% com índice — saturação do pool, registrada e não escondida.",
     "<b>results/queries.txt</b> citado no README não foi gerado; os números estão nas tabelas e podem ser gerados com " + C("bash scripts/coletar-queries.sh") + "."])
H2("6.3 Correções feitas durante a revisão")
BUL(["Scripts " + C(".sh") + " corrigidos para o Git Bash do Windows (" + C("MSYS_NO_PATHCONV=1") + " e " + C(".\\mvnw.cmd") + "): antes, o reinício da API falhava em silêncio.",
     "Roteiro do vídeo: números do cache corrigidos para os medidos (6,2× no p95 e 3,3× no throughput).",
     "Experimentos de cache (3.4/3.5) executados novamente e salvos em " + C("results/cache/") + ".",
     "Painel: nova aba “Teste ao vivo”, com CORS e endpoints de apoio na API."])

# ======================================================================
# APENDICES
# ======================================================================
BR()
H1("Apêndice A — Endpoints")
TAB([["Método", "Rota", "Descrição", "SQL"],
     ["GET", "/api/admin/stats", "Contagem por tabela e índices", "—"],
     ["GET", "/api/admin/cache/stats", "Hits, misses, hit ratio", "0"],
     ["DELETE", "/api/admin/cache", "Limpa o cache", "0"],
     ["POST", "/api/admin/indices/{criar|remover}", "Cria/remove índices do item 2c", "—"],
     ["GET", "/api/admin/explain?clienteId=150", "EXPLAIN ANALYZE da consulta-alvo", "—"],
     ["GET", "/api/produtos/{id}/sem-cache", "Produto sempre do banco", "1"],
     ["GET", "/api/produtos/{id}/com-cache", "Produto via Redis", "0 (HIT) / 1 (MISS)"],
     ["PUT", "/api/produtos/{id}", "Atualiza preço/estoque e invalida", "2"],
     ["GET", "/api/categorias/sem-cache · /com-cache", "Lista de categorias", "1 / 0"],
     ["GET", "/api/pedidos/lazy?limite=", "LAZY acessando relacionamentos", "N+1"],
     ["GET", "/api/pedidos/eager?limite=", "EAGER", "N+1"],
     ["GET", "/api/pedidos/lazy-sem-acesso?limite=", "LAZY sem tocar relacionamentos", "1"],
     ["GET", "/api/pedidos/join-fetch?limite=", "JOIN FETCH em 2 etapas", "2"],
     ["GET", "/api/pedidos/entity-graph?limite=", "@EntityGraph", "2"],
     ["GET", "/api/pedidos/batch?limite=", "@BatchSize(100)", "1 + N/100 (arred.)"],
     ["GET", "/api/pedidos/dto?limite=", "Projeção DTO", "2"],
     ["GET", "/api/pedidos/nativo?limite=", "SQL nativo com json_agg", "2"],
     ["GET", "/api/clientes/{id}/pedidos?limite=", "Consulta-alvo 1 do índice", "1"],
     ["GET", "/api/pedidos/periodo?inicio=&fim=&status=", "Consulta-alvo 2 do índice", "1"],
     ["GET", "/actuator/health", "Saúde da aplicação", "—"]],
    [1.6, 6.4, 5.8, 3.2])

H1("Apêndice B — Glossário")
TAB([["Termo", "Significado"],
     ["Cache HIT / MISS", "HIT: o dado estava no cache. MISS: não estava, foi preciso ir ao banco"],
     ["TTL", "Time to Live: tempo até a chave expirar sozinha no Redis"],
     ["Cache-aside", "A aplicação consulta o cache; no MISS lê do banco e grava no cache"],
     ["@Cacheable / @CacheEvict", "Anotações do Spring: ler/gravar no cache; remover do cache"],
     ["Self-invocation", "Método chamando outro da mesma classe: não passa pelo proxy, a anotação é ignorada"],
     ["LAZY / EAGER", "Carregar relacionamentos sob demanda / antecipadamente"],
     ["N+1", "1 consulta para a lista + 1 (ou mais) por item da lista"],
     ["JOIN FETCH / @EntityGraph", "Carregam relacionamentos na mesma consulta"],
     ["@BatchSize", "Carrega relacionamentos em lotes com WHERE id IN (...)"],
     ["Projeção DTO", "Consulta que devolve só as colunas necessárias, sem entidades"],
     ["Seq Scan / Index Scan", "Varrer a tabela inteira / ir direto às linhas pelo índice"],
     ["EXPLAIN ANALYZE", "Executa a consulta e mostra o plano real com tempos"],
     ["VU", "Usuário virtual do k6: faz requisições em sequência, em loop"],
     ["p95 / p99", "Tempo abaixo do qual estão 95% / 99% das requisições"],
     ["Throughput", "Requisições atendidas por segundo"],
     ["Pool de conexões", "Conjunto fixo (20) de conexões reaproveitadas com o banco"]],
    [4.6, 12.4])


# ======================================================================
# DOCUMENTO: cabecalho/rodape + sumario
# ======================================================================
class Doc(BaseDocTemplate):
    def __init__(self, fn, **kw):
        super().__init__(fn, **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=frame, onPage=self.decorar)])

    def decorar(self, canv, doc):
        if doc.page == 1: return
        canv.saveState()
        canv.setFont("Arial", 7.8); canv.setFillColor(CINZA)
        canv.drawString(doc.leftMargin, A4[1] - 1.25 * cm, "Trabalho Prático A2 — Otimização de Web Services")
        canv.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.25 * cm, "Guia completo e gabarito")
        canv.setStrokeColor(BORDA); canv.setLineWidth(0.5)
        canv.line(doc.leftMargin, A4[1] - 1.4 * cm, A4[0] - doc.rightMargin, A4[1] - 1.4 * cm)
        canv.drawCentredString(A4[0] / 2, 1.1 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            txt = f.getPlainText()
            if txt in ("Sumário",): return
            nivel = 0 if f.style.name == "h1" else 1
            key = f"s{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=nivel, closed=nivel > 0)
            self.notify("TOCEntry", (nivel, txt, self.page, key))

doc = Doc(str(SAIDA), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.9 * cm, bottomMargin=1.8 * cm,
          title="Trabalho A2 — Guia completo e gabarito", author="Trabalho A2", subject="Otimização de Web Services")
doc.multiBuild(story)
print("->", SAIDA)
