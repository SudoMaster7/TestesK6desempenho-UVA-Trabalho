# Guia de aprendizado

Este documento explica **cada conceito** usado no trabalho, mostra **onde ver
no código** e **como observar ao vivo**. A ideia é que você consiga reproduzir e
defender qualquer número do relatório.

---

## 0. A ferramenta que torna tudo visível: o contador de SQL

Antes de qualquer otimização, é preciso **medir**. Toda resposta da API carrega
três headers:

| Header | Significado |
|---|---|
| `X-Query-Count` | quantos comandos SQL aquela requisição executou |
| `X-Response-Time-Ms` | tempo medido no servidor (sem latência de rede) |
| `X-Cache` | `HIT` (veio do cache), `MISS` (foi ao banco), `BYPASS` (endpoint sem cache) |

**Onde ver no código:** `diag/DataSourceProxyConfig.java` (intercepta o JDBC via
datasource-proxy), `diag/QueryCountHolder.java` (contador por thread) e
`diag/DiagnosticoFilter.java` (escreve os headers).

**Como observar ao vivo:**
```bash
curl -i http://localhost:8080/api/pedidos/lazy?limite=10 | grep -i "^X-"
```

**Por que `ThreadLocal`?** No Spring MVC cada requisição é atendida por uma
thread. Guardando o contador na thread, cada SQL é atribuído à requisição que o
disparou — mesmo com 200 usuários simultâneos.

> **Lição**: otimização sem medição é chute. O `X-Query-Count` é o que
> transforma "acho que melhorou" em "passou de 525 para 2".

---

## 1. Cache

### 1.1 Cache-aside (look-aside)

O padrão usado aqui:

```
LEITURA:  procura no cache -> achou?  devolve (HIT)
                           -> não achou? lê o banco, grava no cache (MISS)
ESCRITA:  grava no banco  -> INVALIDA a chave no cache
```

A aplicação é quem controla o cache — o banco não sabe que ele existe. É o
padrão mais comum porque é simples e não exige integração com o SGBD.

**Onde ver:** `service/ProdutoService.java` (`@Cacheable` na leitura, evict no
update).

### 1.2 Cache HIT e cache MISS

- **HIT**: o dado estava no cache. O método anotado com `@Cacheable`
  **nem executa** — o Spring intercepta antes. Resultado: `X-Query-Count: 0`.
- **MISS**: não estava. O método executa, consulta o banco e o retorno é
  gravado no cache.

**Como observar ao vivo:**
```bash
curl -s -X DELETE http://localhost:8080/api/admin/cache     # cache frio
curl -i http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"  # MISS, 1 query
curl -i http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"  # HIT,  0 queries
```

### 1.3 TTL (Time To Live)

Tempo de vida da entrada no cache. Expirado, a chave é removida e a próxima
leitura é MISS.

**Onde ver:** `application.yml` → `app.cache.ttl-produto: 60s`,
`app.cache.ttl-categoria: 10m`; aplicado em `config/CacheConfig.java`.

**Como observar ao vivo:**
```bash
docker exec a2-redis redis-cli TTL "produtos::10"   # segundos restantes
# -2 = chave não existe (expirou ou foi invalidada)
```

> **A regra que define o TTL**: o TTL é o **tamanho máximo da janela de
> inconsistência**. Categoria quase nunca muda → 10 min é seguro. Preço muda →
> 60 s, porque um preço errado por 10 minutos seria prejuízo.

### 1.4 Invalidação: `@CacheEvict` vs `@CachePut`

- `@CacheEvict` **apaga** a chave. A próxima leitura reconstrói a partir do
  banco (a fonte da verdade).
- `@CachePut` **sobrescreve** a chave com o valor que a aplicação supõe ter
  gravado.

**Escolhemos evict.** Se o banco tiver trigger, valor default ou outra
transação concorrente, o `@CachePut` gravaria no cache um valor que nunca
existiu no banco. O evict custa um MISS extra e nunca mente.

**Como observar o risco de NÃO invalidar:**
```bash
bash scripts/experimento-cache-sem-invalidacao.sh
```
Esse script sobe o profile `cache-sem-invalidacao`, altera o preço no banco e
mostra a leitura devolvendo o **preço antigo** até o TTL expirar.

### 1.5 "O cache sempre melhora?" — e como quase respondi errado

**A pergunta do item 3.5 exige cuidado com o método.** Para medir o custo do
MISS eu criei uma variante de carga com 2.000 IDs distintos e cache limpo antes
da rodada, chamada "cache frio". No gráfico, ela ficou **sobreposta** à variante
quente — o que deveria ter sido impossível.

Em vez de explicar a coincidência, fui medir:

```bash
curl -s http://localhost:8080/api/admin/cache/stats
# {"hits":132114,"misses":2008,"hitRatio":98.5}
```

