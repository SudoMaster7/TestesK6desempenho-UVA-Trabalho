package br.uva.aos.entity.batch;

import jakarta.persistence.*;
import org.hibernate.annotations.BatchSize;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;

@Entity
@Immutable
@BatchSize(size = 100)
@Table(name = "item_pedido")
public class ItemPedidoBatch {

    @Id
    private Long id;

    private Integer quantidade;

    @Column(name = "preco_unitario")
    private BigDecimal precoUnitario;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pedido_id")
    private PedidoBatch pedido;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "produto_id")
    private ProdutoBatch produto;

    public Long getId() { return id; }
    public Integer getQuantidade() { return quantidade; }
    public BigDecimal getPrecoUnitario() { return precoUnitario; }
    public PedidoBatch getPedido() { return pedido; }
    public ProdutoBatch getProduto() { return produto; }
}
