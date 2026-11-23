package br.uva.aos.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Só os campos do proprio pedido: usado no endpoint lazy-sem-acesso e no de indices. */
public record PedidoResumoDTO(
        Long id,
        LocalDateTime dataPedido,
        String status,
        BigDecimal valorTotal,
        Long clienteId) {
}
