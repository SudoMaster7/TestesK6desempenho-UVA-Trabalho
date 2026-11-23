package br.uva.aos.config;

import br.uva.aos.dto.CategoriaDTO;
import br.uva.aos.dto.ProdutoDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * ITEM 1 - Configuracao do cache Redis.
 *
 * Por que Redis e nao Caffeine?
 *   - Caffeine e cache LOCAL (dentro da JVM). Com varias instancias da
 *     aplicacao, cada uma teria sua copia e a invalidacao nao propagaria.
 *   - Redis e um cache DISTRIBUIDO e externo: sobrevive ao restart da app,
 *     e compartilhado entre instancias e permite inspecionar as chaves ao vivo
 *     (redis-cli KEYS/TTL/MONITOR) -- o que torna a demonstracao verificavel.
 *   - Contrapartida: cada HIT paga uma ida na rede (~0,2 ms em localhost),
 *     enquanto o Caffeine responderia em nanossegundos. Essa e a razao de o
 *     cache render muito em consulta cara e quase nada em consulta trivial.
 *
 * TTL DIFERENTE POR CACHE, e nao um TTL global:
 *   produtos   -> TTL curto  (preco/estoque mudam) -> limita a janela de dado velho
 *   categorias -> TTL longo  (quase nao muda)      -> maximiza o aproveitamento
 *
 * SERIALIZACAO: um serializer JSON TIPADO por cache.
 * Tentar usar GenericJackson2JsonRedisSerializer com activateDefaultTyping
 * (NON_FINAL) NAO funciona aqui: nossos DTOs sao `record`, que o compilador
 * marca como final, entao o Jackson nao grava o campo de tipo e a LEITURA
 * falha com "need Array value to contain `As.WRAPPER_ARRAY` type information".
 * Declarando o tipo esperado de cada cache o JSON fica limpo (sem metadado de
 * classe), legivel no redis-cli e independente do nome do pacote Java.
 */
@Configuration
public class CacheConfig {

    public static final String CACHE_PRODUTOS = "produtos";
    public static final String CACHE_CATEGORIAS = "categorias";

    @Value("${app.cache.ttl-produto}")
    private Duration ttlProduto;

    @Value("${app.cache.ttl-categoria}")
    private Duration ttlCategoria;

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        ObjectMapper mapper = new ObjectMapper();

        RedisSerializer<ProdutoDTO> produtoSerializer =
                new Jackson2JsonRedisSerializer<>(mapper, ProdutoDTO.class);

        // Para o cache de lista, o tipo precisa ser construido via TypeFactory:
        // List<CategoriaDTO> sofre type erasure e `List.class` perderia o
        // parametro, devolvendo LinkedHashMap em vez de CategoriaDTO.
        RedisSerializer<Object> categoriasSerializer = new Jackson2JsonRedisSerializer<>(
                mapper,
                mapper.getTypeFactory().constructCollectionType(java.util.List.class, CategoriaDTO.class));

        RedisCacheConfiguration base = RedisCacheConfiguration.defaultCacheConfig()
                .disableCachingNullValues() // nao cachear null evita "cache penetration"
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()));

        Map<String, RedisCacheConfiguration> configs = new HashMap<>();
        configs.put(CACHE_PRODUTOS, base.entryTtl(ttlProduto)
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(produtoSerializer)));
        configs.put(CACHE_CATEGORIAS, base.entryTtl(ttlCategoria)
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(categoriasSerializer)));

        return RedisCacheManager.builder(connectionFactory)
                .cacheDefaults(base.entryTtl(ttlProduto)
                        .serializeValuesWith(RedisSerializationContext.SerializationPair
                                .fromSerializer(produtoSerializer)))
                .withInitialCacheConfigurations(configs)
                .build();
    }
}
