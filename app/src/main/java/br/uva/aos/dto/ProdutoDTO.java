package br.uva.aos.dto;

import java.io.Serializable;
import java.math.BigDecimal;

/**
 * Objeto que vai para o cache (ITEM 1).
 *
 * Cacheamos um DTO, nunca a entidade JPA. Motivos:
 *   - entidade carrega estado de sessao/proxies do Hibernate, que nao
 *     sobrevivem a serializacao e podem causar LazyInitializationException;
 *   - o DTO e estavel e pequeno -> menos bytes no Redis e no payload HTTP.
 *
 * Serializable + record: serializado como JSON pelo RedisCacheManager.
 */
public record ProdutoDTO(
        Long id,
        String nome,
        String sku,
        BigDecimal preco,
        Integer estoque,
        Long categoriaId,
        String categoriaNome
) implements Serializable {
}
