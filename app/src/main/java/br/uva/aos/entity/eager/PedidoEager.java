package br.uva.aos.entity.eager;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Pedido mapeado com TUDO EAGER.
 *
 * ATENCAO (ponto que o enunciado pede para observar, item 4.2): EAGER NAO
 * garante "uma unica consulta". Numa consulta derivada como findAll(), o
 * Hibernate primeiro busca os pedidos e depois resolve cada coleacao EAGER --
 * normalmente com uma query por pedido. Ou seja, EAGER pode produzir N+1
 * tambem, com a diferenca de que o custo e pago SEMPRE, mesmo quando o
 * endpoint nao usa os relacionamentos.
 */
@Entity
@Immutable
@Table(name = "pedido")
public class PedidoEager {

    @Id
    private Long id;

    @Column(name = "data_pedido")
    private LocalDateTime dataPedido;

    private String status;

    @Column(name = "valor_total")
    private BigDecimal valorTotal;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "cliente_id")
    private ClienteEager cliente;

    @OneToMany(mappedBy = "pedido", fetch = FetchType.EAGER)
    private List<ItemPedidoEager> itens;

    public Long getId() { return id; }
    public LocalDateTime getDataPedido() { return dataPedido; }
    public String getStatus() { return status; }
    public BigDecimal getValorTotal() { return valorTotal; }
    public ClienteEager getCliente() { return cliente; }
    public List<ItemPedidoEager> getItens() { return itens; }
}
