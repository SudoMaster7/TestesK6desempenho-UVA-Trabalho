#!/usr/bin/env bash
# =====================================================================
# ITEM 3 - Executa TODOS os cenarios k6, em todos os niveis de carga,
# com 3 repeticoes, controlando o estado inicial (cache/indice) antes de
# cada rodada (exigencia do item 6.5).
#
# Uso:
#   bash scripts/run-all-tests.sh              # completo (demora ~2-3h)
#   RAPIDO=1 bash scripts/run-all-tests.sh     # 1 repeticao, 20s por rodada
#
# Saidas:
#   results/k6/<cenario>_<variante>_<vus>vu_r<rep>.json  (summary do k6)
#   results/recursos/<...>.txt                            (docker stats)
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8080
PSQL="docker exec -i a2-postgres psql -U a2 -d vendas"
K6="/c/Program Files/k6/k6.exe"

mkdir -p results/k6 results/recursos

# LOCK: impede duas baterias simultaneas.
# Isso aconteceu de verdade aqui: um runner anterior sobreviveu ao kill do
# terminal e ficou medindo em paralelo com o novo. Duas baterias disputando a
# mesma aplicacao inflam a latencia das DUAS e os numeros viram lixo -- sem
# nenhum erro aparente nos logs.
LOCK=results/.run-all.lock
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "!! ERRO: ja existe uma bateria rodando (PID $(cat "$LOCK"))."
  echo "   Duas baterias simultaneas contaminam as medicoes de ambas."
  echo "   Para encerrar a anterior:  bash scripts/parar-testes.sh"
  exit 1
fi
echo $$ > "$LOCK"
# Garante que o lock e os k6 filhos morrem junto com o script (inclusive em Ctrl+C).
trap 'rm -f "$LOCK"; pkill -P $$ k6 2>/dev/null; exit' EXIT INT TERM

if [ "${RAPIDO:-0}" = "1" ]; then
  NIVEIS="${NIVEIS:-10 50 100 200}"; REPS="${REPS:-1}"; DUR="${DUR:-20s}"; WARM="${WARM:-8s}"
else
  NIVEIS="${NIVEIS:-10 50 100 200}"; REPS="${REPS:-3}"; DUR="${DUR:-60s}"; WARM="${WARM:-15s}"
fi

# O cenario de persistencia usa niveis de carga MENORES e um limite MENOR.
# Motivo medido: a variante LAZY leva ~1.100 ms por requisicao com limite=50
# (271 consultas SQL). Com 200 usuarios virtuais ela nao "degrada": ela SATURA,
# a fila estoura o timeout e a rodada vira 99% de erro -- o que mediria o
# timeout do k6, nao o custo do N+1. Com limite=20 e ate 50 VUs a comparacao
# entre as estrategias continua valida e o servidor permanece responsivo.
NIVEIS_PERSISTENCIA="${NIVEIS_PERSISTENCIA:-5 10 25 50}"
LIMITE_PERSISTENCIA="${LIMITE_PERSISTENCIA:-20}"

echo "=== Configuracao: niveis=[$NIVEIS] repeticoes=$REPS duracao=$DUR aquecimento=$WARM ==="
echo "=== Persistencia: niveis=[$NIVEIS_PERSISTENCIA] limite=$LIMITE_PERSISTENCIA ==="
echo "=== Volume de dados no banco (registrado conforme item 6.5): ==="
curl -s $BASE/api/admin/stats; echo; echo

# Coleta CPU/memoria dos 3 containers + resumo (item 6.4, "sempre que possivel").
coletar_recursos() {
  local tag="$1"
  {
    echo "# $tag  ($(date '+%H:%M:%S'))"
    docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' a2-postgres a2-redis
  } >> "results/recursos/${tag}.txt" 2>&1
}

# Confere que a aplicacao responde ANTES de medir.
# Sem isso, uma rodada contra a aplicacao caida produz um JSON com ~100% de erro
# que, no CSV, se parece com um dado valido -- e contaminaria o relatorio.
exigir_app_viva() {
  for _ in $(seq 1 20); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' $BASE/actuator/health || true)" = "200" ] && return 0
    sleep 3
  done
  echo "!! ERRO: aplicacao nao responde em $BASE. Abortando para nao gerar dado invalido."
  echo "   Verifique results/app.log e rode: bash scripts/app-restart.sh"
  exit 1
}

