package br.uva.aos.entity.eager;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;

@Entity
@Immutable
@Table(name = "item_pedido")
public class ItemPedidoEager {

    @Id
    private Long id;

    private Integer quantidade;

    @Column(name = "preco_unitario")
    private BigDecimal precoUnitario;

    @ManyToOne(fetch = FetchType.LAZY) // o lado "dono" fica LAZY para nao voltar ao pedido
    @JoinColumn(name = "pedido_id")
    private PedidoEager pedido;

    /** EAGER: carregado junto com o item, sempre, mesmo que ninguem use. */
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "produto_id")
    private ProdutoEager produto;

    public Long getId() { return id; }
    public Integer getQuantidade() { return quantidade; }
    public BigDecimal getPrecoUnitario() { return precoUnitario; }
    public PedidoEager getPedido() { return pedido; }
    public ProdutoEager getProduto() { return produto; }
}
