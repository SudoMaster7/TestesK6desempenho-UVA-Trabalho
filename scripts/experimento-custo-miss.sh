#!/usr/bin/env bash
# =====================================================================
# ITEM 3.5 - "O cache SEMPRE melhora o desempenho?"
#
# POR QUE ESTE SCRIPT EXISTE
# --------------------------
# A variante de carga "com-cache-frio" NAO responde a essa pergunta, e isso foi
# descoberto medindo: com 2.000 IDs distintos e ~2.300 req/s, o cache aquece em
# 0,86 s de uma rodada de 25 s. O hit ratio medido foi de 98,5% -- ou seja, a
# variante "fria" e, na pratica, QUENTE em 96% da rodada.
#
# Teste de carga nao e a ferramenta certa para medir o custo do MISS: qualquer
# faixa de IDs que caiba na tabela (2.000 produtos) aquece em menos de 1 segundo.
# A ferramenta certa e a medicao DETERMINISTICA abaixo: o cache e limpo antes de
# CADA requisicao, garantindo 100% de MISS.
#
# O QUE SE ESPERA
# ---------------
#   sem-cache : vai ao banco.                        1 ida  (banco)
#   MISS      : consulta o Redis, vai ao banco,      3 idas (Redis + banco + Redis)
#               grava no Redis.
# Logo o MISS deve ser MAIS LENTO que nao ter cache nenhum. Esse e exatamente o
# custo que o cache cobra quando nao ha reuso.
# =====================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

BASE=${BASE:-http://localhost:8080}
N=${N:-60}
OUT=results/cache/custo-miss.txt
mkdir -p results/cache

tempo_de() {   # $1 = url -> imprime X-Response-Time-Ms
  curl -si "$1" | grep -i '^X-Response-Time-Ms' | tr -d '\r' | awk '{print $2}'
}

{
echo "======================================================================"
echo " O CACHE SEMPRE MELHORA? - medicao deterministica (100% MISS)"
echo " $(date '+%Y-%m-%d %H:%M:%S')   |   $N repeticoes por variante"
echo "======================================================================"
echo
echo "Contexto medido que motivou este teste:"
curl -s "$BASE/api/admin/cache/stats"; echo
echo
} > "$OUT"

# Aquecimento da JVM (descartado): sem isso as primeiras medicoes refletem
# compilacao JIT, nao o custo do cache.
for i in $(seq 1 20); do
  curl -s -o /dev/null "$BASE/api/produtos/$((i % 50 + 1))/sem-cache"
  curl -s -o /dev/null "$BASE/api/produtos/$((i % 50 + 1))/com-cache"
done

echo ">> medindo SEM CACHE ($N requisicoes)..."
sc=""
for i in $(seq 1 $N); do
  id=$(( (i % 50) + 1 ))
  sc="$sc $(tempo_de "$BASE/api/produtos/$id/sem-cache")"
done

echo ">> medindo COM CACHE, 100% MISS (limpa o cache antes de CADA requisicao)..."
ms=""
for i in $(seq 1 $N); do
  id=$(( (i % 50) + 1 ))
  curl -s -X DELETE "$BASE/api/admin/cache" > /dev/null   # garante o MISS
  ms="$ms $(tempo_de "$BASE/api/produtos/$id/com-cache")"
done

echo ">> medindo COM CACHE, 100% HIT (aquece uma vez e repete)..."
curl -s -X DELETE "$BASE/api/admin/cache" > /dev/null
for i in $(seq 1 50); do curl -s -o /dev/null "$BASE/api/produtos/$((i % 50 + 1))/com-cache"; done
ht=""
for i in $(seq 1 $N); do
  id=$(( (i % 50) + 1 ))
  ht="$ht $(tempo_de "$BASE/api/produtos/$id/com-cache")"
done

python3 - "$OUT" "$sc" "$ms" "$ht" <<'PY' >> "$OUT"
import statistics as st, sys

def serie(txt):
    return sorted(float(x) for x in txt.split() if x)

_, out, sc, ms, ht = sys.argv
dados = [("sem cache (1 ida: banco)", serie(sc)),
         ("com cache - MISS (3 idas: Redis+banco+Redis)", serie(ms)),
         ("com cache - HIT (1 ida: Redis)", serie(ht))]

def p(v, q):
    return v[min(int(len(v) * q), len(v) - 1)]

print(f"{'variante':46s} {'n':>4s} {'media':>9s} {'mediana':>9s} {'p95':>9s}")
print("-" * 82)
for nome, v in dados:
    if not v:
        print(f"{nome:46s}  (sem dados)"); continue
    print(f"{nome:46s} {len(v):4d} {st.mean(v):8.2f}ms {st.median(v):8.2f}ms {p(v,.95):8.2f}ms")

base = st.median(dados[0][1])
miss = st.median(dados[1][1])
hit  = st.median(dados[2][1])
print()
print("CONCLUSAO (medianas, menos sensiveis a outliers que a media):")
print(f"  MISS vs sem cache : {miss:.2f} ms vs {base:.2f} ms  "
      f"-> o cache {'CUSTA' if miss > base else 'ja compensa'} "
      f"{abs(miss - base):.2f} ms por requisicao sem reuso")
print(f"  HIT  vs sem cache : {hit:.2f} ms vs {base:.2f} ms  "
      f"-> {base / hit:.1f}x mais rapido quando ha reuso")
if miss > base:
    n = (miss - base) / max(base - hit, 1e-9)
    print(f"  PONTO DE EQUILIBRIO: cada MISS precisa ser seguido de ~{n:.1f} HIT(s) "
          f"para o cache compensar.")
PY

echo
echo ">> gravado: $OUT"
cat "$OUT"
