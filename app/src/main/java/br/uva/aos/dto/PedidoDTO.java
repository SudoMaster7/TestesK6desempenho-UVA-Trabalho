package br.uva.aos.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Payload unico para TODAS as estrategias de persistencia (lazy, eager,
 * join-fetch, entity-graph, batch, dto, nativo).
 *
 * Usar o mesmo DTO em todos os endpoints e essencial para a comparacao ser
 * honesta: se cada endpoint devolvesse um formato diferente, parte da diferenca
 * de tempo viria da serializacao, nao da estrategia de carregamento.
 */
public record PedidoDTO(
        Long id,
        LocalDateTime dataPedido,
        String status,
        BigDecimal valorTotal,
        Long clienteId,
        String clienteNome,
        String clienteCidade,
        List<ItemDTO> itens
) {
    public record ItemDTO(
            Long id,
            Long produtoId,
            String produtoNome,
            Integer quantidade,
            BigDecimal precoUnitario) {
    }
}
