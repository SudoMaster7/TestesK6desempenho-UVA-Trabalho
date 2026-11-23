// =====================================================================
// ITEM 3 - Configuracao comum dos testes de carga (Grafana k6).
//
// POR QUE k6?
//   - cenarios em JavaScript versionaveis no repositorio (reprodutibilidade);
//   - consumo proprio baixo (escrito em Go) -> o gerador de carga nao rouba
//     CPU da aplicacao medida, problema comum com JMeter na mesma maquina;
//   - exporta percentis (p95/p99) e taxa de erro em JSON direto, sem GUI.
// =====================================================================

// Nivel de carga: 10 (baixo), 50 (medio), 100 (alto), 200 (muito alto).
export const VUS = parseInt(__ENV.VUS || '10', 10);
export const DURATION = __ENV.DURATION || '60s';
export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

// MODO=aquecimento -> rodada curta cujo resultado e JOGADO FORA.
// MODO=medicao     -> rodada que vale e e exportada para results/k6/.
//
// POR QUE DUAS EXECUCOES SEPARADAS DO k6, e nao dois `scenarios` no mesmo run?
// Porque o `--summary-export` agrega TODAS as metricas da execucao: se o
// aquecimento estivesse no mesmo run, suas latencias altas (JVM ainda
// interpretando o bytecode, pool de conexoes vazio, cache de buffers do
// Postgres frio) entrariam na media e nos percentis -- exatamente o que o item
// 6.5 do enunciado manda evitar. Separando os processos, o JSON exportado
// contem somente a fase de medicao.
export const MODO = __ENV.MODO || 'medicao';

export function opcoes(nomeCenario) {
  const aquecendo = MODO === 'aquecimento';
  return {
    vus: aquecendo ? Math.max(1, Math.floor(VUS / 5)) : VUS,
    duration: aquecendo ? (__ENV.WARMUP || '15s') : DURATION,
    // Metricas obrigatorias do item 6.4: media, p95, p99 (+ min/med/max).
    summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
    thresholds: {
      // Taxa de erros: o enunciado exige reportar. O teto e alto de proposito
      // para o teste NAO abortar sob carga -- queremos REGISTRAR a degradacao,
      // nao esconde-la. Um threshold apertado encerraria o teste antes do fim.
      http_req_failed: ['rate<0.25'],
    },
    tags: { cenario: nomeCenario, modo: MODO },
    gracefulStop: '5s',
  };
}

/** Retorna um inteiro no intervalo [min, max]. */
export function aleatorio(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
