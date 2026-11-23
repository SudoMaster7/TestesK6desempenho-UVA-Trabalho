package br.uva.aos.repository;

import br.uva.aos.entity.lazy.PedidoLazy;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Map;

/**
 * FASE 4 - projecao direta (sem entidades gerenciadas) e SQL nativo.
 */
public interface PedidoProjecaoRepository extends JpaRepository<PedidoLazy, Long> {

    /**
     * PROJECAO JPQL "flat": uma unica query com join, devolvendo colunas soltas.
     *
     * Vantagem sobre carregar entidades: o Hibernate nao cria objetos
     * gerenciados nem guarda nada no contexto de persistencia (sem snapshot
     * para dirty checking), o que reduz CPU e memoria por requisicao.
     * O agrupamento pedido -> itens e feito em Java (ver PedidoService).
     */
    @Query("""
           select p.id, p.dataPedido, p.status, p.valorTotal,
                  c.id, c.nome, c.cidade,
                  i.id, pr.id, pr.nome, i.quantidade, i.precoUnitario
           from PedidoLazy p
             join p.cliente c
             left join p.itens i
             left join i.produto pr
           where p.id in :ids
           order by p.id, i.id
           """)
    List<Object[]> buscarProjecao(@Param("ids") List<Long> ids);

    /**
     * SQL NATIVO com json_agg do PostgreSQL: o banco monta o array de itens e
     * devolve UMA linha por pedido, eliminando o trafego das linhas repetidas
     * do join.
     *
     * CUSTO DESSA ESCOLHA (discutido no README, secao 4.4):
     *   - amarra a aplicacao ao PostgreSQL (json_agg nao existe no MySQL/Oracle);
     *   - nao ha verificacao em tempo de compilacao: erro de coluna so aparece
     *     em producao, na execucao;
     *   - renomear uma coluna deixa de ser refatoracao automatica.
     */
    @Query(value = """
           select p.id              as id,
                  p.data_pedido     as data_pedido,
                  p.status          as status,
                  p.valor_total     as valor_total,
                  c.id              as cliente_id,
                  c.nome            as cliente_nome,
                  c.cidade          as cliente_cidade,
                  coalesce(json_agg(
                      json_build_object(
                          'id', i.id,
                          'produtoId', pr.id,
                          'produtoNome', pr.nome,
                          'quantidade', i.quantidade,
                          'precoUnitario', i.preco_unitario)
                      order by i.id
                  ) filter (where i.id is not null), '[]') as itens
           from pedido p
             join cliente c on c.id = p.cliente_id
             left join item_pedido i on i.pedido_id = p.id
             left join produto pr on pr.id = i.produto_id
           where p.id = any(:ids)
           group by p.id, c.id
           order by p.id
           """, nativeQuery = true)
    List<Map<String, Object>> buscarNativo(@Param("ids") Long[] ids);
}
