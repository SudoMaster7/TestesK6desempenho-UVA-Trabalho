// =====================================================================
// CENARIO 2 - ESTRATEGIAS DE PERSISTENCIA (item 6.2)
//
// Compara, com o MESMO ?limite=, as implementacoes:
//   lazy (N+1) | eager | join-fetch | entity-graph | batch | dto | nativo
//
// O limite padrao e 100: suficiente para o N+1 doer (ordem de 500 queries por
// requisicao) sem estourar o timeout com 200 VUs.
// =====================================================================
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, opcoes } from './lib/config.js';

const VARIANTE = __ENV.VARIANTE || 'lazy';
const LIMITE = __ENV.LIMITE || '100';
export const options = opcoes(`persistencia-${VARIANTE}`);

export default function () {
  const res = http.get(`${BASE_URL}/api/pedidos/${VARIANTE}?limite=${LIMITE}`,
                       { tags: { variante: VARIANTE, limite: LIMITE } });
  check(res, { 'status 200': (r) => r.status === 200 });
}
