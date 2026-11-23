-- =====================================================================
-- Trabalho A2 - Schema do dominio "Sistema de Vendas"
-- 5 tabelas relacionadas: categoria -> produto, cliente -> pedido -> item_pedido
--
-- DECISAO DELIBERADA: NAO criamos indice em pedido(cliente_id) nem em
-- pedido(data_pedido). O PostgreSQL nao indexa chaves estrangeiras
-- automaticamente (ao contrario do MySQL/InnoDB), entao a tabela comeca
-- apenas com as PKs. Isso e o estado "antes" do experimento do ITEM 2c:
-- queremos observar Seq Scan + Sort e depois medir o ganho do indice.
-- =====================================================================

DROP TABLE IF EXISTS item_pedido CASCADE;
DROP TABLE IF EXISTS pedido CASCADE;
DROP TABLE IF EXISTS cliente CASCADE;
DROP TABLE IF EXISTS produto CASCADE;
DROP TABLE IF EXISTS categoria CASCADE;

CREATE TABLE categoria (
    id          BIGINT       PRIMARY KEY,
    nome        VARCHAR(80)  NOT NULL,
    descricao   VARCHAR(255)
);

CREATE TABLE produto (
    id           BIGINT        PRIMARY KEY,
    nome         VARCHAR(120)  NOT NULL,
    sku          VARCHAR(40)   NOT NULL,
    preco        NUMERIC(12,2) NOT NULL,
    estoque      INTEGER       NOT NULL,
    categoria_id BIGINT        NOT NULL REFERENCES categoria(id)
);

CREATE TABLE cliente (
    id      BIGINT       PRIMARY KEY,
    nome    VARCHAR(120) NOT NULL,
    email   VARCHAR(160) NOT NULL,
    cidade  VARCHAR(80)  NOT NULL,
    uf      CHAR(2)      NOT NULL
);

CREATE TABLE pedido (
    id          BIGINT        PRIMARY KEY,
    cliente_id  BIGINT        NOT NULL REFERENCES cliente(id),
    data_pedido TIMESTAMP     NOT NULL,
    status      VARCHAR(20)   NOT NULL,
    valor_total NUMERIC(12,2) NOT NULL
);

CREATE TABLE item_pedido (
    id            BIGINT        PRIMARY KEY,
    pedido_id     BIGINT        NOT NULL REFERENCES pedido(id),
    produto_id    BIGINT        NOT NULL REFERENCES produto(id),
    quantidade    INTEGER       NOT NULL,
    preco_unitario NUMERIC(12,2) NOT NULL
);

-- item_pedido(pedido_id) É indexado: sem ele TODA estrategia de persistencia
-- (lazy, eager, join fetch) viraria Seq Scan de 1M linhas e o experimento do
-- ITEM 2a mediria o acesso ao disco, nao a diferenca entre as estrategias.
CREATE INDEX idx_item_pedido_pedido ON item_pedido (pedido_id);
