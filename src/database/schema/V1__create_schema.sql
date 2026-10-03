-- =============================================================================
-- SISTEMA TRIBUTÁRIO - CONTROLE DE INADIMPLÊNCIA (IPTU / ISS)
-- Script: V1__create_schema.sql
-- Versão: 1.0
-- Banco:  PostgreSQL 14+
-- Autor:  Gerado automaticamente a partir do DER (Jacinto)
-- Data:   2026-09-25
-- Normalização: 3FN
-- =============================================================================

-- Habilita extensão para UUID (caso queira usar gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- SCHEMA DEDICADO
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS tributario;

SET search_path TO tributario, public;

-- =============================================================================
-- 1. CONTRIBUINTE
--    Pessoa física ou jurídica responsável pelo pagamento dos tributos.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.contribuinte (
    cpf_cnpj          VARCHAR(18)  NOT NULL,
    nome              VARCHAR(150) NOT NULL,
    is_iptu_social    BOOLEAN      NOT NULL DEFAULT FALSE,  -- isenção social IPTU
    contato           VARCHAR(100),                         -- e-mail ou telefone

    CONSTRAINT pk_contribuinte PRIMARY KEY (cpf_cnpj),
    CONSTRAINT chk_cpf_cnpj_formato CHECK (
        cpf_cnpj ~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$'   -- CPF
        OR cpf_cnpj ~ '^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$' -- CNPJ
    )
);

COMMENT ON TABLE  tributario.contribuinte IS 'Cadastro de contribuintes (PF e PJ) do município.';
COMMENT ON COLUMN tributario.contribuinte.is_iptu_social IS 'TRUE quando o contribuinte tem isenção/redução social de IPTU.';

-- =============================================================================
-- 2. ANALISTA_FISCAL
--    Servidores que acessam e analisam os dados de inadimplência.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.analista_fiscal (
    id_analista  VARCHAR(36)  NOT NULL DEFAULT gen_random_uuid()::TEXT,
    nome         VARCHAR(150) NOT NULL,
    perfil       VARCHAR(50)  NOT NULL,  -- ex.: 'ADMINISTRADOR', 'AUDITOR', 'CONSULTOR'

    CONSTRAINT pk_analista_fiscal PRIMARY KEY (id_analista),
    CONSTRAINT chk_perfil CHECK (perfil IN ('ADMINISTRADOR', 'AUDITOR', 'CONSULTOR'))
);

COMMENT ON TABLE tributario.analista_fiscal IS 'Analistas fiscais com acesso ao sistema de controle de inadimplência.';

-- =============================================================================
-- 3. LOG_AUDITORIA
--    Registra cada acesso/ação realizado por um analista (LGPD).
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.log_auditoria (
    id_log              VARCHAR(36)  NOT NULL DEFAULT gen_random_uuid()::TEXT,
    id_analista         VARCHAR(36)  NOT NULL,
    timestamp_acesso    TIMESTAMP    NOT NULL DEFAULT NOW(),
    filtros_aplicados   TEXT,         -- JSON ou texto livre dos filtros usados
    justificativa_lgpd  TEXT NOT NULL, -- obrigatório por LGPD

    CONSTRAINT pk_log_auditoria    PRIMARY KEY (id_log),
    CONSTRAINT fk_log_analista     FOREIGN KEY (id_analista)
        REFERENCES tributario.analista_fiscal (id_analista)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

COMMENT ON TABLE  tributario.log_auditoria IS 'Trilha de auditoria de acessos dos analistas fiscais (conformidade LGPD).';
COMMENT ON COLUMN tributario.log_auditoria.justificativa_lgpd IS 'Justificativa obrigatória para acesso a dados pessoais (LGPD Art. 37).';

-- =============================================================================
-- 4. IMOVEL
--    Imóvel urbano sujeito ao IPTU, vinculado a um contribuinte.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.imovel (
    inscricao_imobiliaria   VARCHAR(20)  NOT NULL,
    cpf_cnpj_proprietario   VARCHAR(18)  NOT NULL,
    logradouro              VARCHAR(200) NOT NULL,
    bairro                  VARCHAR(100) NOT NULL,
    area_edificada          NUMERIC(10,2) NOT NULL CHECK (area_edificada > 0),
    setor_urbano            VARCHAR(20)  NOT NULL,

    CONSTRAINT pk_imovel            PRIMARY KEY (inscricao_imobiliaria),
    CONSTRAINT fk_imovel_contribuinte FOREIGN KEY (cpf_cnpj_proprietario)
        REFERENCES tributario.contribuinte (cpf_cnpj)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

COMMENT ON TABLE  tributario.imovel IS 'Cadastro imobiliário urbano para fins de lançamento de IPTU.';
COMMENT ON COLUMN tributario.imovel.inscricao_imobiliaria IS 'Chave de inscrição cadastral do imóvel no município.';
COMMENT ON COLUMN tributario.imovel.setor_urbano IS 'Código do setor/zona urbana para cálculo da alíquota IPTU.';

-- =============================================================================
-- 5. DEBITO_TRIBUTARIO
--    Lançamento de débito de IPTU ou ISS vinculado ao imóvel/contribuinte.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.debito_tributario (
    id_debito             VARCHAR(36)  NOT NULL DEFAULT gen_random_uuid()::TEXT,
    inscricao_imobiliaria VARCHAR(20),  -- NULL quando débito for de ISS (sem imóvel)
    cpf_cnpj              VARCHAR(18)  NOT NULL,
    tipo_tributo          VARCHAR(4)   NOT NULL,
    valor_debito          NUMERIC(15,2) NOT NULL CHECK (valor_debito > 0),
    data_vencimento       DATE         NOT NULL,
    status_pagamento      VARCHAR(20)  NOT NULL DEFAULT 'PENDENTE',

    CONSTRAINT pk_debito_tributario  PRIMARY KEY (id_debito),
    CONSTRAINT fk_debito_imovel      FOREIGN KEY (inscricao_imobiliaria)
        REFERENCES tributario.imovel (inscricao_imobiliaria)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_debito_contribuinte FOREIGN KEY (cpf_cnpj)
        REFERENCES tributario.contribuinte (cpf_cnpj)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_tipo_tributo      CHECK (tipo_tributo IN ('IPTU', 'ISS')),
    CONSTRAINT chk_status_pagamento  CHECK (status_pagamento IN (
        'PENDENTE', 'PAGO', 'VENCIDO', 'PARCELADO', 'CANCELADO'
    )),
    -- ISS não exige imóvel; IPTU obrigatoriamente possui inscrição imobiliária
    CONSTRAINT chk_iptu_requer_imovel CHECK (
        tipo_tributo <> 'IPTU' OR inscricao_imobiliaria IS NOT NULL
    )
);

COMMENT ON TABLE  tributario.debito_tributario IS 'Débitos tributários lançados por contribuinte (IPTU e ISS).';
COMMENT ON COLUMN tributario.debito_tributario.status_pagamento IS 'PENDENTE | PAGO | VENCIDO | PARCELADO | CANCELADO';

-- =============================================================================
-- 6. MODELO_PREDICAO
--    Metadados dos modelos de ML usados para prever inadimplência.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.modelo_predicao (
    id_modelo         VARCHAR(36)  NOT NULL DEFAULT gen_random_uuid()::TEXT,
    versao            VARCHAR(50)  NOT NULL,
    acuracia          NUMERIC(5,4) NOT NULL CHECK (acuracia BETWEEN 0 AND 1),
    data_treinamento  DATE         NOT NULL,

    CONSTRAINT pk_modelo_predicao PRIMARY KEY (id_modelo),
    CONSTRAINT uq_modelo_versao   UNIQUE (versao)
);

COMMENT ON TABLE  tributario.modelo_predicao IS 'Registro de versões dos modelos preditivos de inadimplência.';
COMMENT ON COLUMN tributario.modelo_predicao.acuracia IS 'Acurácia do modelo no conjunto de teste (0.0 a 1.0).';

-- =============================================================================
-- 7. SCORE_RECUPERABILIDADE
--    Score gerado pelo modelo para cada débito, indicando chance de pagamento.
-- =============================================================================
CREATE TABLE IF NOT EXISTS tributario.score_recuperabilidade (
    id_score            VARCHAR(36)  NOT NULL DEFAULT gen_random_uuid()::TEXT,
    id_debito           VARCHAR(36)  NOT NULL,
    id_modelo           VARCHAR(36)  NOT NULL,
    score_valor         NUMERIC(5,4) NOT NULL CHECK (score_valor BETWEEN 0 AND 1),
    nivel_inadimplencia VARCHAR(20)  NOT NULL,
    data_calculo        DATE         NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT pk_score_recuperabilidade PRIMARY KEY (id_score),
    CONSTRAINT fk_score_debito   FOREIGN KEY (id_debito)
        REFERENCES tributario.debito_tributario (id_debito)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_score_modelo   FOREIGN KEY (id_modelo)
        REFERENCES tributario.modelo_predicao (id_modelo)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_nivel_inadimplencia CHECK (nivel_inadimplencia IN (
        'BAIXO', 'MEDIO', 'ALTO', 'CRITICO'
    )),
    -- Garante que cada par (débito + modelo) seja único
    CONSTRAINT uq_score_debito_modelo UNIQUE (id_debito, id_modelo)
);

COMMENT ON TABLE  tributario.score_recuperabilidade IS 'Score de recuperabilidade do débito gerado pelos modelos preditivos.';
COMMENT ON COLUMN tributario.score_recuperabilidade.nivel_inadimplencia IS 'Classificação: BAIXO | MEDIO | ALTO | CRITICO';
COMMENT ON COLUMN tributario.score_recuperabilidade.score_valor IS 'Probabilidade de pagamento (0 = certeza de inadimplência, 1 = certeza de pagamento).';

-- =============================================================================
-- ÍNDICES DE DESEMPENHO
-- =============================================================================

-- Buscas frequentes por CPF/CNPJ
CREATE INDEX IF NOT EXISTS idx_imovel_proprietario   ON tributario.imovel (cpf_cnpj_proprietario);
CREATE INDEX IF NOT EXISTS idx_debito_contribuinte    ON tributario.debito_tributario (cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_debito_status          ON tributario.debito_tributario (status_pagamento);
CREATE INDEX IF NOT EXISTS idx_debito_tipo_vencimento ON tributario.debito_tributario (tipo_tributo, data_vencimento);
CREATE INDEX IF NOT EXISTS idx_score_nivel            ON tributario.score_recuperabilidade (nivel_inadimplencia);
CREATE INDEX IF NOT EXISTS idx_log_analista           ON tributario.log_auditoria (id_analista, timestamp_acesso);

-- =============================================================================
-- FIM DO SCHEMA
-- =============================================================================