**Hit ratio de 98,5%.** Os `misses` foram exatamente 2.008 — ou seja, só os
2.000 IDs distintos, uma vez cada. A conta explica tudo:

```
2.300 req/s x 25 s = 57.500 requisições para 2.000 IDs
-> cada ID é pedido ~29 vezes
-> o cache aquece em 2.000 / 2.300 = 0,86 s  (3,5% da rodada)
```

A variante era **quente em 96% do tempo**. Ela não media o custo do MISS: media
o efeito da **cardinalidade das chaves** (50 vs 2.000 IDs) — outra pergunta,
também válida, mas outra.

> **Lição de método (vale mais que o número):** teste de carga é a ferramenta
> **errada** para medir o custo do MISS. Qualquer faixa de chaves que caiba na
> tabela aquece em menos de um segundo. E, principalmente: **rótulo de variante
> não é prova — o hit ratio é.** Se eu não tivesse conferido, teria afirmado no
> relatório que "o cache atrapalha quando não há reuso" com base em dados que
> mostravam 98,5% de HIT.

**A medição correta** é determinística — limpa o cache antes de **cada**
requisição, garantindo 100% de MISS:

```bash
bash scripts/experimento-custo-miss.sh
```

Ela compara as três situações pelo número de idas à rede:

| Situação | Idas | Esperado |
|---|---|---|
| sem cache | 1 (banco) | linha de base |
| cache MISS | 3 (Redis + banco + Redis) | **mais lento** que não ter cache |
| cache HIT | 1 (Redis) | muito mais rápido |

E calcula o **ponto de equilíbrio**: quantos HITs cada MISS precisa para o cache
compensar. É essa razão — não o rótulo da variante — que responde se vale a pena
cachear um dado.

### 1.6 A armadilha do proxy (erro que realmente aconteceu aqui)

`@Cacheable` é implementado por um **proxy** em volta do bean. Se um método da
mesma classe chama o método anotado diretamente (*self-invocation*), a chamada
**não passa pelo proxy** e o cache nunca é consultado.

Foi exatamente o bug da primeira versão deste projeto: a checagem HIT/MISS
morava dentro do `ProdutoService` e chamava `buscarComCache()` na própria
classe. Resultado: `X-Cache: MISS` e `X-Query-Count: 1` em **todas** as
requisições — sem erro nenhum no log.

**Correção:** separar a instrumentação em outro bean
(`service/CacheInstrumentado.java`), para a chamada atravessar o proxy.

> **Lição**: anotação do Spring só funciona quando a chamada vem **de fora** do
> bean. Se o cache "não funciona" e não há erro, suspeite disso primeiro.

### 1.7 Serialização no Redis

Os DTOs são `record`, que o compilador marca como **final**. Isso quebra o
`GenericJackson2JsonRedisSerializer` com `activateDefaultTyping(NON_FINAL)`: o
Jackson não grava o campo de tipo e a leitura falha com *"need Array value to
contain `As.WRAPPER_ARRAY` type information"*.

**Correção:** um serializer **tipado por cache** (`CacheConfig.java`). O JSON
fica limpo e legível:
```bash
docker exec a2-redis redis-cli GET "produtos::10"
# {"id":10,"nome":"Produto 10","preco":777.77,...}
```

---

## 2. Estratégias de carregamento (JPA/Hibernate)

### 2.1 LAZY, EAGER e o proxy do Hibernate

- **LAZY**: no lugar do objeto relacionado, o Hibernate coloca um **proxy**
  (objeto vazio que sabe se carregar). O SQL extra só sai no **primeiro acesso**
  a um atributo desse proxy.
- **EAGER**: o relacionamento é carregado junto, sempre, mesmo que ninguém use.

**Onde ver:** `entity/lazy/` e `entity/eager/` — as **mesmas tabelas** mapeadas
duas vezes.

> **Por que dois conjuntos de entidades?** No JPA, o `FetchType` faz parte do
> *mapeamento*: uma classe não pode ser LAZY num endpoint e EAGER noutro. Para
> comparar as duas estratégias no mesmo banco, não há alternativa senão mapear
> duas vezes. Ambos são `@Immutable` (somente leitura), porque existem apenas
> para o experimento.

### 2.2 O problema N+1

Uma consulta para a lista + **N** consultas para os relacionamentos:

```
 1  SELECT * FROM pedido ORDER BY id LIMIT 100         <- a "1"
 +  SELECT * FROM cliente     WHERE id = ?        x100  <- os "N"
 +  SELECT * FROM item_pedido WHERE pedido_id = ? x100
 +  SELECT * FROM produto     WHERE id = ?        x...
```

