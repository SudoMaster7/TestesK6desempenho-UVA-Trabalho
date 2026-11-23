package br.uva.aos.entity.lazy;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Pedido mapeado com TUDO LAZY.
 *
 * Em LAZY, o Hibernate devolve um PROXY no lugar do objeto relacionado. O SQL
 * extra so e disparado no primeiro acesso a um atributo desse proxy -- e dai
 * vem o N+1: 1 query para a lista de pedidos + N queries (uma por pedido) ao
 * percorrer cliente/itens na montagem do DTO.
 */
@Entity
@Immutable
@Table(name = "pedido")
public class PedidoLazy {

    @Id
    private Long id;

    @Column(name = "data_pedido")
    private LocalDateTime dataPedido;

    private String status;

    @Column(name = "valor_total")
    private BigDecimal valorTotal;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "cliente_id")
    private ClienteLazy cliente;

    @OneToMany(mappedBy = "pedido", fetch = FetchType.LAZY)
    private List<ItemPedidoLazy> itens;

    public Long getId() { return id; }
    public LocalDateTime getDataPedido() { return dataPedido; }
    public String getStatus() { return status; }
    public BigDecimal getValorTotal() { return valorTotal; }
    public ClienteLazy getCliente() { return cliente; }
    public List<ItemPedidoLazy> getItens() { return itens; }
}