rodar() {
  local cenario="$1" script="$2" variante="$3" vus="$4" rep="$5"
  local tag="${cenario}_${variante}_${vus}vu_r${rep}"
  local json="results/k6/${tag}.json"

  echo "----> $tag"
  exigir_app_viva
  # 1) AQUECIMENTO: execucao separada, resultado descartado (nao exporta JSON).
  MODO=aquecimento VUS="$vus" WARMUP="$WARM" VARIANTE="$variante" LIMITE="${LIMITE:-100}" \
    BASE_URL="$BASE" "$K6" run --quiet "$script" > /dev/null 2>&1

  # 2) MEDICAO: so esta rodada vai para o relatorio.
  coletar_recursos "$tag"
  MODO=medicao VUS="$vus" DURATION="$DUR" VARIANTE="$variante" LIMITE="${LIMITE:-100}" \
    BASE_URL="$BASE" "$K6" run --quiet --summary-export "$json" "$script" \
    > "results/k6/${tag}.log" 2>&1
  local rc=$?
  coletar_recursos "$tag"

  # Valida a rodada: taxa de erro acima de 50% nao e "degradacao sob carga",
  # e sinal de que a aplicacao estava indisponivel. Nesse caso o JSON e
  # DESCARTADO (renomeado para .invalido) para nao entrar no relatorio.
  local taxa
  taxa=$(python3 -c "
import json,sys
try:
    d=json.load(open('$json'))['metrics'].get('http_req_failed',{})
    print(d.get('value',0) or 0)
except Exception:
    print(1)
" 2>/dev/null || echo 1)
  if python3 -c "import sys; sys.exit(0 if float('$taxa')>0.5 else 1)" 2>/dev/null; then
    echo "      !! DESCARTADA: taxa de erro $(python3 -c "print(round(float('$taxa')*100,1))")% -- aplicacao indisponivel?"
    mv "$json" "${json}.invalido" 2>/dev/null || true
    exigir_app_viva
  elif [ $rc -ne 0 ]; then
    echo "      (k6 retornou $rc -- threshold estourado; o summary foi salvo e os dados valem)"
  fi
  # Pausa entre rodadas: deixa o pool de conexoes e o GC voltarem ao repouso,
  # para uma rodada nao contaminar a seguinte.
  sleep 5
}

for rep in $(seq 1 "$REPS"); do
for vus in $NIVEIS; do

  echo; echo "############ REPETICAO $rep | $vus VUs ############"

  # ---------- CENARIO 1: CACHE ----------
  # sem-cache: estado do cache e irrelevante, mas limpamos para nao haver
  # memoria de rodadas anteriores influenciando o Redis.
  curl -s -X DELETE $BASE/api/admin/cache > /dev/null
  rodar cache k6/cenario1-cache.js sem-cache "$vus" "$rep"

  # com-cache-quente: PRE-AQUECE o cache com os 50 IDs usados pelo cenario,
  # para medir o caso "cache cheio" (HIT quase sempre).
  curl -s -X DELETE $BASE/api/admin/cache > /dev/null
  for id in $(seq 1 50); do curl -s "$BASE/api/produtos/$id/com-cache" > /dev/null; done
  rodar cache k6/cenario1-cache.js com-cache-quente "$vus" "$rep"

  # com-cache-frio: cache limpo logo antes + IDs espalhados pelos 2.000 produtos.
  #
  # A TAG do dataset foi mantida ("frio") de proposito, para nao quebrar a
  # rastreabilidade dos arquivos ja coletados em results/. Mas o NOME E
  # IMPRECISO: a medicao deu 98,5% de hit ratio -- o cache aquece em 0,86 s de
  # uma rodada de 25 s. O que esta variante mede e a CARDINALIDADE das chaves
  # (50 vs 2.000 IDs), nao o custo do MISS. Os relatorios exibem o rotulo
  # corrigido; o custo do MISS esta em scripts/experimento-custo-miss.sh.
  curl -s -X DELETE $BASE/api/admin/cache > /dev/null
  rodar cache k6/cenario1-cache.js com-cache-frio "$vus" "$rep"


  # ---------- CENARIO 3: INDICES ----------
  # O indice e removido/criado ENTRE as rodadas; o ANALYZE dentro dos scripts
  # garante que o planner decida com estatisticas atualizadas.
  $PSQL -f /db/11-drop-index.sql > /dev/null 2>&1
  rodar indices k6/cenario3-indices.js sem-indice "$vus" "$rep"

  $PSQL -f /db/10-create-index.sql > /dev/null 2>&1
  rodar indices k6/cenario3-indices.js com-indice "$vus" "$rep"

done
done

# ---------- CENARIO 2: PERSISTENCIA (niveis proprios) ----------
for rep in $(seq 1 "$REPS"); do
for vus in $NIVEIS_PERSISTENCIA; do
  echo; echo "############ PERSISTENCIA | REPETICAO $rep | $vus VUs ############"
  # export (e nao prefixo VAR=x): prefixo antes de uma FUNCAO bash nao chega
  # aos comandos executados dentro dela.
  export LIMITE="$LIMITE_PERSISTENCIA"
  for variante in lazy eager join-fetch entity-graph batch dto nativo; do
    rodar persistencia k6/cenario2-persistencia.js "$variante" "$vus" "$rep"
  done
  unset LIMITE
done
done

# Deixa o banco no estado COM indice (que e o estado final desejado do projeto).
$PSQL -f /db/10-create-index.sql > /dev/null 2>&1

echo; echo "=== Concluido. $(ls results/k6/*.json | wc -l) arquivos de summary em results/k6/ ==="
echo "Proximo passo: python scripts/gerar_graficos.py"
