package br.uva.aos.entity;

import jakarta.persistence.*;

/**
 * Categoria - entidade de BAIXA volatilidade (muda raramente).
 * E exatamente o perfil ideal para cache com TTL longo (ITEM 1, criterio 3.1).
 */
@Entity
@Table(name = "categoria")
public class Categoria {

    @Id
    private Long id;

    private String nome;
    private String descricao;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getNome() { return nome; }
    public void setNome(String nome) { this.nome = nome; }
    public String getDescricao() { return descricao; }
    public void setDescricao(String descricao) { this.descricao = descricao; }
}
