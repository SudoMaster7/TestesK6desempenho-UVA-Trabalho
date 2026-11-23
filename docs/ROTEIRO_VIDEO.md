# Roteiro do vídeo (máximo 7 minutos)

**Antes de gravar** — deixe tudo pronto e aquecido:

```bash
docker compose up -d --wait                 # Postgres + Redis
bash scripts/app-restart.sh                 # aplicação na porta 8080
curl -s http://localhost:8080/api/admin/stats   # confirma o volume de dados
```

Abra em abas separadas: **terminal**, **docs/dashboard.html**, e deixe o
`README.md` à mão. Fonte do terminal em tamanho grande (≥ 16pt).

---

## Bloco 1 — Abertura e arquitetura · `0:00 – 0:45`

**Mostrar:** aba "Como funciona" do `docs/dashboard.html`.

**Falar:**
> "Trabalho A2 de Análise e Otimização de Sistemas. Uma API REST de vendas em
> Spring Boot, com 300 mil pedidos e 1 milhão de itens no PostgreSQL. Aplicamos
> três técnicas de otimização: cache com Redis, otimização de consultas e
> índices. Cada técnica ataca um nível diferente: o cache reduz quantas
> requisições chegam ao banco, a estratégia de consulta reduz quantos SQL cada
> requisição dispara, e o índice reduz o custo de cada SQL."

**Comando:**
```bash
curl -s http://localhost:8080/api/admin/stats
```

---

## Bloco 2 — A ferramenta de medição · `0:45 – 1:15`

**Falar:**
> "Tudo aqui é comprovável. Toda resposta traz três headers: quantos SQL a
> requisição executou, o tempo no servidor, e se o cache foi usado. É o
> `X-Query-Count` que transforma 'acho que melhorou' em número."

**Comando:**
```bash
curl -i http://localhost:8080/api/produtos/10/sem-cache | grep -i "^X-"
```
> Apontar: `X-Query-Count: 1`, `X-Cache: BYPASS`.

---

## Bloco 3 — Cache: HIT, MISS e invalidação · `1:15 – 2:30`

**Comandos (um por vez, pausando para apontar o header):**
```bash
# cache frio
curl -s -X DELETE http://localhost:8080/api/admin/cache

# 1) MISS -> 1 query
curl -i http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"

# 2) HIT -> ZERO query
curl -i http://localhost:8080/api/produtos/10/com-cache | grep -i "^X-"

# 3) o dado dentro do Redis e o TTL
docker exec a2-redis redis-cli GET "produtos::10"
docker exec a2-redis redis-cli TTL "produtos::10"

# 4) atualiza o preço -> a chave é invalidada
curl -s -X PUT http://localhost:8080/api/produtos/10 \
  -H "Content-Type: application/json" -d '{"preco":1234.56,"estoque":7}' > /dev/null
docker exec a2-redis redis-cli TTL "produtos::10"      # -2 = chave removida

# 5) próxima leitura: MISS, com o dado novo
curl -s http://localhost:8080/api/produtos/10/com-cache
```

**Falar (no passo 2):**
> "`X-Query-Count: zero`. Essa é a prova do cache — latência menor poderia ser
> coincidência, mas zero SQL não tem outra explicação: o banco não foi tocado."

**Falar (no passo 4):**
> "TTL igual a −2 significa que a chave não existe mais. Usamos `@CacheEvict`,
> que apaga, em vez de `@CachePut`, que sobrescreveria com o valor que a
> aplicação *supõe* ter gravado. Apagando, a próxima leitura reconstrói a partir
> da fonte da verdade."

**Falar (fechando o bloco):**
> "E se não houvesse invalidação? O cliente receberia o preço antigo por todo o
> TTL. Isso está demonstrado no `results/cache/sem-invalidacao.txt`."

---

## Bloco 4 — LAZY vs EAGER e o N+1 · `2:30 – 3:40`

**Comando:**
```bash
for l in 10 100 500; do
  echo -n "lazy limite=$l -> "; curl -si "http://localhost:8080/api/pedidos/lazy?limite=$l" | grep -i x-query-count
done
```

**Falar:**
> "LAZY acessando os relacionamentos: o número de consultas **cresce com o
> limite**. É o N+1 — uma consulta para a lista, mais duas por pedido para
> cliente e itens."

**Comando:**
```bash
echo -n "eager  -> "; curl -si "http://localhost:8080/api/pedidos/eager?limite=100" | grep -i x-query-count
echo -n "lazy-sem-acesso -> "; curl -si "http://localhost:8080/api/pedidos/lazy-sem-acesso?limite=1000" | grep -i x-query-count
```

**Falar:**
> "Dois pontos importantes. Primeiro: **EAGER não resolve o N+1** — ele também
> dispara centenas de consultas, só que agora o custo é pago sempre. Segundo: o
> LAZY sem acessar os relacionamentos faz **uma** consulta, mesmo com mil
> pedidos. O problema nunca foi o LAZY: foi percorrer relacionamentos sem
> planejar como carregá-los."

---

## Bloco 5 — Consultas otimizadas · `3:40 – 4:30`

**Comando:**
```bash
for e in lazy eager join-fetch entity-graph batch dto nativo; do
  printf "%-14s " "$e"; curl -si "http://localhost:8080/api/pedidos/$e?limite=100" | grep -i x-query-count
done
```

