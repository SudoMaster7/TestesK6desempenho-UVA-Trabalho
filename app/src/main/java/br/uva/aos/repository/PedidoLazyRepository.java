package br.uva.aos.repository;

import br.uva.aos.entity.lazy.PedidoLazy;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface PedidoLazyRepository extends JpaRepository<PedidoLazy, Long> {

    /**
     * Consulta propositalmente INGENUA: busca so os pedidos, sem tocar nos
     * relacionamentos. Quem provoca o N+1 e o codigo do service, ao percorrer
     * cliente e itens depois. Ordenado por id para que todas as estrategias
     * leiam exatamente as mesmas linhas (comparacao justa).
     */
    @Query("select p from PedidoLazy p order by p.id")
    List<PedidoLazy> buscarPagina(Pageable pageable);
}
