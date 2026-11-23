package br.uva.aos.entity.batch;

import jakarta.persistence.*;
import org.hibernate.annotations.BatchSize;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;

@Entity
@Immutable
@BatchSize(size = 100)
@Table(name = "produto")
public class ProdutoBatch {

    @Id
    private Long id;
    private String nome;
    private String sku;
    private BigDecimal preco;

    public Long getId() { return id; }
    public String getNome() { return nome; }
    public String getSku() { return sku; }
    public BigDecimal getPreco() { return preco; }
}
