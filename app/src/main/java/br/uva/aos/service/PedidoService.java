package br.uva.aos.service;

import br.uva.aos.dto.PedidoDTO;
import br.uva.aos.dto.PedidoResumoDTO;
import br.uva.aos.repository.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * FASES 3, 4 e 5 - todas as estrategias de recuperacao de pedidos.
 *
 * Todos os metodos devolvem o MESMO PedidoDTO e leem as MESMAS linhas
 * (ordenadas por id, com o mesmo `limite`). A unica variavel do experimento e
 * COMO os dados sao buscados -- e isso e o que o X-Query-Count mede.
 */
@Service
public class PedidoService {

    private final PedidoLazyRepository lazyRepository;
    private final PedidoEagerRepository eagerRepository;
    private final PedidoBatchRepository batchRepository;
    private final PedidoOtimizadoRepository otimizadoRepository;
    private final PedidoProjecaoRepository projecaoRepository;
    private final ObjectMapper objectMapper;

    public PedidoService(PedidoLazyRepository lazyRepository,
                         PedidoEagerRepository eagerRepository,
                         PedidoBatchRepository batchRepository,
                         PedidoOtimizadoRepository otimizadoRepository,
                         PedidoProjecaoRepository projecaoRepository,
                         ObjectMapper objectMapper) {
        this.lazyRepository = lazyRepository;
        this.eagerRepository = eagerRepository;
        this.batchRepository = batchRepository;
        this.otimizadoRepository = otimizadoRepository;
        this.projecaoRepository = projecaoRepository;
        this.objectMapper = objectMapper;
    }

    private static Pageable pagina(int limite) {
        return PageRequest.of(0, limite);
    }

    // =================================================================
    // FASE 3 - ITEM 2a: LAZY vs EAGER
    // =================================================================

    /**
     * LAZY COM ACESSO -> provoca o N+1.
     *
     * A 1a query traz os pedidos. Depois, para cada pedido, o acesso a
     * getCliente().getNome() e a getItens() forca o Hibernate a disparar SQL
     * adicional. Resultado esperado: X-Query-Count cresce proporcionalmente ao
     * limite (ordem de 2N+1).
     */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarLazy(int limite) {
        var pedidos = lazyRepository.buscarPagina(pagina(limite));
        List<PedidoDTO> out = new ArrayList<>(pedidos.size());
        for (var p : pedidos) {
            List<PedidoDTO.ItemDTO> itens = new ArrayList<>();
            // Este for e o gatilho do N+1: cada iteracao inicializa a colecao
            // e, dentro dela, cada item resolve o proxy do produto.
            for (var i : p.getItens()) {
                itens.add(new PedidoDTO.ItemDTO(i.getId(),
                        i.getProduto().getId(), i.getProduto().getNome(),
                        i.getQuantidade(), i.getPrecoUnitario()));
            }
            out.add(new PedidoDTO(p.getId(), p.getDataPedido(), p.getStatus(), p.getValorTotal(),
                    p.getCliente().getId(), p.getCliente().getNome(), p.getCliente().getCidade(),
                    itens));
        }
        return out;
    }

    /**
     * LAZY SEM ACESSO -> mostra a VANTAGEM do LAZY.
     * Nenhum relacionamento e tocado, portanto nenhuma query extra e emitida:
     * X-Query-Count fica em 1 independentemente do limite.
     */
    @Transactional(readOnly = true)
    public List<PedidoResumoDTO> listarLazySemAcesso(int limite) {
        return lazyRepository.buscarPagina(pagina(limite)).stream()
                .map(p -> new PedidoResumoDTO(p.getId(), p.getDataPedido(), p.getStatus(),
                        p.getValorTotal(), null)) // cliente nao e acessado de proposito
                .toList();
    }

    /**
     * EAGER -> o custo e pago sempre, no momento da consulta.
     * Observar no X-Query-Count se o Hibernate resolveu em 1 query ou se
     * tambem gerou N+1 (comportamento tipico de colecao EAGER em consulta
     * derivada/JPQL sem fetch explicito).
     */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarEager(int limite) {
        var pedidos = eagerRepository.buscarPagina(pagina(limite));
        List<PedidoDTO> out = new ArrayList<>(pedidos.size());
        for (var p : pedidos) {
            List<PedidoDTO.ItemDTO> itens = new ArrayList<>();
            for (var i : p.getItens()) {
                itens.add(new PedidoDTO.ItemDTO(i.getId(),
                        i.getProduto().getId(), i.getProduto().getNome(),
                        i.getQuantidade(), i.getPrecoUnitario()));
            }
            out.add(new PedidoDTO(p.getId(), p.getDataPedido(), p.getStatus(), p.getValorTotal(),
                    p.getCliente().getId(), p.getCliente().getNome(), p.getCliente().getCidade(),
                    itens));
        }
        return out;
    }

    // =================================================================
    // FASE 4 - ITEM 2b: estrategias otimizadas
    // =================================================================

    /** JOIN FETCH em 2 etapas (IDs paginados -> fetch por IDs). */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarJoinFetch(int limite) {
        List<Long> ids = otimizadoRepository.buscarIdsPagina(pagina(limite));
        return mapearLazy(otimizadoRepository.buscarComJoinFetch(ids));
    }

    /** @EntityGraph: mesmo efeito do JOIN FETCH, declarado por atributos. */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarEntityGraph(int limite) {
        List<Long> ids = otimizadoRepository.buscarIdsPagina(pagina(limite));
        return mapearLazy(otimizadoRepository.buscarComEntityGraph(ids));
    }

