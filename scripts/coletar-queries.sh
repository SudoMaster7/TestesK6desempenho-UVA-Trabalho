#!/usr/bin/env bash
# =====================================================================
# Coleta o X-Query-Count REAL de cada estrategia de persistencia, em
# varios limites, e salva em results/queries.json (usado pelo dashboard
# e pelas tabelas do README).
#
# Mede com a aplicacao JA AQUECIDA: a primeira chamada de cada endpoint e
# descartada, porque nela o Hibernate ainda esta montando o plano da query e
# o pool de conexoes pode estar abrindo conexao nova.
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

BASE=${BASE:-http://localhost:8080}
LIMITES=${LIMITES:-"10 100 500 1000"}
ESTRATEGIAS=${ESTRATEGIAS:-"lazy eager lazy-sem-acesso join-fetch entity-graph batch dto nativo"}
OUT=results/queries.json
TXT=results/queries.txt
mkdir -p results

echo "estrategia;limite;queries;tempo_ms;bytes" > "$TXT"
printf '{\n' > "$OUT"
primeiro_e=1

for e in $ESTRATEGIAS; do
  [ $primeiro_e -eq 0 ] && printf ',\n' >> "$OUT"
  primeiro_e=0
  printf '  "%s": {' "$e" >> "$OUT"
  primeiro_l=1
  for l in $LIMITES; do
    # aquecimento (descartado)
    curl -s -o /dev/null "$BASE/api/pedidos/$e?limite=$l"
    # medicao
    # Corpo descartado em /dev/null (funciona no Linux e no Git Bash do
    # Windows). Antes ia para /tmp.body: no Windows esse caminho e a raiz do
    # disco, o curl falhava DEPOIS de imprimir os headers, o "||" repetia a
    # chamada e cada valor saia duplicado ("55\n55"), gerando JSON invalido.
    hdr=$(curl -s -D - -o /dev/null "$BASE/api/pedidos/$e?limite=$l")
    q=$(printf '%s' "$hdr" | grep -i '^X-Query-Count' | head -n1 | tr -d '\r' | awk '{print $2}')
    t=$(printf '%s' "$hdr" | grep -i '^X-Response-Time-Ms' | head -n1 | tr -d '\r' | awk '{print $2}')
    b=$(curl -s -o /dev/null -w '%{size_download}' "$BASE/api/pedidos/$e?limite=$l")
    q=${q:-0}; t=${t:-0}; b=${b:-0}
    printf "%-16s limite=%-5s queries=%-6s tempo=%-9s bytes=%s\n" "$e" "$l" "$q" "$t" "$b"
    echo "$e;$l;$q;$t;$b" >> "$TXT"
    [ $primeiro_l -eq 0 ] && printf ', ' >> "$OUT"
    primeiro_l=0
    printf '"%s": %s' "$l" "$q" >> "$OUT"
  done
  printf '}' >> "$OUT"
done
printf '\n}\n' >> "$OUT"

echo
echo ">> gravado: $OUT e $TXT"
