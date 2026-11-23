package br.uva.aos.dto;

import java.io.Serializable;

public record CategoriaDTO(Long id, String nome, String descricao) implements Serializable {
}
