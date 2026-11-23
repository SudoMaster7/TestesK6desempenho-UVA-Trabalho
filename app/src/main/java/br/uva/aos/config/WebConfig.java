package br.uva.aos.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Libera o CORS para o painel docs/dashboard.html (aba "Teste ao vivo").
 *
 * O painel e aberto direto do disco (file://), entao o navegador o trata como
 * outra origem. Sem esta configuracao o fetch() e bloqueado e, mesmo liberado,
 * o JavaScript NAO enxerga headers customizados: por isso os headers de
 * diagnostico precisam ser listados explicitamente em exposedHeaders.
 *
 * Projeto academico, rodando apenas em localhost: liberar qualquer origem e
 * aceitavel aqui. Em producao, restrinja allowedOriginPatterns.
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .exposedHeaders("X-Query-Count", "X-Response-Time-Ms", "X-Cache");
    }
}
