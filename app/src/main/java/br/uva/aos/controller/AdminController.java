package br.uva.aos.controller;

import br.uva.aos.service.CacheMetricas;
import org.springframework.cache.CacheManager;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Endpoints de apoio aos experimentos:
 *   /api/admin/stats       -> volume de dados (exigido pelo item 6.5)
 *   /api/admin/cache       -> DELETE limpa o cache (cenario de cache frio)
 *   /api/admin/cache/stats -> hits/misses/evictions/acessos ao banco
 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final JdbcTemplate jdbc;
    private final CacheManager cacheManager;
    private final CacheMetricas metricas;

    public AdminController(JdbcTemplate jdbc, CacheManager cacheManager, CacheMetricas metricas) {
        this.jdbc = jdbc;
        this.cacheManager = cacheManager;
        this.metricas = metricas;
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        Map<String, Object> out = new LinkedHashMap<>();
        for (String tabela : new String[]{"categoria", "produto", "cliente", "pedido", "item_pedido"}) {
            out.put(tabela, jdbc.queryForObject("select count(*) from " + tabela, Long.class));
        }
        out.put("indicesPedido", jdbc.queryForList(
                "select indexname from pg_indexes where tablename = 'pedido' order by indexname",
                String.class));
        return out;
    }

    /** Cache frio: usado antes das rodadas k6 que medem o cenario de MISS. */
    @DeleteMapping("/cache")
    public Map<String, Object> limparCache() {
        cacheManager.getCacheNames().forEach(nome -> {
            var c = cacheManager.getCache(nome);
            if (c != null) {
                c.clear();
            }
        });
        metricas.zerar();
        return Map.of("status", "cache limpo e contadores zerados",
                      "caches", cacheManager.getCacheNames());
    }

    @GetMapping("/cache/stats")
    public Map<String, Object> cacheStats() {
        return metricas.snapshot();
    }
}
