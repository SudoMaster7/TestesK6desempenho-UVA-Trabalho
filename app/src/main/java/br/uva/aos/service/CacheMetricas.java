package br.uva.aos.service;

import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Contadores do cache expostos em GET /api/admin/cache/stats.
 *
 * Contamos na APLICACAO (e nao so no Redis) porque o que interessa ao
 * relatorio e quantas requisicoes foram resolvidas sem tocar no banco --
 * essa e a metrica do item 3.5 ("quantidade de acessos ao banco de dados").
 */
@Component
public class CacheMetricas {

    private final AtomicLong hits = new AtomicLong();
    private final AtomicLong misses = new AtomicLong();
    private final AtomicLong evictions = new AtomicLong();
    private final AtomicLong acessosBanco = new AtomicLong();

    public void registrarHit() { hits.incrementAndGet(); }
    public void registrarMiss() { misses.incrementAndGet(); }
    public void registrarEviction() { evictions.incrementAndGet(); }
    public void registrarAcessoBanco() { acessosBanco.incrementAndGet(); }

    public void zerar() {
        hits.set(0); misses.set(0); evictions.set(0); acessosBanco.set(0);
    }

    public Map<String, Object> snapshot() {
        long h = hits.get();
        long m = misses.get();
        long total = h + m;
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("hits", h);
        out.put("misses", m);
        out.put("evictions", evictions.get());
        out.put("acessosBanco", acessosBanco.get());
        out.put("totalConsultasComCache", total);
        out.put("hitRatio", total == 0 ? 0.0 : Math.round((h * 10000.0 / total)) / 100.0);
        return out;
    }
}
