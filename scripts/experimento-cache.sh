#!/usr/bin/env bash
# =====================================================================
# ITEM 3.4 - Experimento OBRIGATORIO do cache (5 passos do enunciado).
#
# Usa TTL curto (10s) para o passo 5 (expiracao) caber na demonstracao.
# Rode:  TTL=10s bash scripts/experimento-cache.sh
# Saida: results/cache/experimento.txt
# =====================================================================
set -uo pipefail
export MSYS_NO_PATHCONV=1  # evita o Git Bash converter /PID e /c em caminhos
cd "$(dirname "$0")/.."

BASE=http://localhost:8080
PRODUTO=${PRODUTO:-10}
OUT=results/cache/experimento.txt
mkdir -p results/cache

# TTL curto apenas para este experimento: com 60s a demonstracao da expiracao
# ficaria longa demais para o video de 7 minutos.
TTL_EXP=${TTL:-10s}
echo ">> reiniciando a aplicacao com app.cache.ttl-produto=$TTL_EXP"
JAVA_HOME_WIN='C:\Program Files\Microsoft\jdk-21.0.13.102-hotspot'
for PID in $(netstat -ano 2>/dev/null | grep LISTENING | grep ':8080' | awk '{print $NF}' | sort -u); do
  taskkill /PID "$PID" /F >/dev/null 2>&1 || true
done
sleep 4
(cd app && nohup cmd.exe /c "set JAVA_HOME=$JAVA_HOME_WIN&& .\mvnw.cmd -B -DskipTests -Dspring-boot.run.jvmArguments=-Dapp.cache.ttl-produto=$TTL_EXP spring-boot:run" > ../results/app.log 2>&1 &)
for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' $BASE/actuator/health || true)" = "200" ] && break
  sleep 3
done

exec > >(tee "$OUT") 2>&1

echo "====================================================================="
echo " EXPERIMENTO DE CACHE - ITEM 3.4"
echo " data: $(date '+%Y-%m-%d %H:%M:%S')   produto: $PRODUTO   TTL: $TTL_EXP"
echo "====================================================================="
echo
echo "--- Estado inicial: limpando o cache (cache frio) ---"
curl -s -X DELETE $BASE/api/admin/cache; echo; echo

echo "=== PASSO 1: primeira consulta (esperado X-Cache: MISS, X-Query-Count: 1) ==="
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo; echo

echo "=== PASSO 2: repete a consulta (esperado X-Cache: HIT, X-Query-Count: 0) ==="
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo; echo

echo "--- Chave gravada no Redis e TTL restante ---"
docker exec a2-redis redis-cli GET "produtos::$PRODUTO"
echo "TTL (segundos): $(docker exec a2-redis redis-cli TTL "produtos::$PRODUTO")"
echo

echo "=== PASSO 3: PUT altera preco/estoque no banco (dispara a invalidacao) ==="
curl -i -s -X PUT "$BASE/api/produtos/$PRODUTO" \
     -H 'Content-Type: application/json' \
     -d '{"preco": 1234.56, "estoque": 7}'; echo; echo
echo "--- A chave deve ter sido REMOVIDA do Redis (TTL -2 = inexistente) ---"
echo "TTL apos o PUT: $(docker exec a2-redis redis-cli TTL "produtos::$PRODUTO")"
echo

echo "=== PASSO 4: consulta de novo (esperado MISS + preco ATUALIZADO = 1234.56) ==="
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo; echo
echo "--- e mais uma vez, agora HIT com o dado novo ---"
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo; echo

echo "=== PASSO 5: expiracao por TTL ==="
echo "Valor em cache agora:"
docker exec a2-redis redis-cli GET "produtos::$PRODUTO"
SEG=$(docker exec a2-redis redis-cli TTL "produtos::$PRODUTO" | tr -d '\r')
echo "TTL restante: ${SEG}s -- aguardando a expiracao..."
sleep $((SEG + 2))
echo "TTL depois da espera (-2 = chave expirada e removida): $(docker exec a2-redis redis-cli TTL "produtos::$PRODUTO")"
echo "KEYS no Redis: $(docker exec a2-redis redis-cli KEYS 'produtos*')"
echo
echo "Nova consulta apos a expiracao (esperado MISS: o cache precisa ser reconstruido)"
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo; echo

echo "=== Contadores finais do cache ==="
curl -s $BASE/api/admin/cache/stats; echo; echo
echo "FIM. Saida salva em $OUT"
