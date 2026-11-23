package br.uva.aos.service;

import br.uva.aos.config.CacheConfig;
import br.uva.aos.diag.CacheStatusHolder;
import br.uva.aos.dto.CategoriaDTO;
import br.uva.aos.repository.CategoriaRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

/**
 * ITEM 1 - Cache da lista de categorias.
 * Lista pequena, lida em quase toda tela e praticamente imutavel: o caso de
 * cache com melhor relacao beneficio/risco do sistema (TTL de 10 minutos).
 */
@Service
public class CategoriaService {

    private static final Logger log = LoggerFactory.getLogger(CategoriaService.class);
    public static final String CHAVE_LISTA = "todas";

    private final CategoriaRepository repository;
    private final CacheMetricas metricas;

    public CategoriaService(CategoriaRepository repository, CacheMetricas metricas) {
        this.repository = repository;
        this.metricas = metricas;
    }

    @Transactional(readOnly = true)
    public List<CategoriaDTO> listarSemCache() {
        CacheStatusHolder.set(CacheStatusHolder.Status.BYPASS);
        metricas.registrarAcessoBanco();
        return consultarBanco();
    }

    @Cacheable(cacheNames = CacheConfig.CACHE_CATEGORIAS, key = "'" + CHAVE_LISTA + "'")
    @Transactional(readOnly = true)
    public List<CategoriaDTO> listarComCache() {
        log.info("CACHE MISS categorias::{} -> consultando o banco", CHAVE_LISTA);
        metricas.registrarMiss();
        metricas.registrarAcessoBanco();
        return consultarBanco();
    }

    @CacheEvict(cacheNames = CacheConfig.CACHE_CATEGORIAS, allEntries = true)
    public void invalidarTudo() {
        metricas.registrarEviction();
        log.info("CACHE EVICT categorias (todas as entradas)");
    }

    private List<CategoriaDTO> consultarBanco() {
        List<CategoriaDTO> out = new ArrayList<>();
        repository.findAll().forEach(c ->
                out.add(new CategoriaDTO(c.getId(), c.getNome(), c.getDescricao())));
        return out;
    }
}