**Como observar ao vivo** (o número cresce com o limite):
```bash
for l in 10 100 500; do
  curl -si "http://localhost:8080/api/pedidos/lazy?limite=$l" | grep -i x-query-count
done
```

**Onde ver:** `service/PedidoService.java`, método `listarLazy` — o `for` que
percorre `getItens()` é o gatilho.

> **O ponto que o enunciado pede para observar (item 4.2): EAGER também gera
> N+1.** Numa consulta JPQL sem fetch explícito, o Hibernate busca os pedidos e
> depois resolve cada coleção EAGER — uma query por pedido. A diferença é que
> agora o custo é pago **sempre**. Compare `/lazy` e `/eager` com o mesmo
> limite: ambos ficam na ordem de centenas de queries.

### 2.3 A vantagem real do LAZY

```bash
curl -si "http://localhost:8080/api/pedidos/lazy-sem-acesso?limite=1000" | grep -i x-query-count
# X-Query-Count: 1  (independentemente do limite)
```

LAZY é um bom **default**. O erro não é o LAZY: é percorrer relacionamentos sem
ter planejado como carregá-los.

### 2.4 JOIN FETCH

Uma única query com `join`, trazendo tudo de uma vez.

**A armadilha da paginação:** com `JOIN FETCH` de **coleção**, um pedido vira N
linhas (uma por item). Aplicar `LIMIT` direto cortaria no meio dos itens,
retornando pedidos incompletos. O Hibernate detecta isso e, para não errar, traz
**tudo** para a memória e pagina em Java (aviso `HHH90003004`) — o que anula o
ganho.

**Solução — padrão de 2 etapas:**
1. buscar só os **IDs** da página (`LIMIT` seguro, sem join de coleção);
2. fazer o `JOIN FETCH` **por esses IDs**.

**Onde ver:** `repository/PedidoOtimizadoRepository.java`
(`buscarIdsPagina` + `buscarComJoinFetch`).

### 2.5 `@EntityGraph`

Mesma ideia do JOIN FETCH, declarada por atributos
(`attributePaths = {"cliente","itens","itens.produto"}`) em vez de escrita na
JPQL. Útil para variar o que carregar reaproveitando a mesma query.

### 2.6 Batch fetching (`@BatchSize`)

Em vez de 1 + N consultas, o Hibernate agrupa a resolução dos proxies em
`WHERE pedido_id IN (?, ?, ...)` → **1 + ⌈N/size⌉** consultas.

**Onde ver:** `entity/batch/PedidoBatch.java` (`@BatchSize(size = 100)`).

**Quando preferir ao JOIN FETCH:** quando há **várias coleções**. Dois JOIN
FETCH de coleção na mesma query produzem produto cartesiano (10 itens × 5
pagamentos = 50 linhas); o batch fetching evita isso ao custo de algumas
consultas extras.

### 2.7 Projeção DTO

Lê colunas soltas e monta o DTO, sem criar entidades gerenciadas. O Hibernate
não guarda nada no contexto de persistência nem faz *dirty checking* → menos CPU
e memória por requisição. Ideal para telas de leitura.

**Onde ver:** `repository/PedidoProjecaoRepository.buscarProjecao`.

### 2.8 SQL nativo

Usamos `json_agg` do PostgreSQL: o **banco** monta o array de itens e devolve
uma linha por pedido, eliminando o tráfego das linhas repetidas do join.

**Compensou?** Em número de SQL, empata com JOIN FETCH. Ganha em tráfego.
**Mas custa:**
- portabilidade — `json_agg` não existe em MySQL/Oracle;
- nenhuma verificação em tempo de compilação: erro de coluna só aparece na
  execução;
- renomear coluna deixa de ser refatoração automática da IDE.

> **Conclusão honesta:** SQL nativo vale quando o gargalo **medido** é o volume
> trafegado. Não como padrão.

---

## 3. Índices

### 3.1 Índice B-tree e índice composto

O B-tree é uma árvore ordenada: o banco desce a árvore em vez de ler a tabela
toda. Num índice **composto** `(cliente_id, data_pedido DESC)`:

- `cliente_id` resolve o filtro de igualdade;
- `data_pedido DESC` já entrega as linhas na ordem pedida → o nó `Sort`
  **desaparece** do plano.

A **ordem das colunas é decisiva**: igualdade primeiro, intervalo/ordenação
depois. `(data_pedido, status)` serve à consulta de período porque é o intervalo
que define o trecho do índice a varrer.

**Onde ver:** `db/10-create-index.sql`.

### 3.2 `EXPLAIN (ANALYZE, BUFFERS)`

- `EXPLAIN` → mostra o plano **estimado**.
- `EXPLAIN ANALYZE` → **executa** e mostra o tempo e as linhas reais.
- `BUFFERS` → quantos blocos foram lidos (memória vs disco).

O que procurar:

