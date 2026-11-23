package br.uva.aos.entity.lazy;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

/**
 * FASE 3 - conjunto LAZY.
 *
 * POR QUE DOIS CONJUNTOS DE ENTIDADES PARA AS MESMAS TABELAS?
 * No JPA o FetchType faz parte do MAPEAMENTO: uma mesma classe nao pode ser
 * LAZY num endpoint e EAGER noutro. Para comparar as duas estrategias no mesmo
 * banco, mapeamos as mesmas tabelas duas vezes, em pacotes separados.
 *
 * Ambos os conjuntos sao @Immutable (somente leitura): existem apenas para o
 * experimento, nunca para gravar. Isso tambem evita que o Hibernate faca dirty
 * checking dessas entidades, o que distorceria a medicao.
 */
@Entity
@Immutable
@Table(name = "cliente")
public class ClienteLazy {

    @Id
    private Long id;
    private String nome;
    private String email;
    private String cidade;
    private String uf;

    public Long getId() { return id; }
    public String getNome() { return nome; }
    public String getEmail() { return email; }
    public String getCidade() { return cidade; }
    public String getUf() { return uf; }
}
