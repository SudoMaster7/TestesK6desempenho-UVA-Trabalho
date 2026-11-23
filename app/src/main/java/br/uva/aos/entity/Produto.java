package br.uva.aos.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

/**
 * Produto - alta frequencia de leitura, mas preco/estoque sao VOLATEIS.
 * Por isso o cache de produto usa TTL curto + invalidacao ativa no update.
 *
 * O relacionamento com Categoria e EAGER aqui porque o DTO de detalhe SEMPRE
 * mostra o nome da categoria: deixar LAZY so adicionaria uma segunda query.
 * (Decisao registrada no README, secao 3.)
 */
@Entity
@Table(name = "produto")
public class Produto {

    @Id
    private Long id;

    private String nome;
    private String sku;
    private BigDecimal preco;
    private Integer estoque;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "categoria_id")
    private Categoria categoria;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getNome() { return nome; }
    public void setNome(String nome) { this.nome = nome; }
    public String getSku() { return sku; }
    public void setSku(String sku) { this.sku = sku; }
    public BigDecimal getPreco() { return preco; }
    public void setPreco(BigDecimal preco) { this.preco = preco; }
    public Integer getEstoque() { return estoque; }
    public void setEstoque(Integer estoque) { this.estoque = estoque; }
    public Categoria getCategoria() { return categoria; }
    public void setCategoria(Categoria categoria) { this.categoria = categoria; }
}
