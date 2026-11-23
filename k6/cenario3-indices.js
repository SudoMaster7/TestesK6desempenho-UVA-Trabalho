// =====================================================================
// CENARIO 3 - INDICES (item 6.2)
//
// A MESMA requisicao e medida duas vezes: com a tabela sem indice e depois com
// o indice criado. Quem aplica/remove o indice entre as rodadas e o
// run-all-tests (o k6 nao mexe no banco).
//
// cliente_id ALEATORIO de proposito: com um unico id fixo o Postgres manteria
// as mesmas paginas no cache de buffers e o Seq Scan pareceria mais rapido do
// que realmente e.
// =====================================================================
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, opcoes, aleatorio } from './lib/config.js';

const VARIANTE = __ENV.VARIANTE || 'sem-indice';
export const options = opcoes(`indices-${VARIANTE}`);

export default function () {
  const res = http.get(
      `${BASE_URL}/api/clientes/${aleatorio(1, 20000)}/pedidos?limite=50`,
      { tags: { variante: VARIANTE } });
  check(res, { 'status 200': (r) => r.status === 200 });
}
