# Otimização de Web Services: cache, consultas e testes de desempenho

Trabalho Prático A2 — **Análise e Otimização de Sistemas** — Universidade Veiga de Almeida

API REST de um sistema de vendas em **Spring Boot 3.5 / Java 21**, com
**PostgreSQL 16** e **Redis 7**, usada para medir experimentalmente o efeito de
três técnicas de otimização sobre **300 mil pedidos** e **1,05 milhão de itens**.

---

## Sumário

- [Resultados em uma página](#resultados-em-uma-página)
- [Como executar](#como-executar)
- [O painel de resultados](#o-painel-de-resultados)
- [Arquitetura](#arquitetura)
- [Como cada número é comprovado](#como-cada-número-é-comprovado)
- [Item 1 — Cache com Redis](#item-1--cache-com-redis)
- [Item 2a — LAZY vs EAGER e o N+1](#item-2a--lazy-vs-eager-e-o-n1)
- [Item 2b — Consultas otimizadas](#item-2b--consultas-otimizadas)
- [Item 2c — Índices](#item-2c--índices)
- [Item 3 — Testes de desempenho](#item-3--testes-de-desempenho)
- [Endpoints](#endpoints)
- [Conclusões](#conclusões)
- [Documentação complementar](#documentação-complementar)

---

## Resultados em uma página

Todos os números abaixo foram **medidos nesta máquina** e estão em `results/`.
Nenhum é estimado.

### Consultas SQL por requisição (`limite=50`)

| Estratégia | SQL por requisição | Tempo no servidor | Comportamento |
|---|---:|---:|---|
| LAZY com acesso | **271** | 1.127 ms | cresce com o limite → **N+1** |
| EAGER | **101** | 255 ms | também N+1, e pago sempre |
| `@BatchSize(100)` | 5 | 163 ms | 1 + ⌈N/size⌉ |
| SQL nativo (`json_agg`) | **2** | 100 ms | constante |
| Projeção DTO | **2** | 219 ms | constante |
| JOIN FETCH | **2** | 26 ms | constante |
| `@EntityGraph` | **2** | **22 ms** | constante |
| LAZY sem acesso | **1** | 8 ms | nada é tocado |

> **LAZY → EntityGraph: 271 → 2 consultas (−99,3%) e 1.127 → 22 ms (51× mais
> rápido).** Mesmo DTO, mesmo resultado.

### Índice (`EXPLAIN ANALYZE`, 5 execuções por consulta, 1ª descartada)

| Consulta-alvo | Sem índice | Com índice | Ganho |
|---|---:|---:|---:|
| `WHERE cliente_id = ? ORDER BY data_pedido DESC` | 19,13 ms | **0,257 ms** | **74×** (−98,7%) |
| `WHERE data_pedido BETWEEN ? AND ? AND status = ?` | 16,96 ms | **0,304 ms** | **56×** (−98,2%) |

| Nó do plano | Sem índice | Com índice |
|---|---:|---:|
| `Seq Scan on pedido` | 10 | **0** |
| `Index Scan using idx_...` | 0 | **10** |
| `Sort` | 10 | **0** |

### Cache

| | Resultado |
|---|---|
| 1ª leitura (MISS) | `X-Cache: MISS`, `X-Query-Count: 1` |
| 2ª leitura (HIT) | `X-Cache: HIT`, **`X-Query-Count: 0`** |
| Após `PUT` | chave invalidada (`TTL = -2`), próxima leitura é MISS com o dado novo |

### Sob carga — média de **3 repetições** por ponto

**Cache** (`sem-cache` → `com-cache-quente`):

| VUs | p95 sem | p95 com | Ganho | Throughput sem → com |
|---:|---:|---:|---:|---|
| 10 | 8,25 ms | 5,34 ms | 1,5× | 1.603 → 2.620 req/s (1,6×) |
| 50 | 55,29 ms | 13,54 ms | 4,1× | 1.875 → 5.378 req/s (2,9×) |
| 100 | 124,26 ms | 27,96 ms | 4,4× | 1.869 → 5.653 req/s (3,0×) |
| **200** | **290,21 ms** | **46,80 ms** | **6,2×** | 1.966 → 6.502 req/s (**3,3×**) |

**Índice** (`sem-indice` → `com-indice`):

| VUs | p95 sem | p95 com | Ganho | Throughput sem → com |
|---:|---:|---:|---:|---|
| 10 | 295,75 ms | 7,95 ms | **37,2×** | 49 → 1.578 req/s (32×) |
| 50 | 1.428,88 ms | 59,11 ms | 24,2× | 53 → 1.801 req/s (34×) |
| 100 | 3.167,46 ms | 121,16 ms | 26,1× | 56 → 1.981 req/s (36×) |
| **200** | **6.798,60 ms** | **332,76 ms** | **20,4×** | 62 → 1.926 req/s (**31×**) |

> **O ganho do cache CRESCE com a carga** (1,5× → 6,2×): com pouca
> concorrência o banco dá conta, e o cache quase não importa; sob pressão, cada
> consulta evitada vale mais. **Já o índice é decisivo em qualquer carga** —
> 37× até com 10 VUs, porque o `Seq Scan` em 300 mil linhas é caro mesmo sem
> concorrência. É a diferença entre uma otimização que alivia *contenção* e uma
> que elimina *trabalho*.

> **O throughput denuncia a saturação:** sem índice ele **estaciona em ~50-60
> req/s** em todos os níveis de carga. Dobrar os usuários não aumenta a vazão,
> só a fila — por isso o p95 sai de 296 ms para 6,8 s. Com índice, a vazão
> acompanha a carga até ~1.900-2.000 req/s.

> **A prova do cache é `X-Query-Count: 0`.** Latência menor poderia ser
> coincidência; zero SQL não tem outra explicação: o banco não foi tocado.

Os números sob carga (latência média, p95, p99, throughput e taxa de erro, em
4 níveis de VUs × 3 repetições) estão em `results/resumo.csv` e no painel.

---

## Como executar

### Pré-requisitos

Docker, JDK 21, k6 e Python com pandas/matplotlib.

```bash
# Windows (winget)
winget install Microsoft.OpenJDK.21
winget install GrafanaLabs.k6          # ATENÇÃO: o id é GrafanaLabs.k6, não Grafana.k6
python3 -m pip install --user pandas matplotlib
```

> **Maven não é necessário**: o projeto usa o wrapper (`mvnw`).

### 1. Subir a infraestrutura

```bash
docker compose up -d --wait
```

O schema (`db/01-schema.sql`) e o seed (`db/02-seed.sql`) rodam automaticamente
na primeira inicialização. O seed usa `setseed(0.42)`, portanto é
**determinístico**: a mesma execução gera exatamente os mesmos dados.

> **Portas**: `55432` (Postgres) e `16379` (Redis) no host, para não colidir com
> instâncias já existentes na máquina.

### 2. Subir a aplicação

```bash
bash scripts/app-restart.sh      # sobe, aguarda o health e grava results/app.log
curl -s http://localhost:8080/api/admin/stats
```

### 3. Rodar os experimentos

```bash
bash scripts/experimento-cache.sh            # item 1: MISS vs HIT, TTL, invalidação
bash scripts/experimento-cache-sem-invalidacao.sh   # o risco de NÃO invalidar
bash scripts/coletar-queries.sh              # item 2: X-Query-Count por estratégia
bash scripts/explain-antes-depois.sh         # item 2c: EXPLAIN sem/com índice
bash scripts/run-all-tests.sh                # item 3: bateria k6 completa
```

### 4. Gerar relatório e painel

```bash
python3 scripts/gerar_graficos.py      # results/resumo.csv + docs/img/*.png
python3 scripts/gerar_dashboard.py     # docs/dashboard.html
```

---

## O painel de resultados

```bash
python3 scripts/gerar_dashboard.py
start docs/dashboard.html        # Windows
```

**`docs/dashboard.html`** é uma página única (sem servidor, sem build) com oito
abas:

| Aba | Conteúdo |
|---|---|
| **Visão geral** | KPIs calculados dos resultados reais + volume de dados |
| **Como funciona** | caminho de uma requisição e onde cada técnica atua |
| **1. Cache** | ciclo HIT/MISS/invalidação, TTL por volatilidade, gráfico sob carga |
| **2a. LAZY vs EAGER** | gráfico de SQL por requisição e por que o N+1 ocorre |
| **2b. Consultas otimizadas** | comparação das 5 estratégias, com os trade-offs |
| **2c. Índices** | antes/depois do `EXPLAIN` e a tabela de nós do plano |
| **3. Testes de carga** | gráficos interativos (métrica e cenário selecionáveis) |
| **O que muda o desempenho** | cada parâmetro ajustável e o efeito esperado |

Os gráficos são interativos (Chart.js): troque a métrica entre média/p95/p99/
throughput e alterne a escala logarítmica. **A página lê os dados de
`results/`** — se um experimento não foi executado, a seção correspondente diz
isso em vez de mostrar número inventado.

---

## Arquitetura

```
  curl / k6
     |
     v
  [ Filtro de diagnóstico ]  <-- mede o tempo e conta os SQL da requisição
     |                           X-Query-Count / X-Response-Time-Ms / X-Cache
     v
  [ Controller ] -> [ Service ] ---------> [ Redis ]   TÉCNICA 1: se está no
     |                  |                   (cache)    cache, termina aqui: 0 SQL
     |                  | (MISS)
     |                  v
     |            [ Repository / JPA ]                 TÉCNICA 2: a estratégia
     |                  |                              decide QUANTOS SQL
     |                  v
     |            [ datasource-proxy ]  <-- conta cada SQL
     |                  v
     +------------> [ PostgreSQL ]                     TÉCNICA 3: o índice decide
                                                        o custo de CADA SQL
```

**As três técnicas atacam níveis diferentes** — por isso se somam em vez de
competir:

| Técnica | O que reduz |
|---|---|
| Cache | o número de requisições que **chegam ao banco** |
| Estratégia de consulta | o número de SQL **por requisição** |
| Índice | o custo de **cada SQL** |

### Modelo de dados (5 tabelas relacionadas)

```
categoria 1---N produto
                   |
                   | N
  cliente 1---N pedido 1---N item_pedido
```

| Tabela | Registros | Papel no experimento |
|---|---:|---|
| `categoria` | 20 | baixa volatilidade → cache com TTL longo |
| `produto` | 2.000 | preço/estoque voláteis → cache com TTL curto |
| `cliente` | 20.000 | filtro da consulta-alvo dos índices |
| `pedido` | 300.000 | tabela principal: `Seq Scan` aqui custa caro |
| `item_pedido` | 1.050.000 | coleção que provoca o N+1 |

> `pedido` nasce **sem índice** em `cliente_id`/`data_pedido`. É deliberado: o
> PostgreSQL não indexa chaves estrangeiras automaticamente, e precisávamos do
> estado "antes" para medir o ganho.

---

## Como cada número é comprovado

Toda resposta da API carrega:

| Header | Significado |
|---|---|
| `X-Query-Count` | quantos comandos SQL aquela requisição executou |
| `X-Response-Time-Ms` | tempo medido no servidor (sem latência de rede) |
| `X-Cache` | `HIT`, `MISS` ou `BYPASS` |

```bash
curl -i http://localhost:8080/api/pedidos/lazy?limite=10 | grep -i "^X-"
```

**Implementação:** `diag/DataSourceProxyConfig.java` (intercepta o JDBC via
datasource-proxy) → `diag/QueryCountHolder.java` (contador em `ThreadLocal`) →
`diag/DiagnosticoFilter.java` (escreve os headers).

> **Por que `ThreadLocal`?** No Spring MVC cada requisição é atendida por uma
> thread; guardando o contador na thread, cada SQL é atribuído à requisição que
> o disparou — mesmo com 200 usuários simultâneos.

---

## Item 1 — Cache com Redis

### O que foi cacheado, e por quê

| Dado | Leitura | Volatilidade | TTL | Decisão |
|---|---|---|---|---|
| Detalhe do produto | muito alta | média (preço/estoque) | 60 s | cachear + invalidar no update |
| Lista de categorias | alta | baixíssima | 10 min | cachear com TTL longo |

> **A regra que define o TTL:** o TTL é o **tamanho máximo da janela de
> inconsistência**. Categoria quase nunca muda → 10 min é seguro. Preço muda →
> 60 s, porque preço errado por 10 minutos é prejuízo.

### Padrão usado: cache-aside

```
LEITURA:  procura no cache -> achou? devolve (HIT)
                           -> não achou? lê o banco e grava no cache (MISS)
ESCRITA:  grava no banco   -> INVALIDA a chave
```

### `@CacheEvict` em vez de `@CachePut`

`@CachePut` gravaria no cache o valor que a aplicação **supõe** ter gravado. Com
trigger, valor default ou escrita concorrente, o cache passaria a servir um
valor que **nunca existiu** no banco. O evict apaga; a próxima leitura
reconstrói a partir da fonte da verdade. Custo: um MISS extra. Benefício: o
cache não mente.

**O risco de não invalidar** está demonstrado em
`results/cache/sem-invalidacao.txt` (gerado pelo profile
`cache-sem-invalidacao`): a leitura devolve o preço antigo até o TTL expirar.

### Duas armadilhas que custaram tempo

**1. Self-invocation anula o `@Cacheable`.** A anotação é implementada por um
**proxy** em volta do bean. Um método da mesma classe chamando o método anotado
**não passa pelo proxy** — e o cache nunca é consultado. Era exatamente o bug da
primeira versão: `X-Cache: MISS` em toda requisição, **sem nenhum erro no log**.
Correção: separar a instrumentação em `service/CacheInstrumentado.java`.

**2. `record` + `activateDefaultTyping(NON_FINAL)` não serializa.** O compilador
marca `record` como `final`, então o Jackson não grava o campo de tipo e a
leitura falha. Correção: serializer **tipado por cache** em `CacheConfig.java` —
o que também deixou o JSON legível no Redis:

```bash
docker exec a2-redis redis-cli GET "produtos::10"
# {"id":10,"nome":"Produto 10","preco":1234.56,...}
docker exec a2-redis redis-cli TTL "produtos::10"
```

---

## Item 2a — LAZY vs EAGER e o N+1

`entity/lazy/` e `entity/eager/` mapeiam as **mesmas tabelas** duas vezes.

> **Por que duplicar as entidades?** No JPA o `FetchType` faz parte do
> *mapeamento*: uma classe não pode ser LAZY num endpoint e EAGER noutro. Para
> comparar as duas estratégias no mesmo banco, não há alternativa. Ambas são
> `@Immutable`, pois existem só para o experimento.

### O N+1, medido

```bash
for l in 10 100 500; do
  curl -si "http://localhost:8080/api/pedidos/lazy?limite=$l" | grep -i x-query-count
done
```

O número **cresce com o limite**:

```
 1  SELECT * FROM pedido ORDER BY id LIMIT 100         <- a "1"
 +  SELECT * FROM cliente     WHERE id = ?        x100  <- os "N"
 +  SELECT * FROM item_pedido WHERE pedido_id = ? x100
 +  SELECT * FROM produto     WHERE id = ?        x...
```

### Dois achados que o enunciado pede para observar

**EAGER não resolve o N+1.** Em JPQL sem fetch explícito, o Hibernate busca os
pedidos e depois resolve cada coleção EAGER — uma query por pedido (101 com
`limite=50`). A diferença é que agora o custo é pago **sempre**, mesmo quando o
endpoint não usa os relacionamentos.

**A vantagem real do LAZY** aparece em `/lazy-sem-acesso`: **1 consulta**,
independentemente do limite. LAZY é um bom *default*; o erro não é o LAZY, é
percorrer relacionamentos sem ter planejado como carregá-los.

---

## Item 2b — Consultas otimizadas

| Estratégia | Como funciona | Quando preferir |
|---|---|---|
| `JOIN FETCH` | uma query com join | o caso geral |
| `@EntityGraph` | mesmo plano, declarado por atributos | reaproveitar a query variando o que carregar |
| `@BatchSize` | agrupa os proxies em `WHERE id IN (...)` | **várias coleções**: evita o produto cartesiano |
| Projeção DTO | colunas soltas, sem entidades gerenciadas | telas de leitura |
| SQL nativo (`json_agg`) | o banco monta o array de itens | payload grande |

### A armadilha da paginação com `JOIN FETCH`

Com join de **coleção**, um pedido vira N linhas (uma por item). Aplicar `LIMIT`
direto cortaria no meio dos itens, retornando pedidos incompletos. O Hibernate
detecta isso e, para não errar, traz **tudo** para a memória e pagina em Java
(aviso `HHH90003004`) — anulando o ganho.

**Solução — padrão de 2 etapas** (`repository/PedidoOtimizadoRepository.java`):

1. buscar só os **IDs** da página (`LIMIT` seguro, sem join de coleção);
2. fazer o `JOIN FETCH` **por esses IDs**.

### SQL nativo compensou?

Em número de SQL, **empata** com JOIN FETCH (ambos constantes). Ganha em
tráfego, por não repetir os dados do pedido em cada linha de item. **Mas custa:**
portabilidade (`json_agg` é PostgreSQL), nenhuma verificação em tempo de
compilação, e renomear coluna deixa de ser refatoração automática.

> **Conclusão honesta:** vale quando o gargalo **medido** é o volume trafegado.
> Não como padrão.

---

## Item 2c — Índices

```sql
-- consulta-alvo (não muda uma letra entre as duas medições)
SELECT * FROM pedido WHERE cliente_id = 150 ORDER BY data_pedido DESC LIMIT 50;

CREATE INDEX idx_pedido_cliente_data ON pedido (cliente_id, data_pedido DESC);
```

**Resultado: 19,13 ms → 0,257 ms (74× mais rápido).** Duas coisas melhoraram:

- **`Seq Scan` → `Index Scan`**: em vez de ler 300.000 linhas e descartar quase
  todas, o banco vai direto às linhas daquele cliente;
- **o nó `Sort` desapareceu**: o índice foi criado em `(cliente_id,
  data_pedido DESC)`, já na ordem pedida pelo `ORDER BY`. Nada a ordenar em
  tempo de execução.

> **A ordem das colunas é decisiva**: igualdade primeiro, intervalo/ordenação
> depois. É por isso que o índice **composto** rende muito mais que um índice
> simples em `cliente_id`.

### Por que não indexar tudo

1. **Espaço** em disco.
2. **Escrita mais lenta**: cada `INSERT`/`UPDATE`/`DELETE` atualiza **todos** os
   índices da tabela.
3. **Índice inútil**: com baixa seletividade (ex.: `status`, 5 valores em 300
   mil linhas), o planner **ignora** o índice — ler o índice e depois buscar as
   linhas sairia mais caro que varrer a tabela.

> **Por que descartar a 1ª execução do `EXPLAIN`?** O PostgreSQL mantém cache de
> blocos (*shared buffers*): a primeira execução lê do disco, as seguintes da
> memória. Comparar uma primeira com uma quinta mediria o cache, não o índice.

---

## Item 3 — Testes de desempenho

```bash
bash scripts/run-all-tests.sh
```

**4 níveis de carga × 3 repetições**, com aquecimento descartado. Métricas
coletadas: latência média, **p95**, **p99**, throughput e taxa de erro.

### Como ler os números

- **VUs ≠ req/s.** Um usuário virtual dispara requisições em sequência; 10 VUs
  podem gerar centenas de req/s. Mais VUs = mais **concorrência**, não
  necessariamente mais vazão.
- **p95/p99 importam mais que a média.** Média de 50 ms com p99 de 2.000 ms
  significa que 1 em 100 usuários esperou 2 segundos. p99 alto indica fila no
  pool, pausa de GC ou contenção no banco.
- **Throughput que para de subir** com mais VUs indica saturação.

### Controle de variáveis

Para a comparação ser honesta, só **uma** coisa pode mudar entre rodadas:

| Variável | Como foi fixada |
|---|---|
| CPU/memória | limites fixos no `docker-compose.yml` |
| pool de conexões | `maximum-pool-size = minimum-idle = 20` (pool fixo) |
| volume de dados | seed determinístico (`setseed(0.42)`) |
| estado do cache | limpo/pré-aquecido explicitamente antes de cada rodada |
| estado do índice | criado/removido pelo runner |
| log de SQL | desligado (profile `sql-log` só para demonstração) |
| aquecimento | execução separada e **descartada** |
| repetições | 3 por ponto, com desvio-padrão do p95 registrado |

> **Por que o aquecimento roda em processo separado?** Porque
> `--summary-export` agrega **todas** as métricas da execução: o aquecimento
> entraria na média e nos percentis. Em processos separados, o JSON contém só a
> medição.

### Três decisões forçadas pelos dados

**1. `generate_statistics` foi silenciado.** O
`StatisticalLoggingSessionEventListener` imprime um bloco "Session Metrics" por
sessão: sob carga gerou **34 MB de log em poucos minutos**, e o I/O entrou no
tempo de resposta — a exata distorção que o trabalho diz evitar. As estatísticas
continuam disponíveis via Actuator; só o log foi desligado.

**2. O runner descarta rodadas inválidas.** Uma rodada contra a aplicação
indisponível gera um JSON com ~100% de erro que, no CSV, **se parece com um dado
válido**. Agora o runner verifica o health antes de medir e renomeia para
`.invalido` qualquer rodada com taxa de erro acima de 50%.

**3. O cenário de persistência usa carga menor.** A variante LAZY leva ~1.100 ms
por requisição (271 consultas). Com 200 VUs ela não "degrada": **satura**, a
fila estoura o timeout e a rodada mediria o timeout do k6, não o custo do N+1.
Com `limite=20` e até 50 VUs a comparação entre estratégias continua válida e o
servidor permanece responsivo.

---

## Endpoints

### Diagnóstico

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/admin/stats` | contagem por tabela e índices existentes |
| `GET` | `/api/admin/cache/stats` | hits, misses, evictions, hit ratio |
| `DELETE` | `/api/admin/cache` | limpa o cache (para medir MISS) |
| `GET` | `/actuator/health` | saúde da aplicação |

### Item 1 — Cache

| Método | Rota |
|---|---|
| `GET` | `/api/produtos/{id}/sem-cache` |
| `GET` | `/api/produtos/{id}/com-cache` |
| `PUT` | `/api/produtos/{id}` (invalida o cache) |
| `GET` | `/api/categorias/sem-cache` · `/api/categorias/com-cache` |

### Item 2 — Consultas (todas aceitam `?limite=`)

| Rota | SQL por requisição |
|---|---|
| `/api/pedidos/lazy` | N+1 (cresce) |
| `/api/pedidos/eager` | N+1 (cresce) |
| `/api/pedidos/lazy-sem-acesso` | 1 |
| `/api/pedidos/join-fetch` | 2 |
| `/api/pedidos/entity-graph` | 2 |
| `/api/pedidos/batch` | 1 + ⌈N/100⌉ |
| `/api/pedidos/dto` | 2 |
| `/api/pedidos/nativo` | 2 |

### Item 2c — Consultas-alvo dos índices

| Rota |
|---|
| `/api/clientes/{id}/pedidos?limite=50` |
| `/api/pedidos/periodo?inicio=&fim=&status=&limite=` |

> A coleção **`postman/A2.postman_collection.json`** (22 requisições,
> organizadas por item do enunciado) está pronta para importar.

---

## Conclusões

1. **A maior redução de trabalho veio da otimização das consultas.** Eliminar o
   N+1 levou de 271 para 2 consultas por requisição (−99,3%) e de 1.127 ms para
   22 ms (51×) — sem trocar o banco e sem adicionar infraestrutura.

2. **O índice foi o maior ganho por esforço.** Uma linha de SQL, nenhuma
   mudança na aplicação, 74× mais rápido na consulta-alvo. Mas índice tem custo
   em espaço e em escrita: indexar tudo é contraproducente.

3. **O cache ganhou 6,2× no p95 com 200 VUs** (290,21 → 46,80 ms) e **3,3× no
   throughput** (1.966 → 6.502 req/s) — e, principalmente, **o ganho cresce com
   a carga** (1,5× com 10 VUs → 6,2× com 200). Com cache quente,
   `X-Query-Count: 0`: o banco nem é consultado.

   **E uma correção honesta de método:** a variante que eu havia chamado de
   "cache frio" **não** mede o custo do MISS. A medição mostrou hit ratio de
   **98,5%** nela — com 2.000 IDs e ~2.300 req/s, o cache aquece em **0,86 s de
   uma rodada de 25 s**. Ela mede o efeito da *cardinalidade das chaves*
   (50 vs 2.000 IDs), e por isso foi renomeada para `com-cache-espalhado`.
   O custo real do MISS exige medição determinística, feita em
   `scripts/experimento-custo-miss.sh` (cache limpo antes de **cada**
   requisição): aí sim o MISS paga 3 idas (Redis + banco + Redis) contra 1 ida
   de quem não tem cache.

   > **Lição de método:** teste de carga é a ferramenta errada para medir o
   > custo do MISS — qualquer faixa de chaves que caiba na tabela aquece em
   > menos de um segundo. Rótulo de variante não é prova; o hit ratio é.

4. **As três técnicas se somam, porque atacam níveis diferentes** — requisições
   que chegam ao banco, SQL por requisição, custo de cada SQL. A ordem de ataque
   importa: primeiro **medir**, depois reduzir o número de consultas, depois
   tornar cada consulta mais barata, e só então cachear. Cachear uma consulta mal
   escrita só esconde o problema até o primeiro MISS.

5. **Nenhuma dessas conclusões seria possível sem medição.** O `X-Query-Count`
   foi o que transformou "acho que melhorou" em "passou de 271 para 2" — e foi
   também o que revelou os dois bugs silenciosos deste projeto: o cache que não
   cacheava (self-invocation) e o log que distorcia a medição.

---

## Documentação complementar

| Arquivo | Conteúdo |
|---|---|
| **`docs/dashboard.html`** | **painel interativo com todos os resultados e as explicações** |
| `docs/APRENDIZADO.md` | cada conceito explicado, onde ver no código e como observar ao vivo |
| `docs/ROTEIRO_VIDEO.md` | roteiro cronometrado da apresentação (≤ 7 min) |
| `results/resumo.csv` | todas as rodadas do k6 consolidadas |
| `results/queries.txt` | `X-Query-Count` por estratégia e limite |
| `results/indices/` | saída completa do `EXPLAIN` antes/depois |
| `results/cache/` | experimento de cache e o caso sem invalidação |
| `docs/img/` | gráficos gerados (PNG) |

### Estrutura do projeto

```
a2-otimizacao/
├── docker-compose.yml          Postgres 16 + Redis 7, com recursos limitados
├── db/                         schema, seed determinístico, create/drop index
├── app/src/main/java/br/uva/aos/
│   ├── diag/                   contador de SQL, status de cache, filtro
│   ├── entity/{lazy,eager,batch}/   as mesmas tabelas, 3 mapeamentos
│   ├── repository/             JPQL, EntityGraph, projeção, SQL nativo
│   ├── service/                regras + @Cacheable/@CacheEvict
│   ├── controller/             endpoints por técnica
│   └── config/                 CacheConfig (TTL por cache)
├── k6/                         3 cenários de carga
├── scripts/                    experimentos, runner, gráficos, dashboard
├── results/                    saídas das execuções
├── docs/                       dashboard, aprendizado, roteiro, imagens
└── postman/                    coleção com 22 requisições
```
