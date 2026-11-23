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

    // ------------------------------------------------------------------
    // Apoio a demonstracao ao vivo do item 2c (aba "Teste ao vivo" do painel).
    // Fazem o mesmo que db/10-create-index.sql e db/11-drop-index.sql.
    // ------------------------------------------------------------------

    /** POST /api/admin/indices/criar | /api/admin/indices/remover */
    @PostMapping("/indices/{acao}")
    public Map<String, Object> indices(@PathVariable String acao) {
        long inicio = System.nanoTime();
        switch (acao) {
            case "criar" -> {
                jdbc.execute("CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data ON pedido (cliente_id, data_pedido DESC)");
                jdbc.execute("CREATE INDEX IF NOT EXISTS idx_pedido_data_status ON pedido (data_pedido, status)");
            }
            case "remover" -> {
                jdbc.execute("DROP INDEX IF EXISTS idx_pedido_cliente_data");
                jdbc.execute("DROP INDEX IF EXISTS idx_pedido_data_status");
            }
            default -> throw new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.BAD_REQUEST, "acao deve ser 'criar' ou 'remover'");
        }
        jdbc.execute("ANALYZE pedido");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("acao", acao);
        out.put("duracaoMs", Math.round((System.nanoTime() - inicio) / 1_000_000.0));
        out.put("indicesPedido", jdbc.queryForList(
                "select indexname from pg_indexes where tablename = 'pedido' order by indexname",
                String.class));
        return out;
    }

    /**
     * EXPLAIN ANALYZE da consulta-alvo do item 2c. Executa 2 vezes e devolve a
     * 2a: a 1a pode ler do disco e mediria o cache de blocos, nao o indice.
     */
    @GetMapping("/explain")
    public Map<String, Object> explain(@RequestParam(defaultValue = "150") long clienteId) {
        String sql = "EXPLAIN ANALYZE SELECT * FROM pedido WHERE cliente_id = " + clienteId
                + " ORDER BY data_pedido DESC LIMIT 50";
        jdbc.queryForList(sql, String.class); // aquecimento, descartado
        var plano = jdbc.queryForList(sql, String.class);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("consulta", "SELECT * FROM pedido WHERE cliente_id = " + clienteId
                + " ORDER BY data_pedido DESC LIMIT 50");
        out.put("plano", plano);
        out.put("indicesPedido", jdbc.queryForList(
                "select indexname from pg_indexes where tablename = 'pedido' order by indexname",
                String.class));
        return out;
    }
}
