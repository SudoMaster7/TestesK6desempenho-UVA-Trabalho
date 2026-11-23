package br.uva.aos.repository;

import br.uva.aos.dto.PedidoResumoDTO;
import br.uva.aos.entity.lazy.PedidoLazy;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * FASE 4 - Estrategias otimizadas, todas sobre o MESMO caso de uso
 * (listar pedidos com cliente e itens) e sobre as entidades LAZY.
 *
 * Trabalhar a partir do mapeamento LAZY e intencional: e assim que se corrige
 * o N+1 na pratica -- mantem-se o mapeamento sob demanda e resolve-se o
 * carregamento na CONSULTA, nao na anotacao.
 */
public interface PedidoOtimizadoRepository extends JpaRepository<PedidoLazy, Long> {

    /**
     * Etapa 1 do padrao de 2 passos para JOIN FETCH com paginacao.
     *
     * POR QUE DUAS ETAPAS? Com JOIN FETCH de COLECAO, uma linha de pedido vira
     * N linhas (uma por item). Se aplicassemos LIMIT direto, o banco cortaria
     * no meio dos itens e traria pedidos incompletos. O Hibernate percebe isso
     * e, para nao errar, traz TUDO para a memoria e pagina em Java
     * (HHH90003004: "firstResult/maxResults specified with collection fetch").
     * Buscando primeiro os IDs da pagina, o LIMIT e aplicado com seguranca.
     */
    @Query("select p.id from PedidoLazy p order by p.id")
    List<Long> buscarIdsPagina(Pageable pageable);

    /**
     * Etapa 2: UMA query traz pedido + cliente + itens + produto dos itens.
     * O `distinct` do JPQL remove as duplicatas de PEDIDO geradas pelo join
     * com a colecao (o Hibernate 6 ja desduplica em memoria, mas manter o
     * distinct deixa a intencao explicita no codigo).
     */
    @Query("""
           select distinct p from PedidoLazy p
             join fetch p.cliente
             left join fetch p.itens i
             left join fetch i.produto
           where p.id in :ids
           order by p.id
           """)
    List<PedidoLazy> buscarComJoinFetch(@Param("ids") List<Long> ids);

    /**
     * @EntityGraph: mesma ideia do JOIN FETCH, porem declarativa. O Hibernate
     * monta o plano de carregamento a partir do grafo de atributos informado,
     * sem precisar escrever o JOIN na JPQL.
     */
    @EntityGraph(attributePaths = {"cliente", "itens", "itens.produto"})
    @Query("select p from PedidoLazy p where p.id in :ids order by p.id")
    List<PedidoLazy> buscarComEntityGraph(@Param("ids") List<Long> ids);

    /**
     * Sem fetch: usado pelo endpoint /batch, onde o carregamento dos
     * relacionamentos e resolvido pelo @BatchSize (ver EntidadeBatchConfig na
     * documentacao do README) -- o Hibernate agrupa os acessos em
     * `where pedido_id in (?, ?, ...)` em vez de uma query por pedido.
     */
    @Query("select p from PedidoLazy p where p.id in :ids order by p.id")
    List<PedidoLazy> buscarSemFetch(@Param("ids") List<Long> ids);

    /**
     * FASE 5 - consulta-alvo do experimento de indices.
     * Filtro de igualdade + ordenacao descendente: o caso classico em que um
     * indice composto (cliente_id, data_pedido DESC) elimina Seq Scan E Sort.
     */
    @Query("""
           select new br.uva.aos.dto.PedidoResumoDTO(p.id, p.dataPedido, p.status, p.valorTotal, p.cliente.id)
           from PedidoLazy p
           where p.cliente.id = :clienteId
           order by p.dataPedido desc
           """)
    List<PedidoResumoDTO> buscarPorCliente(@Param("clienteId") Long clienteId, Pageable pageable);

    /** FASE 5 - segunda consulta-alvo: intervalo de datas + status. */
    @Query("""
           select new br.uva.aos.dto.PedidoResumoDTO(p.id, p.dataPedido, p.status, p.valorTotal, p.cliente.id)
           from PedidoLazy p
           where p.dataPedido between :inicio and :fim and p.status = :status
           order by p.dataPedido desc
           """)
    List<PedidoResumoDTO> buscarPorPeriodo(@Param("inicio") LocalDateTime inicio,
                                           @Param("fim") LocalDateTime fim,
                                           @Param("status") String status,
                                           Pageable pageable);
}
