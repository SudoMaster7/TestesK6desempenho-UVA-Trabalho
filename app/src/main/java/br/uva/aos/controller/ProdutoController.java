package br.uva.aos.controller;

import br.uva.aos.dto.ProdutoDTO;
import br.uva.aos.service.CacheInstrumentado;
import br.uva.aos.service.ProdutoService;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;

/** ITEM 1 - Endpoints de comparacao sem cache x com cache. */
@RestController
@RequestMapping("/api/produtos")
public class ProdutoController {

    private final ProdutoService service;
    private final CacheInstrumentado cacheInstrumentado;

    public ProdutoController(ProdutoService service, CacheInstrumentado cacheInstrumentado) {
        this.service = service;
        this.cacheInstrumentado = cacheInstrumentado;
    }

    /** CENARIO A: toda requisicao vai ao banco (X-Cache: BYPASS, X-Query-Count: 1). */
    @GetMapping("/{id}/sem-cache")
    public ResponseEntity<ProdutoDTO> semCache(@PathVariable Long id) {
        ProdutoDTO dto = service.buscarSemCache(id);
        return dto == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(dto);
    }

    /** CENARIO B: 1o acesso MISS (X-Query-Count: 1), seguintes HIT (X-Query-Count: 0). */
    @GetMapping("/{id}/com-cache")
    public ResponseEntity<ProdutoDTO> comCache(@PathVariable Long id) {
        ProdutoDTO dto = cacheInstrumentado.produtoComCache(id);
        return dto == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(dto);
    }

    /** Operacao de atualizacao (item 3.4, passo 3): dispara a invalidacao do cache. */
    @PutMapping("/{id}")
    public ResponseEntity<ProdutoDTO> atualizar(@PathVariable Long id,
                                                @RequestBody AtualizarProdutoRequest req) {
        ProdutoDTO dto = service.atualizar(id, req.preco(), req.estoque());
        return dto == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(dto);
    }

    public record AtualizarProdutoRequest(
            @NotNull BigDecimal preco,
            @NotNull @PositiveOrZero Integer estoque) {
    }
}
