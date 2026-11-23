#!/usr/bin/env python3
"""
Gera docs/dashboard.html: pagina interativa que explica o trabalho e mostra os
resultados REAIS medidos (nada de valor ilustrativo).

Fontes de dados:
  results/resumo.csv          -> rodadas do k6
  results/indices/resumo.txt  -> tempos do EXPLAIN antes/depois
  results/queries.json        -> X-Query-Count por estrategia (scripts/coletar-queries.sh)
  results/cache/experimento.txt -> saida do experimento obrigatorio do item 3.4

Uso: python scripts/gerar_dashboard.py
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ler_json(caminho, default):
    p = RAIZ / caminho
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        # Nao engolir em silencio: um JSON corrompido fazia a secao do
        # dashboard aparecer como "Sem dados" sem nenhuma pista do motivo.
        print(f"AVISO: {caminho} invalido ({e}); secao ficara vazia")
        return default


def tempos_explain():
    """Extrai os 'Execution Time' de results/indices/{antes,depois}.txt.

    IMPORTANTE: o arquivo contem DUAS consultas-alvo (filtro por cliente e
    filtro por periodo+status), 5 execucoes cada. Misturar as 10 medicoes numa
    media unica compara coisas diferentes, entao separamos por consulta e
    DESCARTAMOS a 1a execucao de cada bloco (ela le do disco; as seguintes vem
    do shared_buffers do Postgres).
    """
    out = {}
    por_consulta = {}
    for fase in ("antes", "depois"):
        p = RAIZ / "results" / "indices" / f"{fase}.txt"
        if not p.exists():
            out[fase] = []
            por_consulta[fase] = []
            continue
        texto = p.read_text(encoding="utf-8", errors="ignore")
        out[fase] = [float(x) for x in re.findall(r"Execution Time:\s*([\d.]+)\s*ms", texto)]

        blocos = []
        for b in re.split(r"={10,}|#+\s*CONSULTA", texto):
            tempos = [float(x) for x in re.findall(r"Execution Time:\s*([\d.]+)\s*ms", b)]
            if not tempos:
                continue
            if "cliente_id" in b:
                rotulo = "WHERE cliente_id = ? ORDER BY data_pedido DESC"
            elif "data_pedido" in b:
                rotulo = "WHERE data_pedido BETWEEN ? AND ? AND status = ?"
            else:
                rotulo = f"consulta {len(blocos) + 1}"
            uteis = tempos[1:] or tempos          # 1a execucao descartada
            blocos.append({
                "consulta": rotulo,
                "tempos": tempos,
                "media": sum(uteis) / len(uteis),
                "n": len(uteis),
            })
        por_consulta[fase] = blocos
    out["por_consulta"] = por_consulta
    # Planos: quais nos de acesso aparecem em cada fase
    planos = {}
    for fase in ("antes", "depois"):
        p = RAIZ / "results" / "indices" / f"{fase}.txt"
        texto = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""
        planos[fase] = {
            "seq_scan": len(re.findall(r"Seq Scan on pedido", texto)),
            "index_scan": len(re.findall(r"Index (?:Only )?Scan(?: Backward)? using", texto)),
            "sort": len(re.findall(r"^\s*->?\s*Sort\b", texto, re.M)),
        }
    return out, planos


def main():
    # ---------- resultados do k6 ----------
    dados = ler_json("docs/dados.json", {"rodadas": [], "medias": []})
    # ---------- contagem de SQL por estrategia ----------
    queries = ler_json("results/queries.json", {})
    # ---------- EXPLAIN ----------
    explain, planos = tempos_explain()

    payload = json.dumps({
        "medias": dados.get("medias", []),
        "rodadas": dados.get("rodadas", []),
        "queries": queries,
        "explain": explain,
        "planos": planos,
    }, ensure_ascii=False)

    html = TEMPLATE.replace("/*__DADOS__*/", payload)
    destino = RAIZ / "docs" / "dashboard.html"
    destino.write_text(html, encoding="utf-8")

    print(f"-> {destino.relative_to(RAIZ)}")
    print(f"   {len(dados.get('medias', []))} combinacoes de carga, "
          f"{len(queries)} estrategias com contagem de SQL, "
          f"{len(explain.get('antes', []))}+{len(explain.get('depois', []))} medicoes de EXPLAIN")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A2 - Otimizacao de Web Services | Painel de Resultados</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0f1117; --card:#171a23; --card2:#1e222e; --bd:#2a2f3d;
    --fg:#e7eaf0; --mut:#9aa3b5; --ac:#5b9cff; --ok:#3ddc97; --warn:#ffb454; --bad:#ff6b6b;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  header{padding:28px 32px;border-bottom:1px solid var(--bd);
         background:linear-gradient(135deg,#171a23,#121520)}
  header h1{margin:0 0 6px;font-size:24px}
  header p{margin:0;color:var(--mut)}
  nav{display:flex;gap:4px;padding:0 32px;border-bottom:1px solid var(--bd);
      background:var(--card);position:sticky;top:0;z-index:10;flex-wrap:wrap}
  nav button{background:none;border:none;color:var(--mut);padding:14px 16px;cursor:pointer;
             font-size:14px;border-bottom:2px solid transparent;font-family:inherit}
  nav button:hover{color:var(--fg)}
  nav button.on{color:var(--ac);border-bottom-color:var(--ac)}
  main{padding:28px 32px;max-width:1180px}
  section{display:none} section.on{display:block}
  h2{font-size:20px;margin:0 0 4px}
  h3{font-size:16px;margin:28px 0 10px;color:var(--fg)}
  .sub{color:var(--mut);margin:0 0 22px}
  .card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:18px;margin:16px 0}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
  .kpi{background:var(--card2);border:1px solid var(--bd);border-radius:10px;padding:16px}
  .kpi .v{font-size:26px;font-weight:600;margin:4px 0}
  .kpi .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
  .kpi .d{color:var(--mut);font-size:12px}
  .good{color:var(--ok)} .bad{color:var(--bad)} .warn{color:var(--warn)}
  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
  th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--bd)}
  th:first-child,td:first-child{text-align:left}
  th{color:var(--mut);font-weight:500;text-transform:uppercase;font-size:11px;letter-spacing:.4px}
  tr:hover td{background:#1b1f2b}
  code{background:#0b0d13;padding:2px 6px;border-radius:4px;font-size:13px;color:#8fd3ff}
  pre{background:#0b0d13;border:1px solid var(--bd);border-radius:8px;padding:14px;
      overflow:auto;font-size:12.5px;line-height:1.5}
  .note{border-left:3px solid var(--ac);background:#141b2b;padding:12px 16px;
        border-radius:0 8px 8px 0;margin:14px 0}
  .note.w{border-color:var(--warn);background:#241e14}
  .note.g{border-color:var(--ok);background:#13231d}
  .ctl{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
  select{background:var(--card2);color:var(--fg);border:1px solid var(--bd);
         border-radius:6px;padding:7px 10px;font-family:inherit}
  label{color:var(--mut);font-size:13px}
  .wrap{position:relative;height:340px}
  .empty{color:var(--mut);font-style:italic;padding:20px;text-align:center}
  .tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
       background:var(--card2);border:1px solid var(--bd);color:var(--mut);margin-right:6px}
  ul{margin:8px 0 8px 20px;padding:0} li{margin:5px 0}
  .lever{background:var(--card2);border:1px solid var(--bd);border-radius:8px;padding:14px;margin:10px 0}
  .lever b{color:var(--ac)}

  /* ---------------- aba Teste ao vivo ---------------- */
  nav button.live{color:var(--ok);font-weight:600}
  nav button.live.on{border-bottom-color:var(--ok)}
  .bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:var(--card);
       border:1px solid var(--bd);border-radius:10px;padding:12px 16px;margin-bottom:6px}
  .dot{width:10px;height:10px;border-radius:50%;background:var(--mut);display:inline-block}
  .dot.on{background:var(--ok);box-shadow:0 0 8px var(--ok)} .dot.off{background:var(--bad)}
  input[type=text],input[type=number]{background:var(--card2);color:var(--fg);border:1px solid var(--bd);
       border-radius:6px;padding:7px 10px;font-family:inherit;font-size:14px}
  .btn{background:var(--card2);color:var(--fg);border:1px solid var(--bd);border-radius:8px;
       padding:9px 14px;cursor:pointer;font:inherit;font-size:14px;transition:.15s}
  .btn:hover:not(:disabled){border-color:var(--ac);color:var(--ac)}
  .btn:disabled{opacity:.45;cursor:wait}
  .btn.pri{background:var(--ac);border-color:var(--ac);color:#0b0d13;font-weight:600}
  .btn.pri:hover:not(:disabled){filter:brightness(1.15);color:#0b0d13}
  .btn.dng:hover:not(:disabled){border-color:var(--bad);color:var(--bad)}
  .btns{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
  .step{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;
        border-radius:50%;background:var(--ac);color:#0b0d13;font-size:12px;font-weight:700;margin-right:6px}
  .log{display:flex;flex-direction:column;gap:8px;margin-top:12px;max-height:760px;overflow:auto}
  .req{display:grid;grid-template-columns:1fr auto;gap:6px 14px;background:var(--card2);
       border:1px solid var(--bd);border-left:4px solid var(--mut);border-radius:8px;padding:10px 14px;
       animation:entra .25s ease-out}
  .req.HIT{border-left-color:var(--ok)} .req.MISS{border-left-color:var(--warn)}
  .req.BYPASS{border-left-color:var(--ac)} .req.ERRO{border-left-color:var(--bad)}
  @keyframes entra{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
  .req .u{font-family:ui-monospace,Consolas,monospace;font-size:13px;word-break:break-all}
  .req .u b{color:var(--ac);margin-right:6px}
  .req .nota{grid-column:1/-1;color:var(--mut);font-size:13px}
  .req .corpo{grid-column:1/-1;font-family:ui-monospace,Consolas,monospace;font-size:12px;
              color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .bdg{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
  .b{border-radius:6px;padding:3px 9px;font-size:12.5px;font-weight:600;white-space:nowrap;
     background:#0b0d13;border:1px solid var(--bd)}
  .b.sql{font-size:14px} .b.sql.z{color:var(--ok);border-color:var(--ok)}
  .b.sql.n{color:var(--bad);border-color:var(--bad)}
  .b.HIT{color:var(--ok)} .b.MISS{color:var(--warn)} .b.BYPASS{color:var(--ac)}
  .hbar{display:grid;grid-template-columns:130px 1fr 150px;gap:10px;align-items:center;margin:7px 0;font-size:13px}
  .hbar .t{height:22px;background:#0b0d13;border-radius:4px;overflow:hidden}
  .hbar .f{height:100%;border-radius:4px;transition:width .6s ease}
  .hbar .v{text-align:right;font-variant-numeric:tabular-nums}
  .plano{white-space:pre;font-size:12px;line-height:1.55;min-height:120px}
  .plano .seq{color:var(--bad);font-weight:700} .plano .idx{color:var(--ok);font-weight:700}
  .plano .srt{color:var(--warn);font-weight:700} .plano .tm{color:#8fd3ff;font-weight:700}
  .duo{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .duo>div{min-width:0}
  @media (max-width:860px){.duo{grid-template-columns:1fr} .hbar{grid-template-columns:100px 1fr 110px}}
  .big{font-size:34px;font-weight:700;font-variant-numeric:tabular-nums}
  .prog{height:6px;background:#0b0d13;border-radius:3px;overflow:hidden;margin:8px 0}
  .prog div{height:100%;background:var(--ac);width:0;transition:width .2s linear}
</style>
</head>
<body>
<header>
  <h1>Otimizacao de Web Services: cache, consultas e testes de desempenho</h1>
  <p>Trabalho Pratico A2 &middot; Analise e Otimizacao de Sistemas &middot; Universidade Veiga de Almeida</p>
</header>

<nav>
  <button class="on" data-t="visao">Visao geral</button>
  <button data-t="aovivo" class="live">&#9654; Teste ao vivo</button>
  <button data-t="arq">Como funciona</button>
  <button data-t="cache">1. Cache</button>
  <button data-t="consultas">2a. LAZY vs EAGER</button>
  <button data-t="otim">2b. Consultas otimizadas</button>
  <button data-t="indices">2c. Indices</button>
  <button data-t="carga">3. Testes de carga</button>
  <button data-t="alav">O que muda o desempenho</button>
</nav>

<main>
<!-- ============================ VISAO GERAL ============================ -->
<section id="visao" class="on">
  <h2>Visao geral</h2>
  <p class="sub">Numeros medidos nesta maquina. Nenhum valor desta pagina foi estimado:
     todos vem de <code>results/</code>.</p>
  <div class="grid" id="kpis"></div>

  <div class="card">
    <h3 style="margin-top:0">A ideia do experimento em uma frase</h3>
    <p>A mesma consulta ("listar pedidos com cliente e itens" / "buscar um produto")
       foi implementada de varias formas diferentes. Tudo o mais foi mantido
       identico &mdash; mesmo banco, mesmo volume de dados, mesma carga, mesma
       maquina &mdash; para que a <b>unica variavel</b> fosse a tecnica de
       otimizacao. Assim, a diferenca de desempenho observada e atribuivel a
       tecnica, e nao ao ambiente.</p>
    <div class="note">
      <b>Como cada afirmacao e comprovada:</b> toda resposta da API traz os
      headers <code>X-Query-Count</code> (quantos SQL aquela requisicao
      executou), <code>X-Response-Time-Ms</code> e <code>X-Cache</code>
      (HIT/MISS/BYPASS). Qualquer numero pode ser reconferido com um
      <code>curl -i</code>.
    </div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Volume de dados</h3>
    <table>
      <tr><th>Tabela</th><th>Registros</th><th>Papel no experimento</th></tr>
      <tr><td>categoria</td><td>20</td><td>baixa volatilidade &rarr; cache com TTL longo</td></tr>
      <tr><td>produto</td><td>2.000</td><td>preco/estoque volateis &rarr; cache com TTL curto</td></tr>
      <tr><td>cliente</td><td>20.000</td><td>filtro da consulta do experimento de indices</td></tr>
      <tr><td>pedido</td><td>300.000</td><td>tabela principal: Seq Scan aqui custa caro</td></tr>
      <tr><td>item_pedido</td><td>1.050.000</td><td>colecao que provoca o N+1</td></tr>
    </table>
  </div>
</section>

<!-- ============================ ARQUITETURA ============================ -->
<section id="arq">
  <h2>Como funciona</h2>
  <p class="sub">O caminho de uma requisicao e onde cada tecnica atua.</p>

  <div class="card">
    <pre>
  curl / k6
     |
     v
  [ Filtro de diagnostico ]  <-- mede o tempo e conta os SQL da requisicao
     |                           devolve X-Query-Count / X-Response-Time-Ms / X-Cache
     v
  [ Controller ]
     |
     v
  [ Service ]---------> [ Redis ]      TECNICA 1: se o dado esta no cache,
     |                   (cache)       a requisicao termina aqui: ZERO SQL.
     |  (cache MISS)
     v
  [ Repository / JPA ]                 TECNICA 2: a estrategia de carregamento
     |                                 decide QUANTOS SQL serao emitidos.
     v
  [ datasource-proxy ]  <-- intercepta cada SQL e incrementa o contador
     |
     v
  [ PostgreSQL ]                       TECNICA 3: o indice decide se cada SQL
                                        varre a tabela toda ou vai direto.
    </pre>
    <div class="note">
      <b>As tres tecnicas atacam niveis diferentes do mesmo problema:</b>
      o cache reduz o <i>numero de requisicoes que chegam ao banco</i>;
      a estrategia de consulta reduz o <i>numero de SQL por requisicao</i>;
      o indice reduz o <i>custo de cada SQL</i>. Por isso elas se somam em vez
      de competir.
    </div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Modelo de dados</h3>
    <pre>
  categoria 1 ---- N produto
                        |
                        | N
                        |
  cliente 1 ---- N pedido 1 ---- N item_pedido
    </pre>
    <p>O <code>pedido</code> nasce <b>sem indice</b> em <code>cliente_id</code>
       e <code>data_pedido</code>: isso e deliberado. O PostgreSQL nao indexa
       chaves estrangeiras automaticamente, e precisavamos do estado "antes"
       para medir o ganho do indice.</p>
  </div>
</section>

<!-- ============================ CACHE ============================ -->
<section id="cache">
  <h2>Item 1 &mdash; Cache com Redis</h2>
  <p class="sub">O cache nao deixa a consulta mais rapida: ele <b>evita</b> a consulta.</p>

  <div class="card">
    <h3 style="margin-top:0">O que foi cacheado, e por que</h3>
    <table>
      <tr><th>Dado</th><th>Frequencia de leitura</th><th>Volatilidade</th><th>TTL</th><th>Decisao</th></tr>
      <tr><td>Detalhe do produto</td><td>muito alta</td><td class="warn">media (preco/estoque)</td>
          <td>60 s</td><td>cachear + invalidar no update</td></tr>
      <tr><td>Lista de categorias</td><td>alta</td><td class="good">baixissima</td>
          <td>10 min</td><td>cachear com TTL longo</td></tr>
    </table>
    <p>A volatilidade e que define o TTL: quanto mais o dado muda, menor o TTL,
       porque <b>o TTL e o tamanho maximo da janela em que um cliente pode
       receber um dado errado</b>.</p>
  </div>

  <div class="card">
    <h3 style="margin-top:0">O ciclo HIT / MISS / invalidacao</h3>
    <pre>
 1) GET /api/produtos/10/com-cache  ->  X-Cache: MISS   X-Query-Count: 1
 2) GET /api/produtos/10/com-cache  ->  X-Cache: HIT    X-Query-Count: 0  <-- banco nao foi tocado
 3) PUT /api/produtos/10 {preco}    ->  grava no banco e REMOVE a chave do Redis
 4) GET /api/produtos/10/com-cache  ->  X-Cache: MISS   X-Query-Count: 1  (dado novo)
 5) apos o TTL                      ->  a chave expira sozinha; proxima leitura e MISS
    </pre>
    <div class="note g"><b>A prova do cache e <code>X-Query-Count: 0</code>.</b>
      Latencia menor poderia ser coincidencia de carga; zero SQL nao tem outra
      explicacao: a requisicao foi atendida sem o banco.</div>
    <div class="note w"><b>Escolhemos <code>@CacheEvict</code> (apagar) em vez de
      <code>@CachePut</code> (sobrescrever).</b> O CachePut gravaria no cache o
      valor que a aplicacao <i>supoe</i> estar no banco; se houver trigger,
      default ou escrita concorrente, o cache passaria a servir um valor que
      nunca existiu. Apagando, a proxima leitura reconstroi a partir da fonte da
      verdade. Custo: um MISS extra. Beneficio: nao existe cache mentindo.</div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Resultado sob carga</h3>
    <div class="ctl">
      <label>Metrica <select id="selCacheMet">
        <option value="latencia_p95_ms">latencia p95 (ms)</option>
        <option value="latencia_media_ms">latencia media (ms)</option>
        <option value="latencia_p99_ms">latencia p99 (ms)</option>
        <option value="throughput_req_s">throughput (req/s)</option>
      </select></label>
    </div>
    <div class="wrap"><canvas id="cCache"></canvas></div>
    <div id="tCache"></div>
    <div class="note w"><b>Correcao de metodo (a medicao contrariou a hipotese):</b>
      a variante hoje chamada <code>com-cache-espalhado</code> nasceu como
      "cache frio", para medir o custo do MISS. <b>Ela nao faz isso.</b> O hit
      ratio medido foi de <b>98,5%</b>: com 2.000 IDs distintos e ~2.300 req/s,
      o cache aquece em <b>0,86 s de uma rodada de 25 s</b>. Por isso as curvas
      "quente" e "espalhado" praticamente coincidem no grafico acima &mdash; as
      duas sao quentes. O que essa variante realmente mede e o efeito da
      <i>cardinalidade das chaves</i> (50 vs 2.000 IDs).
      <br><br>
      <b>Teste de carga e a ferramenta errada para medir o custo do MISS:</b>
      qualquer faixa de chaves que caiba na tabela aquece em menos de um
      segundo. A pergunta do item 3.5 e respondida por
      <code>scripts/experimento-custo-miss.sh</code>, que limpa o cache antes de
      CADA requisicao (100% MISS garantido): o MISS paga 3 idas
      (Redis + banco + Redis) contra 1 ida de quem nao tem cache.
      <br><br>
      <b>Licao:</b> rotulo de variante nao e prova. O hit ratio e.</div>
  </div>
</section>

<!-- ============================ LAZY vs EAGER ============================ -->
<section id="consultas">
  <h2>Item 2a &mdash; LAZY vs EAGER e o problema N+1</h2>
  <p class="sub">O mesmo resultado, a mesma tela, numeros de SQL radicalmente diferentes.</p>

  <div class="card">
    <h3 style="margin-top:0">SQL executado por requisicao (medido)</h3>
    <div class="wrap"><canvas id="cQueries"></canvas></div>
    <div id="tQueries"></div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Por que o N+1 acontece</h3>
    <p>Em LAZY, o Hibernate devolve um <b>proxy</b> no lugar do objeto
       relacionado. O SQL extra so e disparado quando o codigo toca nesse proxy.
       Montar o DTO percorre cliente e itens de cada pedido &mdash; e cada
       acesso vira uma consulta:</p>
    <pre>
 1  SELECT * FROM pedido ORDER BY id LIMIT 100          <- a "1"
 +  SELECT * FROM cliente      WHERE id = ?   x100      <- os "N"
 +  SELECT * FROM item_pedido  WHERE pedido_id = ?  x100
 +  SELECT * FROM produto      WHERE id = ?   x...
    </pre>
    <div class="note w"><b>EAGER nao resolve o N+1.</b> O enunciado pede para
      observar o comportamento real, e foi o que fizemos: com colecao EAGER numa
      consulta JPQL sem fetch explicito, o Hibernate traz os pedidos e depois
      resolve cada colecao &mdash; tambem em N consultas. A diferenca e que
      agora o custo e pago <i>sempre</i>, mesmo quando o endpoint nao usa os
      relacionamentos.</div>
    <div class="note g"><b>A vantagem real do LAZY</b> aparece em
      <code>/lazy-sem-acesso</code>: nada e tocado, nenhuma query extra e
      emitida, e o contador fica em 1 independentemente do limite. LAZY e um bom
      <i>default</i>; o erro nao e o LAZY, e percorrer relacionamentos sem ter
      planejado como carrega-los.</div>
  </div>
</section>

<!-- ============================ OTIMIZADAS ============================ -->
<section id="otim">
  <h2>Item 2b &mdash; Consultas otimizadas</h2>
  <p class="sub">Cinco formas de obter o mesmo DTO com um numero constante de SQL.</p>

  <div class="card">
    <table>
      <tr><th>Estrategia</th><th>Como funciona</th><th>Quando preferir</th></tr>
      <tr><td><code>JOIN FETCH</code></td>
          <td>uma query com join; os relacionamentos vem na mesma linha</td>
          <td>o caso geral; exige o padrao de 2 etapas quando ha paginacao</td></tr>
      <tr><td><code>@EntityGraph</code></td>
          <td>mesmo plano do JOIN FETCH, declarado por atributos</td>
          <td>quando se quer reaproveitar a query variando o que carregar</td></tr>
      <tr><td><code>@BatchSize</code></td>
          <td>agrupa os proxies em <code>WHERE id IN (...)</code></td>
          <td>varias colecoes: evita o produto cartesiano do join</td></tr>
      <tr><td>Projecao DTO</td>
          <td>le colunas soltas, sem criar entidades gerenciadas</td>
          <td>telas de leitura: menos CPU e memoria por requisicao</td></tr>
      <tr><td>SQL nativo (<code>json_agg</code>)</td>
          <td>o banco monta o array de itens; 1 linha por pedido</td>
          <td>payload grande, onde as linhas repetidas do join pesam</td></tr>
    </table>
    <div class="note w"><b>Paginacao + JOIN FETCH de colecao: a armadilha.</b>
      Com join de colecao, um pedido vira N linhas. Aplicar <code>LIMIT</code>
      direto cortaria no meio dos itens, trazendo pedidos incompletos &mdash; o
      Hibernate detecta isso e, para nao errar, traz tudo para a memoria e
      pagina em Java (aviso <code>HHH90003004</code>), o que anula o ganho. A
      solucao e o padrao de 2 etapas: primeiro os <i>IDs</i> da pagina, depois o
      JOIN FETCH <i>por esses IDs</i>.</div>
    <div class="note"><b>SQL nativo compensou?</b> Em numero de SQL, empata com
      JOIN FETCH (ambos constantes). Ganha em trafego, porque nao repete os
      dados do pedido em cada linha de item. Mas custa portabilidade
      (<code>json_agg</code> e PostgreSQL), perde a verificacao em tempo de
      compilacao e renomear coluna deixa de ser refatoracao automatica. Vale
      quando o gargalo medido e o volume de dados trafegado &mdash; nao por
      padrao.</div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Desempenho sob carga</h3>
    <div class="ctl">
      <label>Metrica <select id="selPersMet">
        <option value="latencia_p95_ms">latencia p95 (ms)</option>
        <option value="latencia_media_ms">latencia media (ms)</option>
        <option value="latencia_p99_ms">latencia p99 (ms)</option>
        <option value="throughput_req_s">throughput (req/s)</option>
      </select></label>
      <label><input type="checkbox" id="chkLog" checked> escala logaritmica</label>
    </div>
    <div class="wrap"><canvas id="cPers"></canvas></div>
    <div id="tPers"></div>
    <div class="note w"><b>Como NAO ler esta tabela:</b> a diferenca entre
      <code>lazy</code>/<code>eager</code> e as cinco estrategias otimizadas e
      enorme e consistente (uma ordem de grandeza) &mdash; essa conclusao e
      solida. Ja o ranking <i>entre</i> as cinco otimizadas <b>nao e estavel</b>:
      com 25 VUs, por exemplo, o p95 do <code>join-fetch</code> foi
      110,70 &plusmn; 51,65 ms, ou seja, o desvio entre repeticoes e maior que a
      distancia ate as concorrentes. Dizer "o EntityGraph e o mais rapido"
      seria ler ruido como resultado. Elas emitem o MESMO numero de SQL (2) e a
      escolha entre elas se decide por criterios de projeto (portabilidade,
      verificacao em tempo de compilacao, produto cartesiano com varias
      colecoes), nao por alguns milissegundos de diferenca.</div>
  </div>
</section>

<!-- ============================ INDICES ============================ -->
<section id="indices">
  <h2>Item 2c &mdash; Indices</h2>
  <p class="sub">A consulta nao mudou uma letra. Só o plano de execucao mudou.</p>

  <div class="card">
    <pre>SELECT * FROM pedido WHERE cliente_id = 150 ORDER BY data_pedido DESC LIMIT 50;

CREATE INDEX idx_pedido_cliente_data ON pedido (cliente_id, data_pedido DESC);</pre>
    <div class="grid" id="kpiIdx"></div>
    <h3>Por consulta-alvo (1a execucao descartada)</h3>
    <div id="tIdxConsultas"></div>
    <div class="wrap" style="height:300px"><canvas id="cIdx"></canvas></div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">O que o EXPLAIN mostrou</h3>
    <div id="tPlanos"></div>
    <p>Duas coisas melhoraram ao mesmo tempo:</p>
    <ul>
      <li><b>Seq Scan &rarr; Index Scan:</b> em vez de ler as 300.000 linhas da
          tabela e descartar quase todas, o banco vai direto as linhas daquele
          cliente.</li>
      <li><b>O no <code>Sort</code> desapareceu:</b> o indice foi criado como
          <code>(cliente_id, data_pedido DESC)</code>, ja na ordem pedida pelo
          <code>ORDER BY</code>. Nao ha nada para ordenar em tempo de execucao
          &mdash; e por isso o indice <i>composto</i> rende muito mais que um
          indice simples em <code>cliente_id</code>.</li>
    </ul>
    <div class="note w"><b>Entao por que nao indexar todas as colunas?</b>
      Indice nao e gratuito: (1) ocupa espaco em disco; (2) todo
      INSERT/UPDATE/DELETE precisa atualizar cada indice da tabela, o que torna
      a escrita mais lenta; (3) indice com baixa seletividade (ex.:
      <code>status</code>, com 5 valores distintos em 300 mil linhas) costuma
      ser ignorado pelo planner, pois ler o indice e depois buscar as linhas
      sairia mais caro que varrer a tabela. Indice se escolhe a partir das
      consultas reais &mdash; e se confere no EXPLAIN.</div>
  </div>
</section>

<!-- ============================ CARGA ============================ -->
<section id="carga">
  <h2>Item 3 &mdash; Testes de desempenho (k6)</h2>
  <p class="sub">Metricas obrigatorias: latencia media, p95, p99, throughput e taxa de erros.</p>

  <div class="card">
    <h3 style="margin-top:0">Como ler estes numeros</h3>
    <ul>
      <li><b>VUs nao sao req/s.</b> Um usuario virtual dispara requisicoes em
          sequencia; 10 VUs podem gerar centenas de req/s. Mais VUs = mais
          concorrencia, nao necessariamente mais vazao.</li>
      <li><b>p95 e p99 importam mais que a media.</b> A media esconde a cauda:
          um p99 muito acima da media revela que uma fracao dos usuarios tem uma
          experiencia bem pior &mdash; tipicamente fila por conexao do pool,
          pausa de GC ou contencao no banco.</li>
      <li><b>Throughput que para de subir com mais VUs</b> indica saturacao: o
          gargalo deixou de ser a concorrencia e passou a ser um recurso
          (CPU, conexoes, disco).</li>
      <li><b>Aquecimento descartado:</b> cada rodada roda duas vezes e so a
          segunda e exportada. A primeira serve para a JVM compilar (JIT),
          encher o pool de conexoes e aquecer o cache de buffers do Postgres.</li>
    </ul>
  </div>

  <div class="card">
    <h3 style="margin-top:0">Todos os resultados</h3>
    <div class="ctl">
      <label>Cenario <select id="selCen"></select></label>
      <label>Metrica <select id="selMet">
        <option value="latencia_p95_ms">latencia p95 (ms)</option>
        <option value="latencia_media_ms">latencia media (ms)</option>
        <option value="latencia_p99_ms">latencia p99 (ms)</option>
        <option value="throughput_req_s">throughput (req/s)</option>
        <option value="taxa_erro_pct">taxa de erros (%)</option>
      </select></label>
    </div>
    <div class="wrap"><canvas id="cGeral"></canvas></div>
    <div id="tGeral"></div>
  </div>
</section>

<!-- ============================ ALAVANCAS ============================ -->
<section id="alav">
  <h2>O que muda o desempenho (e em que direcao)</h2>
  <p class="sub">Cada item abaixo e um parametro real do projeto. Altere, rode
     <code>scripts/run-all-tests.sh</code> e compare.</p>

  <div class="lever">
    <b>TTL do cache</b> &mdash; <code>app.cache.ttl-produto</code> em <code>application.yml</code><br>
    TTL maior = mais HIT = menos carga no banco, <b>mas</b> janela maior de dado
    desatualizado. TTL menor = dado mais fresco, menos HIT. Nao existe valor
    "certo": e a troca entre consistencia e custo, decidida pela volatilidade
    do dado.
  </div>
  <div class="lever">
    <b>Invalidacao ativa</b> &mdash; profile <code>cache-sem-invalidacao</code><br>
    Com <code>@CacheEvict</code>, a escrita corrige o cache na hora. Sem ela, o
    cache serve o valor antigo <i>por todo o TTL</i>. Rode
    <code>scripts/experimento-cache-sem-invalidacao.sh</code> para ver o preco
    errado sendo devolvido enquanto o banco ja tem o novo.
  </div>
  <div class="lever">
    <b>Estrategia de carregamento</b> &mdash; endpoint escolhido<br>
    E a alavanca de maior efeito nas listagens: sai de centenas de SQL por
    requisicao (LAZY com acesso) para 2 (JOIN FETCH / DTO). Repare que o
    <code>X-Query-Count</code> do LAZY cresce com <code>?limite=</code>,
    enquanto o das versoes otimizadas fica constante &mdash; essa e a diferenca
    entre complexidade O(N) e O(1) em numero de consultas.
  </div>
  <div class="lever">
    <b><code>?limite=</code></b> &mdash; quantos pedidos por requisicao<br>
    Aumentar o limite nao muda o numero de SQL das estrategias otimizadas, mas
    aumenta o payload. No LAZY, multiplica tambem o numero de consultas: o
    tempo cresce bem mais rapido que o volume de dados retornado.
  </div>
  <div class="lever">
    <b>Indices</b> &mdash; <code>db/10-create-index.sql</code> / <code>11-drop-index.sql</code><br>
    Ganho enorme na leitura filtrada e ordenada; custo em espaco e na escrita.
    A ordem das colunas no indice composto e decisiva: igualdade primeiro,
    intervalo/ordenacao depois.
  </div>
  <div class="lever">
    <b>Tamanho do pool de conexoes</b> &mdash; <code>spring.datasource.hikari.maximum-pool-size</code><br>
    Pool pequeno vira fila sob carga alta: a media sobe pouco e o <b>p99
    explode</b>. Pool grande demais transfere a disputa para o banco (contencao
    de CPU e locks). E tambem por isso o pool esta fixo: pool elastico mudaria
    de tamanho entre rodadas e tornaria as comparacoes incomparaveis.
  </div>
  <div class="lever">
    <b>Log de SQL</b> &mdash; profile <code>sql-log</code><br>
    Excelente para explicar o N+1 ao vivo, <b>pessimo</b> durante medicao: o I/O
    do log entra no tempo de resposta e mascara o efeito real da otimizacao. Por
    isso ele vem desligado por padrao.
  </div>
  <div class="lever">
    <b>Limites de CPU/memoria dos containers</b> &mdash; <code>docker-compose.yml</code><br>
    Estao fixos de proposito. Sem teto, o Docker daria mais recursos numa rodada
    que noutra e a variacao do ambiente se misturaria ao efeito da otimizacao.
  </div>
</section>

<!-- ============================ TESTE AO VIVO ============================ -->
<section id="aovivo">
  <h2>&#9654; Teste ao vivo</h2>
  <p class="sub">Cada botao chama a API <b>de verdade</b> e mostra os headers de diagnostico
     que ela devolveu: <code>X-Query-Count</code> (SQL executados), <code>X-Response-Time-Ms</code>
     e <code>X-Cache</code>. Nada aqui e numero salvo: tudo e medido agora.</p>

  <div class="bar">
    <span class="dot" id="lvDot"></span>
    <span id="lvStatus">verificando a API...</span>
    <span style="flex:1"></span>
    <label>API <input type="text" id="lvBase" value="http://localhost:8080" size="24"></label>
    <button class="btn" id="lvPing">Reconectar</button>
  </div>

  <!-- ---------------- 1. CACHE ---------------- -->
  <div class="card">
    <h3 style="margin-top:0">1. Cache com Redis: MISS, HIT e invalidacao</h3>
    <div class="btns">
      <button class="btn pri" id="cRoteiro">&#9654; Rodar o ciclo completo</button>
      <label>produto <input type="number" id="cId" value="10" min="1" max="2000" style="width:80px"></label>
    </div>
    <div class="btns">
      <button class="btn" data-c="limpar"><span class="step">0</span>Limpar cache</button>
      <button class="btn" data-c="com"><span class="step">1</span>GET com cache</button>
      <button class="btn" data-c="sem">GET sem cache</button>
      <button class="btn" data-c="put"><span class="step">2</span>PUT novo preco</button>
      <button class="btn" data-c="redis">Ver estatisticas do cache</button>
      <button class="btn" id="cLimparLog" style="margin-left:auto">limpar historico</button>
    </div>
    <div class="log" id="cLog"><div class="empty">Clique em "Rodar o ciclo completo" ou use os botoes passo a passo.</div></div>
  </div>

  <!-- ---------------- 2. CONSULTAS / N+1 ---------------- -->
  <div class="card">
    <h3 style="margin-top:0">2. LAZY vs EAGER vs consultas otimizadas (N+1)</h3>
    <div class="btns">
      <label>limite <select id="qLim"><option>10</option><option selected>50</option><option>100</option><option>500</option></select></label>
      <button class="btn pri" id="qTodas">&#9654; Comparar todas as estrategias</button>
      <button class="btn" id="qCresce">LAZY com limite crescente (10 &rarr; 100 &rarr; 500)</button>
    </div>
    <div class="duo">
      <div><b>Consultas SQL por requisicao</b><div id="qSql"><div class="empty">-</div></div></div>
      <div><b>Tempo no servidor (ms)</b><div id="qMs"><div class="empty">-</div></div></div>
    </div>
    <div class="note" id="qNota" style="display:none"></div>
  </div>

  <!-- ---------------- 3. INDICE ---------------- -->
  <div class="card">
    <h3 style="margin-top:0">3. Indice: EXPLAIN ANALYZE antes e depois</h3>
    <p style="margin:0;color:var(--mut)">Consulta-alvo (nao muda entre as medicoes):
      <code>SELECT * FROM pedido WHERE cliente_id = 150 ORDER BY data_pedido DESC LIMIT 50</code></p>
    <div class="btns">
      <button class="btn pri" id="iComparar">&#9654; Comparar sem indice x com indice</button>
      <button class="btn dng" id="iRemover">Remover indice</button>
      <button class="btn" id="iCriar">Criar indice</button>
      <button class="btn" id="iExplain">Rodar EXPLAIN agora</button>
      <span id="iEstado" class="tag" style="margin-left:auto"></span>
    </div>
    <div class="grid" id="iKpis" style="margin:10px 0"></div>
    <div class="duo">
      <div><b class="bad">Sem indice</b><pre class="plano" id="iAntes">-</pre></div>
      <div><b class="good">Com indice</b><pre class="plano" id="iDepois">-</pre></div>
    </div>
  </div>

  <!-- ---------------- 4. MINI CARGA ---------------- -->
  <div class="card">
    <h3 style="margin-top:0">4. Mini teste de carga: sem cache x com cache</h3>
    <div class="btns">
      <label>duracao <select id="mDur"><option value="5">5 s</option><option value="10" selected>10 s</option><option value="15">15 s</option></select></label>
      <button class="btn pri" id="mRodar">&#9654; Rodar comparacao</button>
      <span id="mFase" style="color:var(--mut)"></span>
    </div>
    <div class="prog"><div id="mProg"></div></div>
    <div class="grid" id="mRes"></div>
    <div class="note g" id="mExplica" style="display:none">
      <b>Por que a latencia quase nao muda aqui?</b> Com so 6 conexoes o banco nao esta sob
      pressao, entao evitar a consulta economiza pouco tempo &mdash; o mesmo que o k6 mediu com
      10 usuarios (p95 1,5&times; melhor). <b>O ganho do cache cresce com a carga:</b> com 200
      usuarios o k6 mediu p95 de 290 &rarr; 47 ms (6,2&times;) e throughput 3,3&times; maior.
      O que o cache garante em qualquer carga e o primeiro numero acima: o banco deixa de ser consultado.
    </div>
    <div class="note w">Este teste roda no navegador, que abre no maximo <b>6 conexoes simultaneas</b>
      por servidor: serve para <i>ilustrar</i> o efeito do cache. Os numeros oficiais (10 a 200
      usuarios, 3 repeticoes) foram medidos com <b>k6</b> e estao na aba <b>3. Testes de carga</b>.</div>
  </div>
</section>
</main>

<script>
const D = /*__DADOS__*/;
const CORES = ['#5b9cff','#3ddc97','#ffb454','#ff6b6b','#b084ff','#4ecdc4','#f78fb3','#8fd3ff'];

// Rotulos de EXIBICAO. Os arquivos em results/ mantem a tag original da rodada
// (renomear o dataset depois de coletado quebraria a rastreabilidade), mas o
// nome exibido precisa ser honesto: a variante "com-cache-frio" mediu 98,5% de
// HIT, entao chama-la de "fria" no grafico induziria o leitor a erro.
const ROTULOS = {
  'com-cache-frio': 'cache espalhado (2.000 IDs - medido 98,5% HIT)',
  'com-cache-quente': 'cache quente (50 IDs)',
  'sem-cache': 'sem cache',
};
const rotulo = (v) => ROTULOS[v] || v;
const graficos = {};

// ---------------- navegacao ----------------
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('on'));
  document.querySelectorAll('section').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  document.getElementById(b.dataset.t).classList.add('on');
});

const num = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? '-' : Number(v).toFixed(d);
const medias = D.medias || [];

function porCenario(cen) { return medias.filter(r => r.cenario === cen); }

// ---------------- grafico de linhas generico ----------------
function linhas(canvasId, dados, metrica, labelY, log) {
  const vus = [...new Set(dados.map(r => r.vus))].sort((a, b) => a - b);
  const vars = [...new Set(dados.map(r => r.variante))];
  const ds = vars.map((v, i) => ({
    label: rotulo(v),
    data: vus.map(u => {
      const r = dados.find(x => x.variante === v && x.vus === u);
      return r ? r[metrica] : null;
    }),
    borderColor: CORES[i % CORES.length],
    backgroundColor: CORES[i % CORES.length] + '22',
    tension: .25, borderWidth: 2, pointRadius: 3, spanGaps: true,
  }));
  if (graficos[canvasId]) graficos[canvasId].destroy();
  const el = document.getElementById(canvasId);
  if (!dados.length) { el.parentElement.innerHTML = '<div class="empty">Sem dados: rode scripts/run-all-tests.sh e depois gerar_graficos.py</div>'; return; }
  graficos[canvasId] = new Chart(el, {
    type: 'line',
    data: { labels: vus.map(u => u + ' VUs'), datasets: ds },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#9aa3b5', boxWidth: 12, font: { size: 11 } } } },
      scales: {
        y: { type: log ? 'logarithmic' : 'linear', title: { display: true, text: labelY, color: '#9aa3b5' },
             ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' } },
        x: { ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' } },
      },
    },
  });
}

// ---------------- tabela generica ----------------
function tabela(divId, dados) {
  const el = document.getElementById(divId);
  if (!dados.length) { el.innerHTML = '<div class="empty">Sem dados ainda.</div>'; return; }
  let h = '<table><tr><th>Variante</th><th>VUs</th><th>media (ms)</th><th>p95 (ms)</th>'
        + '<th>p99 (ms)</th><th>req/s</th><th>erros %</th><th>reps</th></tr>';
  dados.sort((a, b) => a.variante.localeCompare(b.variante) || a.vus - b.vus).forEach(r => {
    h += `<tr><td>${rotulo(r.variante)}</td><td>${r.vus}</td><td>${num(r.latencia_media_ms)}</td>`
       + `<td>${num(r.latencia_p95_ms)}</td><td>${num(r.latencia_p99_ms)}</td>`
       + `<td>${num(r.throughput_req_s)}</td><td>${num(r.taxa_erro_pct, 3)}</td>`
       + `<td>${r.repeticoes || 1}</td></tr>`;
  });
  el.innerHTML = h + '</table>';
}

// ---------------- KPIs da visao geral ----------------
(function kpis() {
  const el = document.getElementById('kpis');
  const cards = [];

  // ganho do cache (maior carga disponivel)
  const cache = porCenario('cache');
  if (cache.length) {
    const vmax = Math.max(...cache.map(r => r.vus));
    const sc = cache.find(r => r.vus === vmax && r.variante === 'sem-cache');
    const cc = cache.find(r => r.vus === vmax && r.variante === 'com-cache-quente');
    if (sc && cc && cc.latencia_p95_ms > 0) {
      const f = sc.latencia_p95_ms / cc.latencia_p95_ms;
      cards.push(`<div class="kpi"><div class="l">Cache quente vs sem cache</div>
        <div class="v ${f >= 1 ? 'good' : 'bad'}">${num(f, 1)}x</div>
        <div class="d">p95 com ${vmax} VUs: ${num(sc.latencia_p95_ms)} ms &rarr; ${num(cc.latencia_p95_ms)} ms</div></div>`);
    }
  }

  // ganho da consulta otimizada
  const pers = porCenario('persistencia');
  if (pers.length) {
    const vmax = Math.max(...pers.map(r => r.vus));
    const lz = pers.find(r => r.vus === vmax && r.variante === 'lazy');
    const cands = pers.filter(r => r.vus === vmax && r.variante !== 'lazy' && r.variante !== 'eager');
    const best = cands.sort((a, b) => a.latencia_p95_ms - b.latencia_p95_ms)[0];
    if (lz && best && best.latencia_p95_ms > 0) {
      cards.push(`<div class="kpi"><div class="l">Melhor consulta vs LAZY (N+1)</div>
        <div class="v good">${num(lz.latencia_p95_ms / best.latencia_p95_ms, 1)}x</div>
        <div class="d">${best.variante} com ${vmax} VUs: ${num(lz.latencia_p95_ms)} ms &rarr; ${num(best.latencia_p95_ms)} ms</div></div>`);
    }
  }

  // ganho do indice (k6)
  const idx = porCenario('indices');
  if (idx.length) {
    const vmax = Math.max(...idx.map(r => r.vus));
    const si = idx.find(r => r.vus === vmax && r.variante === 'sem-indice');
    const ci = idx.find(r => r.vus === vmax && r.variante === 'com-indice');
    if (si && ci && ci.latencia_p95_ms > 0) {
      cards.push(`<div class="kpi"><div class="l">Indice: ganho sob carga</div>
        <div class="v good">${num(si.latencia_p95_ms / ci.latencia_p95_ms, 1)}x</div>
        <div class="d">p95 com ${vmax} VUs: ${num(si.latencia_p95_ms)} ms &rarr; ${num(ci.latencia_p95_ms)} ms</div></div>`);
    }
  }

  // ganho do indice (EXPLAIN) -- usa a CONSULTA PRINCIPAL, nao a media das duas.
  // Misturar consultas-alvo diferentes numa media so produz um numero que nao
  // corresponde a nenhuma consulta real.
  const pcv = (D.explain && D.explain.por_consulta) || {};
  const pa = (pcv.antes || [])[0], pd = (pcv.depois || [])[0];
  if (pa && pd && pd.media > 0) {
    cards.push(`<div class="kpi"><div class="l">Indice: EXPLAIN ANALYZE</div>
      <div class="v good">${num(pa.media / pd.media, 0)}x</div>
      <div class="d">${num(pa.media, 2)} ms &rarr; ${num(pd.media, 3)} ms
        (filtro por cliente, ${pa.n} execucoes)</div></div>`);
  }

  // reducao de SQL
  const q = D.queries || {};
  if (q['lazy'] && q['join-fetch']) {
    const a = q['lazy']['100'], b = q['join-fetch']['100'];
    if (a && b) cards.push(`<div class="kpi"><div class="l">SQL por requisicao (limite=100)</div>
      <div class="v good">${a} &rarr; ${b}</div>
      <div class="d">LAZY com acesso vs JOIN FETCH</div></div>`);
  }

  el.innerHTML = cards.length ? cards.join('')
    : '<div class="empty">Rode os experimentos para preencher os indicadores.</div>';
})();

// ---------------- cache ----------------
function renderCache() {
  const m = document.getElementById('selCacheMet').value;
  const d = porCenario('cache');
  linhas('cCache', d, m, document.getElementById('selCacheMet').selectedOptions[0].text, false);
  tabela('tCache', d);
}
document.getElementById('selCacheMet').onchange = renderCache;
renderCache();

// ---------------- queries por estrategia ----------------
(function renderQueries() {
  const q = D.queries || {};
  const estrategias = Object.keys(q);
  const el = document.getElementById('cQueries');
  if (!estrategias.length) {
    el.parentElement.innerHTML = '<div class="empty">Sem dados: rode scripts/coletar-queries.sh</div>';
    document.getElementById('tQueries').innerHTML = '';
    return;
  }
  const limites = [...new Set(estrategias.flatMap(e => Object.keys(q[e])))].sort((a, b) => a - b);
  graficos['q'] = new Chart(el, {
    type: 'bar',
    data: {
      labels: estrategias,
      datasets: limites.map((l, i) => ({
        label: 'limite=' + l,
        data: estrategias.map(e => q[e][l] ?? null),
        backgroundColor: CORES[i % CORES.length],
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#9aa3b5', boxWidth: 12 } } },
      scales: {
        y: { type: 'logarithmic', title: { display: true, text: 'SQL por requisicao (log)', color: '#9aa3b5' },
             ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' } },
        x: { ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' } },
      },
    },
  });
  let h = '<table><tr><th>Estrategia</th>' + limites.map(l => `<th>limite=${l}</th>`).join('')
        + '<th>Comportamento</th></tr>';
  estrategias.forEach(e => {
    const vals = limites.map(l => q[e][l]);
    const cresce = vals.filter(v => v != null).length > 1
      && vals[vals.length - 1] > vals[0] * 2;
    h += `<tr><td>${e}</td>` + vals.map(v => `<td>${v ?? '-'}</td>`).join('')
       + `<td style="text-align:left" class="${cresce ? 'bad' : 'good'}">`
       + (cresce ? 'cresce com o limite (N+1)' : 'constante') + '</td></tr>';
  });
  document.getElementById('tQueries').innerHTML = h + '</table>';
})();

// ---------------- persistencia ----------------
function renderPers() {
  const m = document.getElementById('selPersMet').value;
  const log = document.getElementById('chkLog').checked;
  const d = porCenario('persistencia');
  linhas('cPers', d, m, document.getElementById('selPersMet').selectedOptions[0].text, log);
  tabela('tPers', d);
}
document.getElementById('selPersMet').onchange = renderPers;
document.getElementById('chkLog').onchange = renderPers;
renderPers();

// ---------------- indices ----------------
(function renderIdx() {
  const ea = (D.explain && D.explain.antes) || [], ed = (D.explain && D.explain.depois) || [];
  const kp = document.getElementById('kpiIdx');
  const pcA = (D.explain && D.explain.por_consulta) || {};
  const k1 = (pcA.antes || [])[0], k2 = (pcA.depois || [])[0];
  if (k1 && k2 && k2.media > 0) {
    kp.innerHTML = `
      <div class="kpi"><div class="l">Sem indice</div><div class="v bad">${num(k1.media, 2)} ms</div>
        <div class="d">filtro por cliente, media de ${k1.n} execucoes</div></div>
      <div class="kpi"><div class="l">Com indice</div><div class="v good">${num(k2.media, 3)} ms</div>
        <div class="d">mesma consulta, media de ${k2.n} execucoes</div></div>
      <div class="kpi"><div class="l">Reducao do tempo</div>
        <div class="v good">${num((1 - k2.media / k1.media) * 100, 1)}%</div>
        <div class="d">equivalente a ${num(k1.media / k2.media, 0)}x mais rapido</div></div>`;
  } else {
    kp.innerHTML = '<div class="empty">Rode scripts/explain-antes-depois.sh</div>';
  }

  // tabela por consulta-alvo
  const pc = (D.explain && D.explain.por_consulta) || {};
  const ta = pc.antes || [], td = pc.depois || [];
  const tdiv = document.getElementById('tIdxConsultas');
  if (ta.length && td.length) {
    let h = '<table><tr><th>Consulta</th><th>Sem indice</th><th>Com indice</th>'
          + '<th>Ganho</th><th>Reducao</th></tr>';
    ta.forEach((a, i) => {
      const b = td[i]; if (!b) return;
      h += `<tr><td style="font-family:monospace;font-size:12px">${a.consulta}</td>`
         + `<td class="bad">${num(a.media, 2)} ms</td>`
         + `<td class="good">${num(b.media, 3)} ms</td>`
         + `<td class="good">${num(a.media / b.media, 0)}x</td>`
         + `<td>${num((1 - b.media / a.media) * 100, 1)}%</td></tr>`;
    });
    tdiv.innerHTML = h + '</table>';
  } else {
    tdiv.innerHTML = '';
  }

  const el = document.getElementById('cIdx');
  if (!ea.length && !ed.length) { el.parentElement.innerHTML = ''; }
  else {
    const n = Math.max(ea.length, ed.length);
    graficos['idx'] = new Chart(el, {
      type: 'bar',
      data: {
        labels: Array.from({ length: n }, (_, i) => 'exec ' + (i + 1)),
        datasets: [
          { label: 'sem indice (ms)', data: ea, backgroundColor: '#ff6b6b' },
          { label: 'com indice (ms)', data: ed, backgroundColor: '#3ddc97' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#9aa3b5', boxWidth: 12 } },
                   title: { display: true, text: 'EXPLAIN ANALYZE: tempo de execucao por repeticao',
                            color: '#9aa3b5' } },
        scales: { y: { type: 'logarithmic', ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' },
                       title: { display: true, text: 'ms (log)', color: '#9aa3b5' } },
                  x: { ticks: { color: '#9aa3b5' }, grid: { color: '#2a2f3d' } } },
      },
    });
  }

  const p = D.planos || {};
  const div = document.getElementById('tPlanos');
  if (p.antes || p.depois) {
    div.innerHTML = `<table>
      <tr><th>No do plano</th><th>Sem indice</th><th>Com indice</th><th>Leitura</th></tr>
      <tr><td>Seq Scan on pedido</td><td class="bad">${(p.antes || {}).seq_scan ?? '-'}</td>
          <td class="good">${(p.depois || {}).seq_scan ?? '-'}</td>
          <td style="text-align:left">varredura completa da tabela: desapareceu</td></tr>
      <tr><td>Index Scan using idx</td><td>${(p.antes || {}).index_scan ?? '-'}</td>
          <td class="good">${(p.depois || {}).index_scan ?? '-'}</td>
          <td style="text-align:left">acesso direto pelo indice: passou a ser usado</td></tr>
      <tr><td>Sort</td><td class="bad">${(p.antes || {}).sort ?? '-'}</td>
          <td class="good">${(p.depois || {}).sort ?? '-'}</td>
          <td style="text-align:left">ordenacao em execucao: eliminada pelo indice DESC</td></tr>
    </table>`;
  }
})();

// ---------------- visao geral de carga ----------------
(function renderGeral() {
  const cens = [...new Set(medias.map(r => r.cenario))];
  const sel = document.getElementById('selCen');
  sel.innerHTML = cens.map(c => `<option value="${c}">${c}</option>`).join('');
  function up() {
    const d = porCenario(sel.value);
    const m = document.getElementById('selMet').value;
    linhas('cGeral', d, m, document.getElementById('selMet').selectedOptions[0].text,
           sel.value === 'persistencia');
    tabela('tGeral', d);
  }
  sel.onchange = up;
  document.getElementById('selMet').onchange = up;
  if (cens.length) up();
  else document.getElementById('tGeral').innerHTML = '<div class="empty">Sem dados ainda.</div>';
})();

// =====================================================================
// TESTE AO VIVO: chama a API real e mostra os headers de diagnostico.
// Requer o CORS liberado em config/WebConfig.java (com exposedHeaders,
// senao o navegador esconde X-Query-Count/X-Cache do JavaScript).
// =====================================================================
(function aoVivo() {
  const $ = (id) => document.getElementById(id);
  const base = () => $('lvBase').value.trim().replace(/\/+$/, '');
  const esc = (s) => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const espera = (ms) => new Promise(r => setTimeout(r, ms));
  const brl = (v) => Number(v).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
  const fmt = (v, d = 0) => Number(v).toLocaleString('pt-BR', {minimumFractionDigits: d, maximumFractionDigits: d});
  const PASSO = 900; // pausa entre passos automaticos: da tempo de narrar no video

  async function chamar(metodo, caminho, corpo) {
    const opt = {method: metodo, cache: 'no-store'};
    if (corpo !== undefined) {
      opt.headers = {'Content-Type': 'application/json'};
      opt.body = JSON.stringify(corpo);
    }
    const r = await fetch(base() + caminho, opt);
    const texto = await r.text();
    let json = null;
    try { json = JSON.parse(texto); } catch (e) { /* corpo nao-JSON */ }
    return {metodo, caminho, status: r.status, ok: r.ok, texto, json,
            sql: r.headers.get('X-Query-Count'),
            ms: r.headers.get('X-Response-Time-Ms'),
            cache: r.headers.get('X-Cache')};
  }

  // ---------- status da conexao ----------
  function status(tipo, html) {
    $('lvDot').className = 'dot ' + tipo;
    $('lvStatus').innerHTML = html;
  }
  async function ping() {
    status('', 'verificando a API...');
    try {
      const r = await chamar('GET', '/api/admin/stats');
      if (r.sql === null) {
        status('off', '<span class="warn">A API respondeu, mas os headers X- estao ocultos. ' +
               'Reinicie a aplicacao para carregar a configuracao de CORS (WebConfig).</span>');
        return;
      }
      const s = r.json;
      status('on', `<b class="good">API online</b> &middot; ${fmt(s.pedido)} pedidos &middot; ` +
             `${fmt(s.item_pedido)} itens`);
      estadoIndice(s.indicesPedido);
    } catch (e) {
      status('off', '<span class="bad">Sem conexao com a API.</span> Suba a aplicacao ' +
             '(<code>bash scripts/app-restart.sh</code>) e clique em Reconectar.');
    }
  }
  $('lvPing').onclick = ping;

  // trava os botoes enquanto um teste roda, para nao misturar medicoes
  async function trava(fn) {
    const bs = document.querySelectorAll('#aovivo .btn');
    bs.forEach(b => b.disabled = true);
    try { await fn(); }
    catch (e) { status('off', `<span class="bad">Erro: ${esc(e.message)}</span> &mdash; a API esta no ar?`); }
    finally { bs.forEach(b => b.disabled = false); }
  }

  // =================== 1. CACHE ===================
  const cId = () => Math.max(1, Math.min(2000, parseInt($('cId').value) || 10));

  function logReq(r, nota) {
    const log = $('cLog');
    if (log.querySelector('.empty')) log.innerHTML = '';
    const n = r.sql === null ? null : Number(r.sql);
    const el = document.createElement('div');
    el.className = 'req ' + (r.ok ? (r.cache || '') : 'ERRO');
    el.innerHTML =
      `<div class="u"><b>${r.metodo}</b>${esc(r.caminho)}</div>
       <div class="bdg">
         ${n !== null ? `<span class="b sql ${n === 0 ? 'z' : ''}">${n} SQL</span>` : ''}
         ${r.ms ? `<span class="b">${r.ms} ms</span>` : ''}
         ${r.cache ? `<span class="b ${r.cache}">${r.cache}</span>` : ''}
         ${!r.ok ? `<span class="b bad">HTTP ${r.status}</span>` : ''}
       </div>
       ${nota ? `<div class="nota">${nota}</div>` : ''}
       <div class="corpo">${esc(r.texto.slice(0, 400))}</div>`;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
  }

  const acoesCache = {
    async limpar() {
      const r = await chamar('DELETE', '/api/admin/cache');
      logReq(r, 'Cache esvaziado. A proxima leitura obrigatoriamente vai ao banco (MISS).');
    },
    async com() {
      const r = await chamar('GET', `/api/produtos/${cId()}/com-cache`);
      const preco = r.json && r.json.preco !== undefined ? ` Preco devolvido: <b>${brl(r.json.preco)}</b>.` : '';
      const nota = r.cache === 'HIT'
        ? `<b class="good">HIT:</b> veio do Redis. <b>0 SQL &mdash; o banco nem foi consultado.</b>${preco}`
        : `<b class="warn">MISS:</b> nao estava no Redis &rarr; foi ao banco (1 SQL) e gravou no cache.${preco}`;
      logReq(r, nota);
    },
    async sem() {
      const r = await chamar('GET', `/api/produtos/${cId()}/sem-cache`);
      logReq(r, '<b style="color:var(--ac)">BYPASS:</b> endpoint sem cache &mdash; toda leitura vai ao banco.');
    },
    async put() {
      const preco = Math.round((100 + Math.random() * 900) * 100) / 100;
      const estoque = Math.floor(Math.random() * 50);
      const r = await chamar('PUT', `/api/produtos/${cId()}`, {preco, estoque});
      logReq(r, `Preco alterado para <b>${brl(preco)}</b>. O <code>@CacheEvict</code> <b>removeu a chave</b> ` +
                `do Redis: a proxima leitura sera MISS, ja com o preco novo (o cache nao serve dado velho).`);
    },
    async redis() {
      const r = await chamar('GET', '/api/admin/cache/stats');
      const s = r.json || {};
      logReq(r, `Desde a ultima limpeza: <b>${fmt(s.hits)}</b> hits, <b>${fmt(s.misses)}</b> misses ` +
                `&rarr; hit ratio <b>${fmt(s.hitRatio, 1)}%</b>. Idas ao banco evitadas: <b>${fmt(s.hits)}</b>.`);
    },
  };
  document.querySelectorAll('[data-c]').forEach(b =>
    b.onclick = () => trava(acoesCache[b.dataset.c]));
  $('cLimparLog').onclick = () => $('cLog').innerHTML = '<div class="empty">Historico limpo.</div>';
  $('cRoteiro').onclick = () => trava(async () => {
    $('cLog').innerHTML = '';
    for (const passo of ['limpar', 'com', 'com', 'com', 'put', 'com', 'com', 'redis']) {
      await acoesCache[passo]();
      await espera(PASSO);
    }
  });

  // =================== 2. CONSULTAS / N+1 ===================
  const ESTRATEGIAS = ['lazy', 'eager', 'batch', 'dto', 'nativo', 'join-fetch', 'entity-graph', 'lazy-sem-acesso'];
  const corSql = (n) => n > 10 ? 'var(--bad)' : n > 2 ? 'var(--warn)' : 'var(--ok)';

  function barras(div, linhas, campo, sufixo, corFn) {
    const max = Math.max(...linhas.map(l => l[campo]), 1);
    $(div).innerHTML = linhas.map(l =>
      `<div class="hbar"><span>${esc(l.nome)}</span>
         <div class="t"><div class="f" style="width:${Math.max(0.6, l[campo] / max * 100)}%;background:${corFn(l)}"></div></div>
         <span class="v"><b>${fmt(l[campo], campo === 'ms' ? 1 : 0)}</b> ${sufixo}</span></div>`).join('');
  }
  function desenhar(linhas) {
    barras('qSql', linhas, 'sql', 'SQL', l => corSql(l.sql));
    barras('qMs', linhas, 'ms', 'ms', l => corSql(l.sql));
  }
  // 1a chamada de cada estrategia e descartada (aquecimento do JIT/pool);
  // mostramos a 2a, como no restante do trabalho.
  async function medir(estrategia, limite) {
    const url = `/api/pedidos/${estrategia}?limite=${limite}`;
    await chamar('GET', url);
    const r = await chamar('GET', url);
    return {sql: Number(r.sql), ms: Number(r.ms), itens: Array.isArray(r.json) ? r.json.length : 0};
  }

  $('qTodas').onclick = () => trava(async () => {
    const lim = $('qLim').value;
    const linhas = [];
    $('qNota').style.display = 'none';
    for (const e of ESTRATEGIAS) {
      linhas.push({nome: e, ...(await medir(e, lim))});
      desenhar(linhas);
    }
    const lazy = linhas.find(l => l.nome === 'lazy');
    const eg = linhas.find(l => l.nome === 'entity-graph');
    $('qNota').className = 'note g';
    $('qNota').style.display = 'block';
    $('qNota').innerHTML =
      `<b>Mesmo resultado (${lim} pedidos com cliente e itens), formas diferentes de buscar.</b> ` +
      `LAZY: <b class="bad">${lazy.sql} SQL</b> em ${fmt(lazy.ms, 1)} ms &rarr; EntityGraph: ` +
      `<b class="good">${eg.sql} SQL</b> em ${fmt(eg.ms, 1)} ms ` +
      `(<b>${fmt(lazy.sql / eg.sql)}&times; menos consultas</b>, ${fmt(lazy.ms / eg.ms, 1)}&times; mais rapido). ` +
      `O <code>lazy-sem-acesso</code> faz 1 SQL porque nao toca nos relacionamentos.`;
  });

  $('qCresce').onclick = () => trava(async () => {
    const linhas = [];
    $('qNota').style.display = 'none';
    for (const lim of [10, 100, 500]) {
      linhas.push({nome: `lazy  limite=${lim}`, ...(await medir('lazy', lim))});
      desenhar(linhas);
    }
    linhas.push({nome: 'entity-graph 500', ...(await medir('entity-graph', 500))});
    desenhar(linhas);
    $('qNota').className = 'note w';
    $('qNota').style.display = 'block';
    $('qNota').innerHTML =
      `<b>Isto e o N+1:</b> no LAZY o numero de consultas <b>cresce junto com o limite</b> ` +
      `(1 para a lista + consultas extras por pedido para cliente, itens e produtos). ` +
      `Com EntityGraph, mesmo com 500 pedidos, continuam sendo <b>${linhas[3].sql} consultas</b>.`;
  });

  // =================== 3. INDICE ===================
  let idxPresente = null;
  function estadoIndice(lista) {
    idxPresente = (lista || []).includes('idx_pedido_cliente_data');
    $('iEstado').innerHTML = idxPresente
      ? '<span class="good">&#9679; indice PRESENTE</span>'
      : '<span class="bad">&#9679; SEM indice</span>';
  }
  function realcar(linhas) {
    return linhas.map(l => {
      const e = esc(l);
      if (/Seq Scan/.test(l)) return `<span class="seq">${e}</span>`;
      if (/Index (Only )?Scan/.test(l)) return `<span class="idx">${e}</span>`;
      if (/Sort/.test(l)) return `<span class="srt">${e}</span>`;
      if (/Execution Time/.test(l)) return `<span class="tm">${e}</span>`;
      return e;
    }).join('\n');
  }
  const tempoExec = (linhas) => {
    const m = linhas.join('\n').match(/Execution Time: ([\d.]+) ms/);
    return m ? Number(m[1]) : null;
  };
  const medidas = {antes: null, depois: null};
  async function explain() {
    const r = await chamar('GET', '/api/admin/explain?clienteId=150');
    estadoIndice(r.json.indicesPedido);
    const lado = idxPresente ? 'depois' : 'antes';
    $(lado === 'antes' ? 'iAntes' : 'iDepois').innerHTML = realcar(r.json.plano);
    medidas[lado] = tempoExec(r.json.plano);
    kpisIndice();
  }
  async function indice(acao) {
    $('iEstado').innerHTML = acao === 'criar' ? 'criando indice em 300 mil linhas...' : 'removendo indice...';
    const r = await chamar('POST', `/api/admin/indices/${acao}`);
    estadoIndice(r.json.indicesPedido);
  }
  function kpisIndice() {
    const {antes, depois} = medidas;
    const k = (l, v, d, cls = '') => `<div class="kpi"><div class="l">${l}</div><div class="v ${cls}">${v}</div><div class="d">${d}</div></div>`;
    $('iKpis').innerHTML =
      k('Sem indice', antes === null ? '-' : fmt(antes, 3) + ' ms', 'Seq Scan: le a tabela inteira', 'bad') +
      k('Com indice', depois === null ? '-' : fmt(depois, 3) + ' ms', 'Index Scan: vai direto as linhas', 'good') +
      k('Ganho', antes && depois ? fmt(antes / depois, 0) + '&times; mais rapido' : '-',
        'mesma consulta, so o indice mudou', 'good');
  }
  $('iRemover').onclick = () => trava(() => indice('remover'));
  $('iCriar').onclick = () => trava(() => indice('criar'));
  $('iExplain').onclick = () => trava(explain);
  $('iComparar').onclick = () => trava(async () => {
    $('iAntes').textContent = 'removendo o indice...';
    $('iDepois').textContent = '-';
    medidas.antes = medidas.depois = null;
    kpisIndice();
    await indice('remover');
    $('iAntes').textContent = 'rodando EXPLAIN ANALYZE...';
    await explain();
    await espera(PASSO);
    $('iDepois').textContent = 'criando o indice...';
    await indice('criar');
    $('iDepois').textContent = 'rodando EXPLAIN ANALYZE...';
    await explain();
  });
  kpisIndice();

  // =================== 4. MINI CARGA ===================
  const pct = (arr, p) => {
    const s = [...arr].sort((a, b) => a - b);
    return s.length ? s[Math.min(s.length - 1, Math.floor(p / 100 * s.length))] : 0;
  };
  const idAleatorio = () => 1 + Math.floor(Math.random() * 50);

  async function carga(rota, segundos, prog0) {
    const W = 6; // limite de conexoes por servidor do navegador
    const inicio = performance.now(), fim = inicio + segundos * 1000;
    const lat = []; let erros = 0;
    const tick = setInterval(() => {
      const f = Math.min(1, (performance.now() - inicio) / (segundos * 1000));
      $('mProg').style.width = (prog0 + f * 50) + '%';
    }, 150);
    async function worker() {
      while (performance.now() < fim) {
        const t = performance.now();
        try {
          const r = await fetch(base() + rota(), {cache: 'no-store'});
          await r.arrayBuffer();
          if (!r.ok) erros++;
        } catch (e) { erros++; }
        lat.push(performance.now() - t);
      }
    }
    await Promise.all(Array.from({length: W}, worker));
    clearInterval(tick);
    const dur = (performance.now() - inicio) / 1000;
    return {req: lat.length, rps: lat.length / dur, p50: pct(lat, 50), p95: pct(lat, 95),
            p99: pct(lat, 99), erros};
  }

  $('mRodar').onclick = () => trava(async () => {
    const seg = Number($('mDur').value);
    $('mRes').innerHTML = '';
    $('mFase').textContent = `1/2: SEM cache por ${seg} s...`;
    const sem = await carga(() => `/api/produtos/${idAleatorio()}/sem-cache`, seg, 0);
    $('mFase').textContent = 'aquecendo o cache (produtos 1 a 50)...';
    await chamar('DELETE', '/api/admin/cache');
    for (let id = 1; id <= 50; id++) await fetch(`${base()}/api/produtos/${id}/com-cache`, {cache: 'no-store'});
    $('mFase').textContent = `2/2: COM cache por ${seg} s...`;
    const com = await carga(() => `/api/produtos/${idAleatorio()}/com-cache`, seg, 50);
    const st = (await chamar('GET', '/api/admin/cache/stats')).json || {};
    $('mProg').style.width = '100%';
    $('mFase').textContent = 'concluido.';
    const k = (l, v, d, cls = '') => `<div class="kpi"><div class="l">${l}</div><div class="big ${cls}">${v}</div><div class="d">${d}</div></div>`;
    // sem cache: cada requisicao = 1 SQL. com cache: so os MISS vao ao banco.
    const bancoSem = sem.req, bancoCom = st.acessosBanco ?? 0;
    $('mRes').innerHTML =
      k('Consultas ao banco', `${fmt(bancoSem)} &rarr; <span class="good">${fmt(bancoCom)}</span>`,
        `<b class="good">${fmt(100 - bancoCom / Math.max(1, com.req) * 100, 1)}% das leituras</b> nem chegaram ao PostgreSQL`) +
      k('Hit ratio (com cache)', `<span class="good">${fmt(st.hitRatio, 1)}%</span>`,
        `${fmt(st.hits)} leituras atendidas pelo Redis`) +
      k('Throughput', `${fmt(sem.rps)} &rarr; <span class="good">${fmt(com.rps)}</span>`,
        `req/s &middot; ${fmt(com.rps / sem.rps, 1)}&times;`) +
      k('Latencia p95', `${fmt(sem.p95, 1)} &rarr; <span class="good">${fmt(com.p95, 1)}</span>`,
        `ms &middot; ${fmt(sem.p95 / com.p95, 1)}&times; &middot; erros: ${sem.erros + com.erros}`);
    $('mExplica').style.display = 'block';
  });

  ping();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