| No plano | Significado |
|---|---|
| `Seq Scan` | varredura completa da tabela |
| `Index Scan` | acesso direto pelo índice |
| `Index Only Scan` | o índice já tinha todas as colunas; nem foi à tabela |
| `Bitmap Heap Scan` | muitas linhas: o banco monta um mapa antes de ler |
| `Sort` | ordenação em tempo de execução (custa CPU e memória) |
| `rows=` | linhas processadas naquele nó |

**Como observar ao vivo:**
```bash
docker exec -i a2-postgres psql -U a2 -d vendas -c \
 "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM pedido WHERE cliente_id = 150 ORDER BY data_pedido DESC LIMIT 50;"
```

**Experimento completo (5 repetições, antes e depois):**
```bash
bash scripts/explain-antes-depois.sh
# -> results/indices/antes.txt, depois.txt, resumo.txt
```

> **Por que descartar a 1ª execução?** O PostgreSQL mantém um cache de blocos
> (*shared buffers*). A primeira execução lê do disco; as seguintes, da memória.
> Comparar uma primeira execução com uma quinta mediria o cache, não o índice.

### 3.3 O custo de manter índices

1. **Espaço** em disco (visível em `pg_indexes_size`).
2. **Escrita mais lenta**: cada `INSERT`/`UPDATE`/`DELETE` precisa atualizar
   **todos** os índices da tabela.
3. **Índice inútil**: com baixa seletividade (ex.: `status`, 5 valores em 300
   mil linhas), o planner costuma **ignorar** o índice — ler o índice e depois
   buscar as linhas sairia mais caro que varrer a tabela.

> **Por isso não se indexa tudo.** Índice se escolhe a partir das consultas
> reais e se confere no `EXPLAIN`.

---

## 4. Testes de desempenho

### 4.1 VUs ≠ req/s

Um **usuário virtual** (VU) dispara requisições em sequência: termina uma, começa
a próxima. 10 VUs podem gerar centenas de req/s. Mais VUs significa mais
**concorrência**, não necessariamente mais vazão — a partir da saturação, mais
VUs só aumentam a fila (e a latência).

### 4.2 Média, p95 e p99

- **média**: soma / número de requisições. Esconde a cauda.
- **p95**: 95% das requisições foram mais rápidas que esse valor.
- **p99**: idem para 99%.

> **Por que percentis importam mais:** uma média de 50 ms com p99 de 2.000 ms
> significa que 1 em 100 usuários esperou 2 segundos. A média não mostra isso.
> p99 alto costuma indicar fila no pool de conexões, pausa de GC ou contenção no
> banco.

### 4.3 Aquecimento e JIT

A JVM começa **interpretando** o bytecode; só depois o **JIT** compila os
trechos quentes para código nativo. Além disso, o pool de conexões precisa
encher e o cache de buffers do Postgres precisa aquecer. Medir esse período
inflaria a latência.

**Como tratamos:** cada rodada executa o k6 **duas vezes** — a primeira
(`MODO=aquecimento`) é descartada, a segunda (`MODO=medicao`) é exportada.

> **Por que dois processos e não dois `scenarios` no mesmo run?** Porque o
> `--summary-export` agrega **todas** as métricas da execução: o aquecimento
> entraria na média e nos percentis. Separando os processos, o JSON contém
> apenas a medição.

### 4.4 Controle de variáveis

Para a comparação ser honesta, só **uma** coisa pode mudar entre rodadas:

| Variável | Como foi fixada |
|---|---|
| CPU/memória | limites fixos no `docker-compose.yml` |
| pool de conexões | `maximum-pool-size = minimum-idle = 20` (pool fixo) |
| volume de dados | seed determinístico com `setseed(0.42)` |
| estado do cache | limpo/pré-aquecido explicitamente antes de cada rodada |
| estado do índice | criado/removido pelo `run-all-tests.sh` |
| log de SQL | desligado (profile `sql-log` só para demonstração) |
| aquecimento | descartado |
| repetições | 3 por ponto, com desvio-padrão do p95 registrado |

> **Lição**: o resultado de um teste de carga só significa algo se você puder
> explicar o que foi mantido constante.

---

## 5. Como tudo se conecta

As três técnicas atacam **níveis diferentes** do mesmo problema:

| Técnica | O que reduz |
|---|---|
| Cache | o número de requisições que **chegam ao banco** |
| Estratégia de consulta | o número de SQL **por requisição** |
| Índice | o custo de **cada SQL** |

Por isso elas se somam em vez de competir. E por isso a ordem de ataque
importa: primeiro **meça** (`X-Query-Count`), depois reduza o número de
consultas, depois torne cada consulta mais barata e só então considere cachear.
Cachear uma consulta mal escrita só esconde o problema até o primeiro MISS.
