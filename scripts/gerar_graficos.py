#!/usr/bin/env python3
"""
ITEM 3 / 6.6 - Consolida os summaries do k6 e gera tabelas e graficos.

Entrada : results/k6/*.json   (um por cenario/variante/nivel/repeticao)
Saidas  : results/resumo.csv            -> todas as rodadas, linha a linha
          results/resumo_medio.csv      -> media das repeticoes
          docs/img/*.png                -> graficos do relatorio
          docs/tabelas.md               -> tabelas Markdown prontas para colar
          docs/dados.json               -> dados que alimentam o dashboard HTML

REGRA DE OURO DO TRABALHO: este script NUNCA inventa numero. Se um arquivo de
summary nao existe, a linha simplesmente nao aparece.
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sem janela: roda em terminal/CI
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIR_K6 = RAIZ / "results" / "k6"
DIR_IMG = RAIZ / "docs" / "img"
DIR_IMG.mkdir(parents=True, exist_ok=True)

# cache_com-cache-quente_100vu_r2.json -> (cache, com-cache-quente, 100, 2)
PADRAO = re.compile(r"^(?P<cenario>[a-z]+)_(?P<variante>.+)_(?P<vus>\d+)vu_r(?P<rep>\d+)\.json$")


def carregar() -> pd.DataFrame:
    linhas = []
    for arq in sorted(DIR_K6.glob("*.json")):
        m = PADRAO.match(arq.name)
        if not m:
            continue
        dados = json.loads(arq.read_text(encoding="utf-8"))
        met = dados.get("metrics", {})
        dur = met.get("http_req_duration", {})
        reqs = met.get("http_reqs", {})
        falhas = met.get("http_req_failed", {})

        # ARMADILHA do JSON do k6: em http_req_failed, "passes" conta as
        # requisicoes que FALHARAM e "fails" as que passaram (a metrica e uma
        # Rate sobre o predicado "falhou"). Uma rodada perfeita aparece como
        # {"passes": 0, "fails": 14764} -- o que parece 100% de erro para quem
        # le rapido. O campo correto e "value": a TAXA (0..1) de falhas.
        taxa_erro = falhas.get("value", 0.0) or 0.0

        linhas.append({
            "cenario": m.group("cenario"),
            "variante": m.group("variante"),
            "vus": int(m.group("vus")),
            "repeticao": int(m.group("rep")),
            "latencia_media_ms": round(dur.get("avg", 0.0), 2),
            "latencia_med_ms": round(dur.get("med", 0.0), 2),
            "latencia_p95_ms": round(dur.get("p(95)", 0.0), 2),
            "latencia_p99_ms": round(dur.get("p(99)", 0.0), 2),
            "latencia_max_ms": round(dur.get("max", 0.0), 2),
            "throughput_req_s": round(reqs.get("rate", 0.0), 2),
            "requisicoes": int(reqs.get("count", 0)),
            "taxa_erro_pct": round(taxa_erro * 100, 3),
        })
    return pd.DataFrame(linhas)


def grafico_linha(df, cenario, metrica, titulo, ylabel, arquivo, log=False):
    sub = df[df.cenario == cenario]
    if sub.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for variante, g in sub.groupby("variante"):
        g = g.sort_values("vus")
        ax.plot(g.vus, g[metrica], marker="o", label=variante)
    ax.set_title(titulo)
    ax.set_xlabel("Usuarios virtuais simultaneos (VUs)")
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("log")
        ax.set_ylabel(ylabel + " (escala log)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    destino = DIR_IMG / arquivo
    fig.savefig(destino, dpi=130)
    plt.close(fig)
    return destino


def grafico_barras(df, cenario, vus, arquivo, titulo):
    sub = df[(df.cenario == cenario) & (df.vus == vus)].sort_values("latencia_p95_ms")
    if sub.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(sub))
    ax.bar([i - 0.2 for i in x], sub.latencia_media_ms, width=0.4, label="media")
    ax.bar([i + 0.2 for i in x], sub.latencia_p95_ms, width=0.4, label="p95")
    ax.set_xticks(list(x))
    ax.set_xticklabels(sub.variante, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Latencia (ms)")
    ax.set_title(f"{titulo} - {vus} VUs")
    ax.grid(alpha=0.3, axis="y")
    ax.legend()
    fig.tight_layout()
    destino = DIR_IMG / arquivo
    fig.savefig(destino, dpi=130)
    plt.close(fig)
    return destino


def main():
    df = carregar()
    if df.empty:
        print("Nenhum summary encontrado em results/k6/. Rode scripts/run-all-tests.sh antes.")
        return

    df = df.sort_values(["cenario", "variante", "vus", "repeticao"])
    df.to_csv(RAIZ / "results" / "resumo.csv", index=False)

    # Media das repeticoes: e o numero que vai para o relatorio. Guardamos
    # tambem o desvio do p95 para evidenciar a consistencia (item 6.5).
    medio = (df.groupby(["cenario", "variante", "vus"], as_index=False)
               .agg(repeticoes=("repeticao", "count"),
                    latencia_media_ms=("latencia_media_ms", "mean"),
                    latencia_p95_ms=("latencia_p95_ms", "mean"),
                    latencia_p95_desvio=("latencia_p95_ms", "std"),
                    latencia_p99_ms=("latencia_p99_ms", "mean"),
                    throughput_req_s=("throughput_req_s", "mean"),
                    taxa_erro_pct=("taxa_erro_pct", "mean"))
               .round(2))
    medio.to_csv(RAIZ / "results" / "resumo_medio.csv", index=False)

    imagens = []
    for cen, titulo in [("cache", "Cenario 1 - Cache"),
                        ("persistencia", "Cenario 2 - Estrategias de persistencia"),
                        ("indices", "Cenario 3 - Indices")]:
        imagens += [
            grafico_linha(medio, cen, "latencia_p95_ms", f"{titulo}: latencia p95 por carga",
                          "p95 (ms)", f"{cen}_p95.png", log=(cen == "persistencia")),
            grafico_linha(medio, cen, "throughput_req_s", f"{titulo}: throughput por carga",
                          "requisicoes/s", f"{cen}_throughput.png"),
        ]
        maior = medio[medio.cenario == cen].vus.max()
        if pd.notna(maior):
            imagens.append(grafico_barras(medio, cen, int(maior), f"{cen}_barras.png", titulo))

    # ---- tabelas Markdown prontas para o README ----
    partes = ["# Tabelas de resultados (geradas por scripts/gerar_graficos.py)\n",
              "> Todos os valores vem de execucoes reais salvas em `results/k6/`.\n"]
    for cen in ["cache", "persistencia", "indices"]:
        sub = medio[medio.cenario == cen]
        if sub.empty:
            continue
        partes.append(f"\n## Cenario: {cen}\n")
        cols = ["variante", "vus", "latencia_media_ms", "latencia_p95_ms",
                "latencia_p99_ms", "throughput_req_s", "taxa_erro_pct", "repeticoes"]
        partes.append(sub[cols].to_markdown(index=False))
        partes.append("\n")
    (RAIZ / "docs" / "tabelas.md").write_text("\n".join(partes), encoding="utf-8")

    # ---- dados para o dashboard HTML ----
    (RAIZ / "docs" / "dados.json").write_text(
        json.dumps({"rodadas": df.to_dict("records"),
                    "medias": medio.to_dict("records")}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"{len(df)} rodadas lidas | {medio.shape[0]} combinacoes cenario/variante/carga")
    print("-> results/resumo.csv, results/resumo_medio.csv")
    print("-> docs/tabelas.md, docs/dados.json")
    for i in [i for i in imagens if i]:
        print(f"-> {i.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
