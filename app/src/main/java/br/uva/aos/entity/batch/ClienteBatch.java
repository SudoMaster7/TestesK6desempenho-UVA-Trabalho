package br.uva.aos.entity.batch;

import jakarta.persistence.*;
import org.hibernate.annotations.BatchSize;
import org.hibernate.annotations.Immutable;

/**
 * FASE 4 - conjunto BATCH.
 *
 * @BatchSize no proprio @Entity faz o Hibernate agrupar a resolucao de varios
 * PROXIES do mesmo tipo numa unica query `where id in (?, ?, ...)`.
 */
@Entity
@Immutable
@BatchSize(size = 100)
@Table(name = "cliente")
public class ClienteBatch {

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