**Falar:**
> "Mesmo resultado, mesmo DTO, mesmo limite. O LAZY faz centenas de consultas; o
> JOIN FETCH, o EntityGraph e a projeção DTO fazem **duas** — e continuam duas
> se eu aumentar o limite. É a diferença entre O(N) e O(1) em número de
> consultas."

**Mencionar (sem abrir o código):**
> "Detalhe que custou tempo: JOIN FETCH de coleção com paginação não funciona
> direto — o Hibernate traz tudo para a memória. A solução é o padrão de duas
> etapas: primeiro os IDs da página, depois o fetch por esses IDs."

---

## Bloco 6 — Índices e EXPLAIN · `4:30 – 5:30`

**Comando (sem índice):**
```bash
docker exec -i a2-postgres psql -U a2 -d vendas -f /db/11-drop-index.sql
docker exec -i a2-postgres psql -U a2 -d vendas -c \
 "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM pedido WHERE cliente_id=150 ORDER BY data_pedido DESC LIMIT 50;"
```
> Apontar: **`Seq Scan on pedido`** e o nó **`Sort`**.

**Comando (com índice):**
```bash
docker exec -i a2-postgres psql -U a2 -d vendas -f /db/10-create-index.sql
docker exec -i a2-postgres psql -U a2 -d vendas -c \
 "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM pedido WHERE cliente_id=150 ORDER BY data_pedido DESC LIMIT 50;"
```
> Apontar: **`Index Scan using idx_pedido_cliente_data`** e que o **`Sort`
> desapareceu**.

**Falar:**
> "A consulta não mudou uma letra. Duas coisas melhoraram: o banco parou de ler
> as 300 mil linhas, e a ordenação desapareceu — porque o índice foi criado em
> `(cliente_id, data_pedido DESC)`, já na ordem pedida pelo `ORDER BY`. Por isso
> o índice composto rende muito mais que um índice simples."

**Fechar:**
> "Mas índice não é grátis: ocupa espaço e deixa toda escrita mais lenta, porque
> cada INSERT precisa atualizar todos os índices. Indexar tudo é contraproducente
> — e índice de baixa seletividade o planner simplesmente ignora."

---

## Bloco 7 — Teste de carga ao vivo · `5:30 – 6:20`

**Comando (≈30 s):**
```bash
# sem cache
MODO=medicao VUS=50 DURATION=15s VARIANTE=sem-cache \
  "/c/Program Files/k6/k6.exe" run k6/cenario1-cache.js

# com cache quente
curl -s -X DELETE http://localhost:8080/api/admin/cache > /dev/null
for id in $(seq 1 50); do curl -s "http://localhost:8080/api/produtos/$id/com-cache" > /dev/null; done
MODO=medicao VUS=50 DURATION=15s VARIANTE=com-cache-quente \
  "/c/Program Files/k6/k6.exe" run k6/cenario1-cache.js
```

**Falar:**
> "50 usuários virtuais. Reparem que usuários virtuais não são requisições por
> segundo: cada usuário dispara requisições em sequência. E olhem o p95 e o p99,
> não só a média — a média esconde a cauda."

---

## Bloco 8 — Resultados e conclusão · `6:20 – 7:00`

**Mostrar:** `docs/dashboard.html`, aba "Visão geral" (os KPIs) e depois
"Testes de carga" (alternando o gráfico entre p95 e throughput).

**Falar:**
> "Resultados consolidados: 4 níveis de carga — 10, 50, 100 e 200 usuários — com
> 3 repetições cada, aquecimento descartado, e todos os números vindos de
> execuções reais salvas em `results/`.
>
> Três conclusões. Primeira: a maior redução de trabalho veio da **otimização
> das consultas** — eliminar o N+1 saiu de centenas de SQL por requisição para
> dois. Segunda: o **índice** foi o maior ganho por esforço — uma linha de SQL,
> sem mudar a aplicação. Terceira: o **cache** tem o maior ganho quando há
> reuso: 6,2x no p95 e 3,3x no throughput com 200 usuarios.
>
> E aqui vai uma correcao de metodo que vale mencionar: eu tinha uma variante
> chamada 'cache frio' para medir o custo do MISS. Fui conferir o hit ratio e
> ele deu 98,5% -- com 2.000 IDs e 2.300 requisicoes por segundo, o cache
> esquenta em menos de um segundo numa rodada de 25. Ou seja, a variante media
> outra coisa. Teste de carga e a ferramenta errada para medir MISS; para isso
> fiz uma medicao deterministica, limpando o cache antes de cada requisicao.
>
> E a lição que fica: nenhuma dessas conclusões seria possível sem medição.
> O `X-Query-Count` foi o que permitiu provar cada afirmação em vez de supor."

---

## Checklist final antes de postar

- [ ] Duração ≤ 7 minutos
- [ ] Mostrou arquitetura, endpoints, cache (HIT/MISS/invalidação), LAZY vs
      EAGER com contagem de SQL, consulta otimizada, EXPLAIN antes/depois,
      índice, ao menos um teste de carga e os resultados
- [ ] Áudio audível e terminal legível
- [ ] Postado na pasta do trabalho **1 dia antes** da apresentação
