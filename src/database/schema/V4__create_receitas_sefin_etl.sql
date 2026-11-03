-- =============================================================================
-- SPRINT E2 — MIGRAÇÃO ADITIVA: receitas orçamentárias da API sgreceitas
-- Compatível com schema tributario da Sprint 2 (PostgreSQL).
-- IMPORTANTE: esta tabela NÃO representa devedores nem débitos de IPTU/ISS.
-- Execute apenas após V1__create_schema.sql e com autorização da equipe do banco.
-- =============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS tributario.receitas_sefin_etl (
    chave_registro         VARCHAR(64) PRIMARY KEY,
    hash_conteudo          VARCHAR(64) NOT NULL,
    orgao                  VARCHAR(50) NOT NULL,
    orgao_nome             VARCHAR(255),
    unidade_id             VARCHAR(70),
    unidade_nome           VARCHAR(255),
    codigo                 VARCHAR(120) NOT NULL,
    codigo_original        VARCHAR(120),
    ano                    INTEGER NOT NULL CHECK (ano BETWEEN 1900 AND 2100),
    mes                    INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    descricao              TEXT NOT NULL,
    valor_orcado           NUMERIC(20,2),
    valor_arrecado_mes     NUMERIC(20,2),
    valor_arrecado_periodo NUMERIC(20,2),
    covid                  VARCHAR(20),
    origem_arquivo         VARCHAR(255) NOT NULL,
    processado_em          TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_receitas_sefin_periodo
    ON tributario.receitas_sefin_etl (ano, mes);
CREATE INDEX IF NOT EXISTS idx_receitas_sefin_orgao
    ON tributario.receitas_sefin_etl (orgao);

COMMENT ON TABLE tributario.receitas_sefin_etl IS
    'Área de integração da API pública de receitas orçamentárias do NUCLEOGOV. Não contém dívidas pessoais de IPTU/ISS.';
COMMIT;