    /** @BatchSize: 1 + ceil(N/100) queries em vez de 1 + 2N. */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarBatch(int limite) {
        var pedidos = batchRepository.buscarPagina(pagina(limite));
        List<PedidoDTO> out = new ArrayList<>(pedidos.size());
        for (var p : pedidos) {
            List<PedidoDTO.ItemDTO> itens = new ArrayList<>();
            for (var i : p.getItens()) {
                itens.add(new PedidoDTO.ItemDTO(i.getId(),
                        i.getProduto().getId(), i.getProduto().getNome(),
                        i.getQuantidade(), i.getPrecoUnitario()));
            }
            out.add(new PedidoDTO(p.getId(), p.getDataPedido(), p.getStatus(), p.getValorTotal(),
                    p.getCliente().getId(), p.getCliente().getNome(), p.getCliente().getCidade(),
                    itens));
        }
        return out;
    }

    /** Projecao JPQL direta em colunas, agrupada em Java. */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarProjecaoDTO(int limite) {
        List<Long> ids = otimizadoRepository.buscarIdsPagina(pagina(limite));
        List<Object[]> linhas = projecaoRepository.buscarProjecao(ids);

        // LinkedHashMap preserva a ordem de id vinda do ORDER BY
        Map<Long, PedidoDTO> acumulado = new LinkedHashMap<>();
        Map<Long, List<PedidoDTO.ItemDTO>> itensPorPedido = new LinkedHashMap<>();

        for (Object[] l : linhas) {
            Long pedidoId = (Long) l[0];
            itensPorPedido.computeIfAbsent(pedidoId, k -> new ArrayList<>());
            if (l[7] != null) { // item pode ser null por causa do left join
                itensPorPedido.get(pedidoId).add(new PedidoDTO.ItemDTO(
                        (Long) l[7], (Long) l[8], (String) l[9],
                        (Integer) l[10], (BigDecimal) l[11]));
            }
            acumulado.putIfAbsent(pedidoId, new PedidoDTO(
                    pedidoId, (LocalDateTime) l[1], (String) l[2], (BigDecimal) l[3],
                    (Long) l[4], (String) l[5], (String) l[6], null));
        }

        List<PedidoDTO> out = new ArrayList<>(acumulado.size());
        acumulado.forEach((id, dto) -> out.add(new PedidoDTO(dto.id(), dto.dataPedido(),
                dto.status(), dto.valorTotal(), dto.clienteId(), dto.clienteNome(),
                dto.clienteCidade(), itensPorPedido.get(id))));
        return out;
    }

    /** SQL nativo com json_agg: 1 linha por pedido, itens montados pelo banco. */
    @Transactional(readOnly = true)
    public List<PedidoDTO> listarNativo(int limite) {
        List<Long> ids = otimizadoRepository.buscarIdsPagina(pagina(limite));
        List<Map<String, Object>> linhas = projecaoRepository.buscarNativo(ids.toArray(new Long[0]));

        List<PedidoDTO> out = new ArrayList<>(linhas.size());
        for (Map<String, Object> l : linhas) {
            List<PedidoDTO.ItemDTO> itens;
            try {
                // O driver devolve o json_agg como String (tipo json do Postgres)
                itens = objectMapper.readValue(String.valueOf(l.get("itens")),
                        objectMapper.getTypeFactory()
                                .constructCollectionType(List.class, PedidoDTO.ItemDTO.class));
            } catch (Exception e) {
                throw new IllegalStateException("Falha ao desserializar os itens do json_agg", e);
            }
            out.add(new PedidoDTO(
                    ((Number) l.get("id")).longValue(),
                    ((Timestamp) l.get("data_pedido")).toLocalDateTime(),
                    (String) l.get("status"),
                    (BigDecimal) l.get("valor_total"),
                    ((Number) l.get("cliente_id")).longValue(),
                    (String) l.get("cliente_nome"),
                    (String) l.get("cliente_cidade"),
                    itens));
        }
        return out;
    }

    // =================================================================
    // FASE 5 - ITEM 2c: consultas-alvo do experimento de indices
    // =================================================================

    @Transactional(readOnly = true)
    public List<PedidoResumoDTO> pedidosPorCliente(Long clienteId, int limite) {
        return otimizadoRepository.buscarPorCliente(clienteId, pagina(limite));
    }

    @Transactional(readOnly = true)
    public List<PedidoResumoDTO> pedidosPorPeriodo(LocalDateTime inicio, LocalDateTime fim,
                                                   String status, int limite) {
        return otimizadoRepository.buscarPorPeriodo(inicio, fim, status, pagina(limite));
    }

    // ---------------------------------------------------------------- apoio
    private List<PedidoDTO> mapearLazy(List<br.uva.aos.entity.lazy.PedidoLazy> pedidos) {
        List<PedidoDTO> out = new ArrayList<>(pedidos.size());
        for (var p : pedidos) {
            List<PedidoDTO.ItemDTO> itens = new ArrayList<>();
            for (var i : p.getItens()) {
                itens.add(new PedidoDTO.ItemDTO(i.getId(),
                        i.getProduto().getId(), i.getProduto().getNome(),
                        i.getQuantidade(), i.getPrecoUnitario()));
            }
            out.add(new PedidoDTO(p.getId(), p.getDataPedido(), p.getStatus(), p.getValorTotal(),
                    p.getCliente().getId(), p.getCliente().getNome(), p.getCliente().getCidade(),
                    itens));
        }
        return out;
    }
}
