package br.uva.aos.repository;

import br.uva.aos.entity.Produto;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;

public interface ProdutoRepository extends JpaRepository<Produto, Long> {

    /**
     * JOIN FETCH explicito: garante UMA unica query para produto+categoria.
     * Sem ele, o findById + acesso a categoria poderia gerar 2 queries.
     */
    @Query("select p from Produto p join fetch p.categoria where p.id = :id")
    Produto buscarComCategoria(@Param("id") Long id);

    /**
     * UPDATE direto em JPQL (nao carrega a entidade): e a operacao de
     * atualizacao exigida pelo enunciado para demonstrar a invalidacao do cache.
     */
    @Modifying
    @Query("update Produto p set p.preco = :preco, p.estoque = :estoque where p.id = :id")
    int atualizarPrecoEstoque(@Param("id") Long id,
                              @Param("preco") BigDecimal preco,
                              @Param("estoque") Integer estoque);
}
