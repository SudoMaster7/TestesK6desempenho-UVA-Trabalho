package br.uva.aos.controller;

import br.uva.aos.dto.PedidoDTO;
import br.uva.aos.dto.PedidoResumoDTO;
import br.uva.aos.service.PedidoService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

/**
 * ITENS 2a/2b/2c - um endpoint por estrategia, todos com o mesmo ?limite=.
 *
 * Como comparar: rode o mesmo limite em cada endpoint e compare o header
 * X-Query-Count (quantidade de SQL) junto com X-Response-Time-Ms.
 */
@RestController
@RequestMapping("/api/pedidos")
@Validated
public class PedidoController {

    private final PedidoService service;

    public PedidoController(PedidoService service) {
        this.service = service;
    }

    // ---------------- FASE 3: LAZY vs EAGER ----------------

    /** LAZY acessando os relacionamentos -> N+1 visivel no X-Query-Count. */
    @GetMapping("/lazy")
    public List<PedidoDTO> lazy(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarLazy(limite);
    }

    /** LAZY sem tocar nos relacionamentos -> 1 query, a vantagem do LAZY. */
    @GetMapping("/lazy-sem-acesso")
    public List<PedidoResumoDTO> lazySemAcesso(
            @RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarLazySemAcesso(limite);
    }

    /** EAGER -> carrega sempre; observar se resolve em 1 query ou tambem gera N+1. */
    @GetMapping("/eager")
    public List<PedidoDTO> eager(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarEager(limite);
    }

    // ---------------- FASE 4: estrategias otimizadas ----------------

    @GetMapping("/join-fetch")
    public List<PedidoDTO> joinFetch(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarJoinFetch(limite);
    }

    @GetMapping("/entity-graph")
    public List<PedidoDTO> entityGraph(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarEntityGraph(limite);
    }

    @GetMapping("/batch")
    public List<PedidoDTO> batch(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarBatch(limite);
    }

    @GetMapping("/dto")
    public List<PedidoDTO> dto(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarProjecaoDTO(limite);
    }

    @GetMapping("/nativo")
    public List<PedidoDTO> nativo(@RequestParam(defaultValue = "100") @Min(1) @Max(2000) int limite) {
        return service.listarNativo(limite);
    }

    // ---------------- FASE 5: consultas do experimento de indices ----------------

    /**
     * Consulta-alvo 2: intervalo de datas + status.
     * Sem indice: Seq Scan em 300k linhas. Com idx_pedido_data_status: Index Scan.
     */
    @GetMapping("/periodo")
    public List<PedidoResumoDTO> porPeriodo(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime inicio,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime fim,
            @RequestParam(defaultValue = "PAGO") String status,
            @RequestParam(defaultValue = "50") @Min(1) @Max(1000) int limite) {
        return service.pedidosPorPeriodo(inicio, fim, status, limite);
    }
}
