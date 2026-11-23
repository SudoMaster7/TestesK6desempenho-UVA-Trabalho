-- ITEM 2c - Cria os indices do experimento e atualiza estatisticas.
-- Rodar DEPOIS de medir o estado "sem indice".

-- Consulta-alvo 1: SELECT * FROM pedido WHERE cliente_id = ? ORDER BY data_pedido DESC LIMIT 50
-- Indice COMPOSTO: a 1a coluna resolve o filtro de igualdade, a 2a (DESC) ja
-- entrega as linhas na ordem pedida -> o no "Sort" desaparece do plano.
CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data
    ON pedido (cliente_id, data_pedido DESC);

-- Consulta-alvo 2: WHERE data_pedido BETWEEN ? AND ? AND status = ?
-- Ordem (data_pedido, status): a coluna do intervalo vem primeiro porque e ela
-- que define o trecho do indice a ser varrido; status filtra dentro desse trecho.
CREATE INDEX IF NOT EXISTS idx_pedido_data_status
    ON pedido (data_pedido, status);

ANALYZE pedido;

SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'pedido' ORDER BY indexname;
SELECT pg_size_pretty(pg_total_relation_size('pedido')) AS tamanho_total_pedido;
