package br.uva.aos.entity.batch;

import jakarta.persistence.*;
import org.hibernate.annotations.BatchSize;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Mapeamento LAZY + @BatchSize: o meio-termo entre LAZY puro e JOIN FETCH.
 *
 * Em vez de 1 + N queries, o Hibernate emite 1 + ceil(N/size). Com limite=100 e
 * size=100, a lista de itens de 100 pedidos e resolvida em UMA query extra
 * (`where pedido_id in (...)`), sem o produto cartesiano do JOIN FETCH.
 */
@Entity
@Immutable
@Table(name = "pedido")
public class PedidoBatch {

    @Id
    private Long id;

    @Column(name = "data_pedido")
    private LocalDateTime dataPedido;

    private String status;

    @Column(name = "valor_total")
    private BigDecimal valorTotal;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "cliente_id")
    private ClienteBatch cliente;

    /** @BatchSize na COLECAO: agrupa o carregamento dos itens de varios pedidos. */
    @OneToMany(mappedBy = "pedido", fetch = FetchType.LAZY)
    @BatchSize(size = 100)
    private List<ItemPedidoBatch> itens;

    public Long getId() { return id; }
    public LocalDateTime getDataPedido() { return dataPedido; }
    public String getStatus() { return status; }
    public BigDecimal getValorTotal() { return valorTotal; }
    public ClienteBatch getCliente() { return cliente; }
    public List<ItemPedidoBatch> getItens() { return itens; }
}
