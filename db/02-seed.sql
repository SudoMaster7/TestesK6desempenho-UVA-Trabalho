-- =====================================================================
-- Trabalho A2 - Seed determinístico com generate_series
--
-- Por que generate_series e nao um gerador em Java/Python?
--   1) Velocidade: 1M de item_pedido em segundos, tudo dentro do banco.
--   2) Reprodutibilidade: setseed() fixa o gerador pseudo-aleatorio, logo
--      QUALQUER maquina que rodar este script gera exatamente os mesmos dados
--      -> os experimentos sao comparaveis entre colegas/execucoes.
--
-- VOLUME PARAMETRIZAVEL: ajuste os valores no bloco abaixo se a maquina for
-- fraca. Mantenha a proporcao (pedido >> cliente) para o experimento de
-- indices continuar fazendo sentido.
-- =====================================================================

\set n_categoria   20
\set n_produto     2000
\set n_cliente     20000
\set n_pedido      300000
\set itens_por_pedido_max 6

-- setseed: tudo que vier de random() a partir daqui e deterministico.
SELECT setseed(0.42);

-- ---------------------------------------------------------------- categoria
INSERT INTO categoria (id, nome, descricao)
SELECT g,
       'Categoria ' || g,
       'Descricao da categoria ' || g
FROM generate_series(1, :n_categoria) g;

-- ---------------------------------------------------------------- produto
INSERT INTO produto (id, nome, sku, preco, estoque, categoria_id)
SELECT g,
       'Produto ' || g,
       'SKU-' || lpad(g::text, 6, '0'),
       round((random() * 990 + 10)::numeric, 2),
       (random() * 500)::int,
       ((g - 1) % :n_categoria) + 1
FROM generate_series(1, :n_produto) g;

-- ---------------------------------------------------------------- cliente
INSERT INTO cliente (id, nome, email, cidade, uf)
SELECT g,
       'Cliente ' || g,
       'cliente' || g || '@exemplo.com.br',
       (ARRAY['Rio de Janeiro','Sao Paulo','Belo Horizonte','Curitiba','Porto Alegre',
              'Salvador','Recife','Fortaleza','Brasilia','Manaus'])[((g - 1) % 10) + 1],
       (ARRAY['RJ','SP','MG','PR','RS','BA','PE','CE','DF','AM'])[((g - 1) % 10) + 1]
FROM generate_series(1, :n_cliente) g;

-- ---------------------------------------------------------------- pedido
-- cliente_id com random() (nao modulo) para a distribuicao ficar irregular,
-- como num sistema real: alguns clientes com muitos pedidos, outros com poucos.
-- data_pedido espalhada nos ultimos 2 anos -> habilita a consulta por intervalo.
-- ATENCAO: sempre floor() ao sortear indice de array/faixa inteira.
-- `::int` em Postgres ARREDONDA (4.6 -> 5), o que estoura o limite do ARRAY
-- e grava NULL; floor() trunca e mantem a faixa correta.
INSERT INTO pedido (id, cliente_id, data_pedido, status, valor_total)
SELECT g,
       floor(random() * :n_cliente)::bigint + 1,
       -- data espalhada deterministicamente em 2 anos (nao usa random):
       -- multiplicar o id por um primo embaralha as datas sem perder reprodutibilidade
       -- g::bigint e obrigatorio: g*7919 com g=300000 passa de 2,3 bilhoes e
       -- estouraria o int de 32 bits do Postgres ("integer out of range").
       timestamp '2024-01-01 00:00:00' + ((g::bigint * 7919) % 63072000) * interval '1 second',
       (ARRAY['NOVO','PAGO','ENVIADO','ENTREGUE','CANCELADO'])[floor(random() * 5)::int + 1],
       0
FROM generate_series(1, :n_pedido) g;

-- ---------------------------------------------------------------- item_pedido
-- 1 a 6 itens por pedido -> ~1.05M linhas com 300k pedidos.
-- ARMADILHA: `generate_series(1, floor(random()*6)::int+1)` numa LATERAL e
-- avaliado UMA vez pelo planner, gerando a MESMA quantidade para todo pedido.
-- Derivar a quantidade do id do pedido garante variacao real (1..6) e continua
-- deterministico.
INSERT INTO item_pedido (id, pedido_id, produto_id, quantidade, preco_unitario)
SELECT row_number() OVER (),
       p.id,
       floor(random() * :n_produto)::bigint + 1,
       floor(random() * 5)::int + 1,
       round((random() * 990 + 10)::numeric, 2)
FROM pedido p
CROSS JOIN LATERAL generate_series(1, ((p.id * 31) % :itens_por_pedido_max)::int + 1) i;

-- valor_total coerente com os itens (evita dado contraditorio no relatorio)
UPDATE pedido p
SET valor_total = sub.total
FROM (
    SELECT pedido_id, round(sum(quantidade * preco_unitario), 2) AS total
    FROM item_pedido
    GROUP BY pedido_id
) sub
WHERE p.id = sub.pedido_id;

-- ANALYZE obrigatorio: sem estatisticas atualizadas o planner do Postgres
-- escolhe planos ruins e o EXPLAIN do ITEM 2c nao representaria a realidade.
ANALYZE;

-- Volume de dados existente no banco (exigido pelo item 6.5 do enunciado)
SELECT 'categoria'   AS tabela, count(*) AS registros FROM categoria
UNION ALL SELECT 'produto',     count(*) FROM produto
UNION ALL SELECT 'cliente',     count(*) FROM cliente
UNION ALL SELECT 'pedido',      count(*) FROM pedido
UNION ALL SELECT 'item_pedido', count(*) FROM item_pedido;
