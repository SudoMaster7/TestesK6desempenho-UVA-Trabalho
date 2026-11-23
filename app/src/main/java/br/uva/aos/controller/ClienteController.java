package br.uva.aos.controller;

import br.uva.aos.dto.PedidoResumoDTO;
import br.uva.aos.service.PedidoService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * FASE 5 - consulta-alvo 1 do experimento de indices:
 *   WHERE cliente_id = ? ORDER BY data_pedido DESC LIMIT 50
 *
 * Sem indice -> Seq Scan + Sort. Com idx_pedido_cliente_data -> Index Scan e o
 * no Sort desaparece (o indice ja esta na ordem pedida).
 */
@RestController
@RequestMapping("/api/clientes")
@Validated
public class ClienteController {

    private final PedidoService service;

    public ClienteController(PedidoService service) {
        this.service = service;
    }

    @GetMapping("/{id}/pedidos")
    public List<PedidoResumoDTO> pedidosDoCliente(
            @PathVariable Long id,
            @RequestParam(defaultValue = "50") @Min(1) @Max(1000) int limite) {
        return service.pedidosPorCliente(id, limite);
    }
}
