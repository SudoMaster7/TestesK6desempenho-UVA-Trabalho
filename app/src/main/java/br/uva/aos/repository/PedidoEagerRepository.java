package br.uva.aos.repository;

import br.uva.aos.entity.eager.PedidoEager;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface PedidoEagerRepository extends JpaRepository<PedidoEager, Long> {

    /** Mesma consulta da versao lazy; a diferenca esta apenas no mapeamento. */
    @Query("select p from PedidoEager p order by p.id")
    List<PedidoEager> buscarPagina(Pageable pageable);
}
