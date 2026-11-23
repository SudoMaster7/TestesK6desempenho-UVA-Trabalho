#!/usr/bin/env bash
# =====================================================================
# ITEM 3.4 (parte final) - DEMONSTRACAO DO RISCO DE DADO DESATUALIZADO.
#
# Sobe a aplicacao no profile `cache-sem-invalidacao` (sem @CacheEvict no
# update) e mostra que, depois de um PUT, a leitura continua devolvendo o
# PRECO ANTIGO ate o TTL expirar -- exatamente o risco que o enunciado
# pede para explicar.
# Saida: results/cache/sem-invalidacao.txt
# =====================================================================
set -uo pipefail
export MSYS_NO_PATHCONV=1  # evita o Git Bash converter /PID e /c em caminhos
cd "$(dirname "$0")/.."

BASE=http://localhost:8080
PRODUTO=${PRODUTO:-20}
TTL_EXP=${TTL:-15s}
OUT=results/cache/sem-invalidacao.txt
mkdir -p results/cache

JAVA_HOME_WIN='C:\Program Files\Microsoft\jdk-21.0.13.102-hotspot'
for PID in $(netstat -ano 2>/dev/null | grep LISTENING | grep ':8080' | awk '{print $NF}' | sort -u); do
  taskkill /PID "$PID" /F >/dev/null 2>&1 || true
done
sleep 4
(cd app && nohup cmd.exe /c "set JAVA_HOME=$JAVA_HOME_WIN&& .\mvnw.cmd -B -DskipTests -Dspring-boot.run.profiles=cache-sem-invalidacao -Dspring-boot.run.jvmArguments=-Dapp.cache.ttl-produto=$TTL_EXP spring-boot:run" > ../results/app.log 2>&1 &)
for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' $BASE/actuator/health || true)" = "200" ] && break
  sleep 3
done

exec > >(tee "$OUT") 2>&1

echo "====================================================================="
echo " CACHE SEM INVALIDACAO - risco de dado desatualizado (stale read)"
echo " profile: cache-sem-invalidacao   TTL: $TTL_EXP   produto: $PRODUTO"
echo "====================================================================="
echo
curl -s -X DELETE $BASE/api/admin/cache >/dev/null

echo "--- 1) leitura inicial (MISS, popula o cache) ---"
curl -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo
PRECO_ANTIGO=$(curl -s "$BASE/api/produtos/$PRODUTO/com-cache" | grep -o '"preco":[0-9.]*')
echo "    preco em cache: $PRECO_ANTIGO"
echo
echo "--- 2) PUT grava 555.55 no BANCO (sem invalidar o cache) ---"
curl -s -X PUT "$BASE/api/produtos/$PRODUTO" -H 'Content-Type: application/json' \
     -d '{"preco": 555.55, "estoque": 3}' >/dev/null
echo "    valor REAL no banco (endpoint /sem-cache):"
curl -s "$BASE/api/produtos/$PRODUTO/sem-cache"; echo
echo
echo "--- 3) leitura com cache: AQUI ESTA O PROBLEMA ---"
echo "    o cliente recebe o preco ANTIGO, nao o 555.55 gravado no banco:"
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo
echo
echo "--- 4) aguardando o TTL expirar para o dado se corrigir sozinho ---"
SEG=$(docker exec a2-redis redis-cli TTL "produtos::$PRODUTO" | tr -d '\r')
echo "    TTL restante: ${SEG}s"
sleep $((SEG + 2))
echo "    leitura apos a expiracao (agora MISS -> le o banco -> 555.55):"
curl -i -s "$BASE/api/produtos/$PRODUTO/com-cache"; echo
echo
echo "CONCLUSAO: sem invalidacao ativa, a janela de inconsistencia e igual ao"
echo "TTL. Para preco/estoque isso significa vender por um valor errado ate o"
echo "TTL vencer -- motivo pelo qual o projeto usa TTL curto + @CacheEvict."
echo
echo "FIM. Saida salva em $OUT"
