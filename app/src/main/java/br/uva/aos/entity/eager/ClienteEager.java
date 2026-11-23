package br.uva.aos.entity.eager;

import jakarta.persistence.*;
import org.hibernate.annotations.Immutable;

@Entity
@Immutable
@Table(name = "cliente")
public class ClienteEager {

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
