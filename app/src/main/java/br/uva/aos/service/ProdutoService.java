package br.uva.aos.service;

import br.uva.aos.config.CacheConfig;
import br.uva.aos.diag.CacheStatusHolder;
import br.uva.aos.dto.ProdutoDTO;
import br.uva.aos.entity.Produto;
import br.uva.aos.repository.ProdutoRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

/**
 * ITEM 1 - Cache de leitura do detalhe do produto.
 *
 * PADRAO USADO: cache-aside (lazy loading / look-aside).
 *   leitura  -> procura no cache; se nao achar, le o banco e grava no cache
 *   escrita  -> grava no banco e INVALIDA a chave (write-invalidate)
 *
 * Por que @CacheEvict e nao @CachePut?
 *   @CachePut sobrescreveria o cache com o valor que a aplicacao ACHA que ficou
 *   no banco. Se o banco tiver trigger, default ou outra transacao concorrente,
 *   o cache guardaria um valor que nunca existiu. O @CacheEvict apaga e deixa a
 *   proxima leitura reconstruir a partir da fonte da verdade (o banco): e mais
 *   seguro, ao custo de um MISS extra. Decisao registrada no README (secao 3).
 */
@Service
public class ProdutoService {

    private static final Logger log = LoggerFactory.getLogger(ProdutoService.class);

    private final ProdutoRepository repository;
    private final CacheMetricas metricas;
    private final CacheManager cacheManager;

    /** Quando false (profile cache-sem-invalidacao) o cache NAO e invalidado no update. */
    @Value("${app.cache.invalidacao-ativa:true}")
    private boolean invalidacaoAtiva;

    public ProdutoService(ProdutoRepository repository,
                          CacheMetricas metricas,
                          CacheManager cacheManager) {
        this.repository = repository;
        this.metricas = metricas;
        this.cacheManager = cacheManager;
    }

    /** CENARIO A - sempre consulta o banco. Serve de linha de base. */
    @Transactional(readOnly = true)
    public ProdutoDTO buscarSemCache(Long id) {
        CacheStatusHolder.set(CacheStatusHolder.Status.BYPASS);
        metricas.registrarAcessoBanco();
        return toDTO(repository.buscarComCategoria(id));
    }

    /**
     * CENARIO B - com cache.
     *
     * NOTA IMPORTANTE SOBRE O @Cacheable: quando ha HIT o Spring intercepta a
     * chamada e este metodo NAO executa -- por isso o HIT e registrado fora
     * daqui (ver CacheInstrumentado). O corpo deste metodo so roda no MISS, e e
     * exatamente isso que o X-Query-Count comprova.
     */
    @Cacheable(cacheNames = CacheConfig.CACHE_PRODUTOS, key = "#id")
    @Transactional(readOnly = true)
    public ProdutoDTO buscarComCache(Long id) {
        log.info("CACHE MISS produtos::{} -> consultando o banco", id);
        metricas.registrarMiss();
        metricas.registrarAcessoBanco();
        return toDTO(repository.buscarComCategoria(id));
    }

    /**
     * Operacao de ATUALIZACAO exigida pelo enunciado (item 3.4, passo 3).
     * Com invalidacao ativa, a chave do produto e removida do Redis -> a proxima
     * leitura devolve o dado novo. Sem invalidacao (profile alternativo), a
     * leitura continua devolvendo o preco ANTIGO ate o TTL expirar.
     */
    @Transactional
    public ProdutoDTO atualizar(Long id, BigDecimal preco, Integer estoque) {
        repository.atualizarPrecoEstoque(id, preco, estoque);
        if (invalidacaoAtiva) {
            // Invalidacao via CacheManager e nao via @CacheEvict nesta classe:
            // chamar um metodo @CacheEvict da PROPRIA classe (self-invocation)
            // nao passa pelo proxy do Spring e o cache nunca seria limpo --
            // o bug ficaria invisivel, pois o metodo "roda" sem erro nenhum.
            var cache = cacheManager.getCache(CacheConfig.CACHE_PRODUTOS);
            if (cache != null) {
                cache.evict(id);
            }
            metricas.registrarEviction();
            log.info("CACHE EVICT produtos::{}", id);
        } else {
            log.warn("INVALIDACAO DESLIGADA: produtos::{} segue com o valor antigo ate o TTL expirar", id);
        }
        return toDTO(repository.buscarComCategoria(id));
    }

    private ProdutoDTO toDTO(Produto p) {
        if (p == null) {
            return null;
        }
        return new ProdutoDTO(p.getId(), p.getNome(), p.getSku(), p.getPreco(), p.getEstoque(),
                p.getCategoria() == null ? null : p.getCategoria().getId(),
                p.getCategoria() == null ? null : p.getCategoria().getNome());
    }
}
