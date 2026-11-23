// =====================================================================
// CENARIO 1 - CACHE (item 6.2)
//
// Variantes (escolhidas por VARIANTE=...):
//   sem-cache        -> toda requisicao vai ao banco (linha de base)
//   com-cache-quente -> cache ja preenchido: faixa pequena de IDs -> quase 100% HIT
//   com-cache-espalhado -> cache limpo antes e IDs espalhados pelos 2.000 produtos.
//
// ATENCAO -- LICAO APRENDIDA (nao renomear de volta para "cache-frio"):
// esta variante foi originalmente criada para medir "o custo do cache quando ele
// NAO ajuda". A MEDICAO MOSTROU QUE ELA NAO FAZ ISSO: com 2.000 IDs distintos e
// ~2.300 req/s, o cache aquece em 0,86 s de uma rodada de 25 s, e o hit ratio
// medido foi de 98,5%. Ou seja, ela e QUENTE em ~96% da rodada.
// O que ela realmente mede e o efeito da CARDINALIDADE da faixa de chaves
// (50 vs 2.000 IDs) -- util, mas outra pergunta.
// O custo do MISS e medido de forma deterministica em
// scripts/experimento-custo-miss.sh, que limpa o cache antes de CADA requisicao.
// =====================================================================
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, opcoes, aleatorio } from './lib/config.js';

const VARIANTE = __ENV.VARIANTE || 'sem-cache';
export const options = opcoes(`cache-${VARIANTE}`);

export default function () {
  let url;
  if (VARIANTE === 'sem-cache') {
    // Mesma faixa estreita da variante quente, para a comparacao ser justa.
    url = `${BASE_URL}/api/produtos/${aleatorio(1, 50)}/sem-cache`;
  } else if (VARIANTE === 'com-cache-quente') {
    url = `${BASE_URL}/api/produtos/${aleatorio(1, 50)}/com-cache`;
  } else {
    // Faixa larga: 2.000 IDs distintos (toda a tabela de produtos).
    // Mede o efeito da cardinalidade das chaves, NAO o custo do MISS.
    url = `${BASE_URL}/api/produtos/${aleatorio(1, 2000)}/com-cache`;
  }

  const res = http.get(url, { tags: { variante: VARIANTE } });
  check(res, { 'status 200': (r) => r.status === 200 });
}
