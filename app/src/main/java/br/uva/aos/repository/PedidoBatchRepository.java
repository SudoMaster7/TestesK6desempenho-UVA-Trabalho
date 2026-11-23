package br.uva.aos.repository;

import br.uva.aos.entity.batch.PedidoBatch;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface PedidoBatchRepository extends JpaRepository<PedidoBatch, Long> {

    @Query("select p from PedidoBatch p order by p.id")
    List<PedidoBatch> buscarPagina(Pageable pageable);
}
