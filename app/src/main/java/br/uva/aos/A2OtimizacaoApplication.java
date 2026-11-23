package br.uva.aos;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

@SpringBootApplication
@EnableCaching // ITEM 1: ativa o @Cacheable/@CacheEvict do Spring Cache sobre o Redis
public class A2OtimizacaoApplication {

	public static void main(String[] args) {
		SpringApplication.run(A2OtimizacaoApplication.class, args);
	}

}
