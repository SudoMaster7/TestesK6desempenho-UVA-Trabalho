#!/usr/bin/env bash
# Demonstracao guiada para gravar o video (segue docs/ROTEIRO_VIDEO.md).
# Cada comando e MOSTRADO antes de rodar e o script ESPERA um Enter entre os
# passos -- assim voce fala com calma e nao precisa digitar nada na gravacao.
#
# Uso (no terminal Git Bash do VS Code, dentro de a2-otimizacao/):
#   bash scripts/demo-video.sh          # roteiro inteiro
#   bash scripts/demo-video.sh 3        # comeca a partir do bloco 3
cd "$(dirname "$0")/.."
B=http://localhost:8080
K6="/c/Program Files/k6/k6.exe"
INICIO="${1:-1}"

AZUL=$'\e[1;36m'; AMARELO=$'\e[1;33m'; VERDE=$'\e[1;32m'; RESET=$'\e[0m'

bloco() { clear; echo "${AMARELO}==================== $1 ====================${RESET}"; echo; }
pausa() { echo; read -rp "${VERDE}[Enter] proximo passo${RESET} " _; echo; }
roda()  { echo "${AZUL}\$ $1${RESET}"; eval "$1"; echo; }
headers() { curl -si "$1" | grep -i '^X-' | tr -d '\r'; }

# ---------- checagem: nada de surpresa no meio da gravacao ----------
if [ "$(curl -s -o /dev/null -w '%{http_code}' $B/actuator/health)" != "200" ]; then
  echo "A aplicacao NAO esta no ar em $B. Suba com: bash scripts/app-restart.sh"; exit 1
fi

if [ "$INICIO" -le 1 ]; then
bloco "BLOCO 1 - Arquitetura e volume de dados"
roda "curl -s $B/api/admin/stats"
pausa
fi

if [ "$INICIO" -le 2 ]; then
bloco "BLOCO 2 - A ferramenta de medicao (headers X-)"
roda "headers $B/api/produtos/10/sem-cache"
pausa
fi

if [ "$INICIO" -le 3 ]; then
bloco "BLOCO 3 - Cache: MISS, HIT e invalidacao"
roda "curl -s -X DELETE $B/api/admin/cache   # limpa o cache"
echo "# 1) primeira leitura -> MISS (vai ao banco)"
roda "headers $B/api/produtos/10/com-cache"
pausa
echo "# 2) segunda leitura -> HIT, ZERO consultas"
roda "headers $B/api/produtos/10/com-cache"
pausa
echo "# 3) o dado gravado no Redis e o tempo de vida (TTL, em segundos)"
roda 'docker exec a2-redis redis-cli GET "produtos::10"'
roda 'docker exec a2-redis redis-cli TTL "produtos::10"'
pausa
NOVO_PRECO="$(awk 'BEGIN{srand(); printf "%.2f", 100+rand()*900}')"
echo "# 4) atualiza o preco -> o cache e INVALIDADO (TTL -2 = chave nao existe)"
roda "curl -s -X PUT $B/api/produtos/10 -H 'Content-Type: application/json' -d '{\"preco\":$NOVO_PRECO,\"estoque\":7}' > /dev/null"
roda 'docker exec a2-redis redis-cli TTL "produtos::10"'
pausa
echo "# 5) proxima leitura: MISS, ja com o preco novo ($NOVO_PRECO)"
roda "headers $B/api/produtos/10/com-cache"
roda "curl -s $B/api/produtos/10/com-cache"
pausa
fi

if [ "$INICIO" -le 4 ]; then
bloco "BLOCO 4 - LAZY vs EAGER e o problema N+1"
echo "# LAZY acessando os relacionamentos: as consultas CRESCEM com o limite"
for l in 10 100 500; do
  echo -n "lazy  limite=$l -> "; curl -si "$B/api/pedidos/lazy?limite=$l" | grep -i x-query-count | tr -d '\r'
done
pausa
echo "# EAGER tambem faz N+1  |  LAZY sem acessar faz 1 so"
echo -n "eager           limite=100  -> "; curl -si "$B/api/pedidos/eager?limite=100" | grep -i x-query-count | tr -d '\r'
echo -n "lazy-sem-acesso limite=1000 -> "; curl -si "$B/api/pedidos/lazy-sem-acesso?limite=1000" | grep -i x-query-count | tr -d '\r'
pausa
fi

if [ "$INICIO" -le 5 ]; then
bloco "BLOCO 5 - Consultas otimizadas (limite=100, mesmo resultado)"
printf "%-14s %-22s %s\n" "estrategia" "consultas SQL" "tempo no servidor"
for e in lazy eager join-fetch entity-graph batch dto nativo; do
  H="$(curl -si "$B/api/pedidos/$e?limite=100" | tr -d '\r')"
  Q="$(echo "$H" | grep -i x-query-count | awk '{print $2}')"
  T="$(echo "$H" | grep -i x-response-time | awk '{print $2}')"
  printf "%-14s %-22s %s ms\n" "$e" "$Q" "$T"
done
pausa
fi

if [ "$INICIO" -le 6 ]; then
SQL="EXPLAIN ANALYZE SELECT * FROM pedido WHERE cliente_id=150 ORDER BY data_pedido DESC LIMIT 50;"
bloco "BLOCO 6a - EXPLAIN SEM indice"
roda "docker exec -i a2-postgres psql -U a2 -d vendas -q < db/11-drop-index.sql > /dev/null   # remove o indice"
roda "docker exec -i a2-postgres psql -U a2 -d vendas -c \"$SQL\""
echo "${AMARELO}>> repare: Seq Scan on pedido  +  no Sort${RESET}"
pausa
bloco "BLOCO 6b - EXPLAIN COM indice"
roda "docker exec -i a2-postgres psql -U a2 -d vendas -q < db/10-create-index.sql > /dev/null   # cria o indice"
roda "docker exec -i a2-postgres psql -U a2 -d vendas -c \"$SQL\""
echo "${AMARELO}>> repare: Index Scan using idx_pedido_cliente_data  e o Sort SUMIU${RESET}"
pausa
fi

if [ "$INICIO" -le 7 ]; then
bloco "BLOCO 7a - Teste de carga: 50 usuarios, SEM cache (15 s)"
roda "MODO=medicao VUS=50 DURATION=15s VARIANTE=sem-cache \"$K6\" run --quiet k6/cenario1-cache.js"
pausa
bloco "BLOCO 7b - Teste de carga: 50 usuarios, COM cache quente (15 s)"
echo "# aquecendo o cache com os produtos 1..50"
curl -s -X DELETE $B/api/admin/cache > /dev/null
for id in $(seq 1 50); do curl -s "$B/api/produtos/$id/com-cache" > /dev/null; done
roda "MODO=medicao VUS=50 DURATION=15s VARIANTE=com-cache-quente \"$K6\" run --quiet k6/cenario1-cache.js"
pausa
fi

bloco "BLOCO 8 - Fim da demonstracao"
echo "Agora mostre o painel docs/dashboard.html: abas 'Visao geral' e '3. Testes de carga'."
