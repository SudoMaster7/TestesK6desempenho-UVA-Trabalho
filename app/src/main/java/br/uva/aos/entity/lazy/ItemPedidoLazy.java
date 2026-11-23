package br.uva.aos.entity.lazy;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;

@Entity
@Immutable
@Table(name = "item_pedido")
public class ItemPedidoLazy {

    @Id
    private Long id;

    private Integer quantidade;

    @Column(name = "preco_unitario")
    private BigDecimal precoUnitario;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pedido_id")
    private PedidoLazy pedido;

    /** LAZY: o produto so e carregado quando getProduto().getNome() for chamado. */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "produto_id")
    private ProdutoLazy produto;

    public Long getId() { return id; }
    public Integer getQuantidade() { return quantidade; }
    public BigDecimal getPrecoUnitario() { return precoUnitario; }
    public PedidoLazy getPedido() { return pedido; }
    public ProdutoLazy getProduto() { return produto; }
}
