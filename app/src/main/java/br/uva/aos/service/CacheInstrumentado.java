package br.uva.aos.service;

import br.uva.aos.config.CacheConfig;
import br.uva.aos.diag.CacheStatusHolder;
import br.uva.aos.dto.CategoriaDTO;
import br.uva.aos.dto.ProdutoDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.CacheManager;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Fachada de observabilidade do cache.
 *
 * POR QUE ESTA CLASSE EXISTE (armadilha classica do Spring Cache):
 * o @Cacheable e implementado por um PROXY em volta do bean. Se um metodo da
 * mesma classe chama o metodo anotado diretamente (self-invocation), a chamada
 * nao passa pelo proxy e o cache NUNCA e consultado -- todo acesso vira MISS.
 *
 * Foi exatamente o que aconteceu na 1a versao deste projeto: a checagem
 * HIT/MISS morava dentro do ProdutoService e chamava buscarComCache() na
 * propria classe, resultando em "X-Cache: MISS" e X-Query-Count: 1 em TODAS as
 * requisicoes. Separando a instrumentacao num bean distinto, a chamada volta a
 * atravessar o proxy e o cache funciona.
 */
@Component
public class CacheInstrumentado {

    private static final Logger log = LoggerFactory.getLogger(CacheInstrumentado.class);

    private final ProdutoService produtoService;
    private final CategoriaService categoriaService;
    private final CacheManager cacheManager;
    private final CacheMetricas metricas;

    public CacheInstrumentado(ProdutoService produtoService,
                              CategoriaService categoriaService,
                              CacheManager cacheManager,
                              CacheMetricas metricas) {
        this.produtoService = produtoService;
        this.categoriaService = categoriaService;
        this.cacheManager = cacheManager;
        this.metricas = metricas;
    }

    public ProdutoDTO produtoComCache(Long id) {
        boolean presente = presente(CacheConfig.CACHE_PRODUTOS, id);
        if (presente) {
            CacheStatusHolder.set(CacheStatusHolder.Status.HIT);
            metricas.registrarHit();
            log.debug("CACHE HIT produtos::{}", id);
        } else {
            CacheStatusHolder.set(CacheStatusHolder.Status.MISS);
        }
        // Chamada em OUTRO bean -> atravessa o proxy -> o @Cacheable e aplicado
        return produtoService.buscarComCache(id);
    }

    public List<CategoriaDTO> categoriasComCache() {
        if (presente(CacheConfig.CACHE_CATEGORIAS, CategoriaService.CHAVE_LISTA)) {
            CacheStatusHolder.set(CacheStatusHolder.Status.HIT);
            metricas.registrarHit();
            log.debug("CACHE HIT categorias::{}", CategoriaService.CHAVE_LISTA);
        } else {
            CacheStatusHolder.set(CacheStatusHolder.Status.MISS);
        }
        return categoriaService.listarComCache();
    }

    private boolean presente(String cacheName, Object chave) {
        var cache = cacheManager.getCache(cacheName);
        return cache != null && cache.get(chave) != null;
    }
}
