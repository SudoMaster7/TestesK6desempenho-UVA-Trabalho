-- ITEM 2c - Volta a tabela pedido ao estado inicial (somente PK).
DROP INDEX IF EXISTS idx_pedido_cliente_data;
DROP INDEX IF EXISTS idx_pedido_data_status;

ANALYZE pedido;

SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'pedido' ORDER BY indexname;
SELECT pg_size_pretty(pg_total_relation_size('pedido')) AS tamanho_total_pedido;
