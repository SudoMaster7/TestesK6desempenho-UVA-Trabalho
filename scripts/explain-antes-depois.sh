#!/usr/bin/env bash
# =====================================================================
# ITEM 2c / 5.3 - EXPLAIN (ANALYZE, BUFFERS) antes e depois dos indices.
#
# Metodologia:
#   - cada consulta e executada 6x; a 1a e DESCARTADA (aquecimento do cache
#     de buffers do Postgres) e as 5 seguintes sao registradas;
#   - a mesma rotina roda sem indice e com indice, no MESMO banco e com os
#     MESMOS parametros, para a unica variavel ser o indice.
# Saidas: results/indices/antes.txt, depois.txt, resumo.txt
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p results/indices

PSQL="docker exec -i a2-postgres psql -U a2 -d vendas"
CLIENTE=${CLIENTE:-150}
REPS=${REPS:-5}

Q1="SELECT * FROM pedido WHERE cliente_id = $CLIENTE ORDER BY data_pedido DESC LIMIT 50;"
Q2="SELECT * FROM pedido WHERE data_pedido BETWEEN '2024-06-01' AND '2024-06-30' AND status = 'PAGO' ORDER BY data_pedido DESC LIMIT 50;"

rodar_fase() {
  local arquivo="$1" rotulo="$2"
  {
    echo "====================================================================="
    echo " EXPLAIN (ANALYZE, BUFFERS) - $rotulo"
    echo " data: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "====================================================================="
    echo
    echo "--- indices existentes na tabela pedido ---"
    $PSQL -c "select indexname, indexdef from pg_indexes where tablename='pedido' order by indexname;"
    echo "--- tamanho da tabela + indices ---"
    $PSQL -c "select pg_size_pretty(pg_relation_size('pedido')) as heap, pg_size_pretty(pg_indexes_size('pedido')) as indices, pg_size_pretty(pg_total_relation_size('pedido')) as total;"
    echo

    for n in 1 2; do
      if [ "$n" = "1" ]; then Q="$Q1"; NOME="CONSULTA 1: cliente_id = $CLIENTE ORDER BY data_pedido DESC LIMIT 50"; else Q="$Q2"; NOME="CONSULTA 2: data_pedido BETWEEN ... AND status = 'PAGO'"; fi
      echo "####################################################################"
      echo "# $NOME"
      echo "####################################################################"
      echo "SQL: $Q"
      echo
      echo "[execucao 0 - AQUECIMENTO, descartada]"
      $PSQL -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) $Q" > /dev/null 2>&1
      for r in $(seq 1 "$REPS"); do
        echo "----------------- repeticao $r de $REPS -----------------"
        $PSQL -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) $Q"
      done
      echo
    done
  } > "$arquivo" 2>&1
  echo ">> gravado: $arquivo"
}

echo ">> FASE 1/2: removendo os indices do experimento (estado 'antes')"
$PSQL -f /db/11-drop-index.sql > results/indices/drop.log 2>&1
rodar_fase results/indices/antes.txt "SEM INDICE (apenas a PK)"

echo ">> FASE 2/2: criando os indices (estado 'depois')"
$PSQL -f /db/10-create-index.sql > results/indices/create.log 2>&1
rodar_fase results/indices/depois.txt "COM INDICE (idx_pedido_cliente_data, idx_pedido_data_status)"

# ---- resumo comparativo extraido dos arquivos brutos ----
{
  echo "================== RESUMO (extraido de antes.txt / depois.txt) =================="
  echo
  for arq in antes depois; do
    echo "### $arq"
    echo "-- tipos de no de acesso encontrados:"
    grep -oE "(Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|Sort|Incremental Sort) [a-zA-Z ]*" "results/indices/$arq.txt" | sort | uniq -c | sort -rn
    echo "-- tempos de execucao medidos (ms):"
    grep -E "Execution Time" "results/indices/$arq.txt" | awk '{print $3}' | tr '\n' ' '
    echo; echo
  done
} > results/indices/resumo.txt
cat results/indices/resumo.txt
echo ">> gravado: results/indices/resumo.txt"
