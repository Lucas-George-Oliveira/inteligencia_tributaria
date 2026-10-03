-- =============================================================================
-- SISTEMA TRIBUTÁRIO - DADOS PILOTO (SEED)
-- Script: V2__seed_dados_piloto.sql
-- Versão: 1.0
-- Descrição: Insere conjunto mínimo de dados reais de piloto para validação
--            do schema e das regras de negócio.
-- =============================================================================

SET search_path TO tributario, public;

-- =============================================================================
-- 1. CONTRIBUINTES (mix de PF e PJ, com e sem isenção IPTU Social)
-- =============================================================================
INSERT INTO tributario.contribuinte (cpf_cnpj, nome, is_iptu_social, contato) VALUES
    ('123.456.789-09', 'Maria da Silva Santos',        TRUE,  'maria.santos@email.com'),
    ('987.654.321-00', 'João Carlos Pereira',          FALSE, '(11) 98765-4321'),
    ('456.789.123-87', 'Ana Paula Rodrigues',          FALSE, 'anapaula@gmail.com'),
    ('321.654.987-12', 'Carlos Eduardo Mendes',        TRUE,  '(11) 91234-5678'),
    ('654.321.098-55', 'Fernanda Lima Costa',          FALSE, 'fernanda.lima@empresa.com'),
    ('11.222.333/0001-44', 'Comércio Rápido Ltda',    FALSE, 'fiscal@comerciorapido.com.br'),
    ('55.666.777/0001-88', 'Serviços Tech ME',        FALSE, 'contato@servicostech.com.br'),
    ('99.888.777/0001-11', 'Construtora Urbana S/A',  FALSE, 'financeiro@construtoraurbana.com')
ON CONFLICT (cpf_cnpj) DO NOTHING;

-- =============================================================================
-- 2. ANALISTAS FISCAIS
-- =============================================================================
INSERT INTO tributario.analista_fiscal (id_analista, nome, perfil) VALUES
    ('analista-001', 'Roberto Alves Martins',  'ADMINISTRADOR'),
    ('analista-002', 'Silvia Torres Campos',   'AUDITOR'),
    ('analista-003', 'Marcos Vinícius Souza',  'CONSULTOR'),
    ('analista-004', 'Patrícia Neves Lima',    'AUDITOR')
ON CONFLICT (id_analista) DO NOTHING;

-- =============================================================================
-- 3. IMÓVEIS (vinculados aos contribuintes PF/PJ)
-- =============================================================================
INSERT INTO tributario.imovel
    (inscricao_imobiliaria, cpf_cnpj_proprietario, logradouro, bairro, area_edificada, setor_urbano)
VALUES
    ('0001-0001-001', '123.456.789-09', 'Rua das Flores, 123',         'Centro',        85.50,  'SU-01'),
    ('0001-0001-002', '987.654.321-00', 'Av. Brasil, 456, Ap. 32',     'Jardim América', 120.00, 'SU-02'),
    ('0001-0001-003', '456.789.123-87', 'Rua Palmeiras, 789',          'Vila Nova',      60.75,  'SU-01'),
    ('0001-0001-004', '321.654.987-12', 'Travessa das Acácias, 10',    'Bela Vista',     45.00,  'SU-03'),
    ('0001-0001-005', '654.321.098-55', 'Alameda Santos, 2000, Ap. 5', 'Jardins',        200.00, 'SU-02'),
    ('0002-0001-001', '11.222.333/0001-44', 'Av. Paulista, 1500, Lj. 3', 'Bela Vista',  350.00, 'SU-02'),
    ('0002-0001-002', '99.888.777/0001-11', 'Rua Industrial, 500',     'Distrito Ind.',  800.00, 'SU-04')
ON CONFLICT (inscricao_imobiliaria) DO NOTHING;

-- =============================================================================
-- 4. DÉBITOS TRIBUTÁRIOS (IPTU e ISS, vários status)
-- =============================================================================
INSERT INTO tributario.debito_tributario
    (id_debito, inscricao_imobiliaria, cpf_cnpj, tipo_tributo, valor_debito, data_vencimento, status_pagamento)
VALUES
    -- IPTU - imóvel residencial Maria (pago)
    ('deb-001', '0001-0001-001', '123.456.789-09', 'IPTU', 850.00,  '2026-02-28', 'PAGO'),
    -- IPTU - imóvel João (vencido - inadimplente)
    ('deb-002', '0001-0001-002', '987.654.321-00', 'IPTU', 1200.00, '2026-03-31', 'VENCIDO'),
    -- IPTU - imóvel Ana (pendente)
    ('deb-003', '0001-0001-003', '456.789.123-87', 'IPTU', 600.00,  '2026-06-30', 'PENDENTE'),
    -- IPTU - imóvel Carlos (isenção social, valor reduzido, pago)
    ('deb-004', '0001-0001-004', '321.654.987-12', 'IPTU', 120.00,  '2026-02-28', 'PAGO'),
    -- IPTU - imóvel Fernanda (parcelado)
    ('deb-005', '0001-0001-005', '654.321.098-55', 'IPTU', 3500.00, '2026-03-31', 'PARCELADO'),
    -- IPTU - imóvel Comércio Rápido (vencido)
    ('deb-006', '0002-0001-001', '11.222.333/0001-44', 'IPTU', 8700.00, '2026-01-31', 'VENCIDO'),
    -- IPTU - imóvel Construtora (vencido - alto valor)
    ('deb-007', '0002-0001-002', '99.888.777/0001-11', 'IPTU', 22000.00,'2025-12-31', 'VENCIDO'),
    -- ISS - Serviços Tech (pendente - sem imóvel)
    ('deb-008', NULL, '55.666.777/0001-88', 'ISS', 4500.00,  '2026-04-30', 'PENDENTE'),
    -- ISS - João Carlos (vencido)
    ('deb-009', NULL, '987.654.321-00',      'ISS', 350.00,   '2026-02-28', 'VENCIDO'),
    -- ISS - Comércio Rápido (pago)
    ('deb-010', NULL, '11.222.333/0001-44',  'ISS', 1800.00,  '2026-03-31', 'PAGO')
ON CONFLICT (id_debito) DO NOTHING;

-- =============================================================================
-- 5. MODELOS DE PREDIÇÃO
-- =============================================================================
INSERT INTO tributario.modelo_predicao (id_modelo, versao, acuracia, data_treinamento) VALUES
    ('modelo-v1', 'v1.0-regressao-logistica', 0.7823, '2025-06-01'),
    ('modelo-v2', 'v2.0-random-forest',        0.8541, '2025-11-15'),
    ('modelo-v3', 'v3.0-gradient-boosting',    0.8912, '2026-03-10')
ON CONFLICT (id_modelo) DO NOTHING;

-- =============================================================================
-- 6. SCORES DE RECUPERABILIDADE
-- =============================================================================
INSERT INTO tributario.score_recuperabilidade
    (id_score, id_debito, id_modelo, score_valor, nivel_inadimplencia, data_calculo)
VALUES
    -- Débitos avaliados pelo modelo v3 (mais recente)
    ('score-001', 'deb-001', 'modelo-v3', 0.9800, 'BAIXO',   '2026-09-01'),  -- Maria pagou
    ('score-002', 'deb-002', 'modelo-v3', 0.1250, 'CRITICO', '2026-09-01'),  -- João vencido
    ('score-003', 'deb-003', 'modelo-v3', 0.6200, 'MEDIO',   '2026-09-01'),  -- Ana pendente
    ('score-004', 'deb-004', 'modelo-v3', 0.9500, 'BAIXO',   '2026-09-01'),  -- Carlos isenção
    ('score-005', 'deb-005', 'modelo-v3', 0.4800, 'MEDIO',   '2026-09-01'),  -- Fernanda parcelado
    ('score-006', 'deb-006', 'modelo-v3', 0.0950, 'CRITICO', '2026-09-01'),  -- Comércio Rápido IPTU
    ('score-007', 'deb-007', 'modelo-v3', 0.0320, 'CRITICO', '2026-09-01'),  -- Construtora vencido alto
    ('score-008', 'deb-008', 'modelo-v3', 0.3100, 'ALTO',    '2026-09-01'),  -- Serviços Tech ISS
    ('score-009', 'deb-009', 'modelo-v3', 0.2200, 'ALTO',    '2026-09-01'),  -- João ISS vencido
    ('score-010', 'deb-010', 'modelo-v3', 0.9600, 'BAIXO',   '2026-09-01'),  -- Comércio Rápido ISS pago
    -- Mesmos débitos avaliados pelo modelo v2 (histórico)
    ('score-011', 'deb-002', 'modelo-v2', 0.1580, 'CRITICO', '2026-06-01'),
    ('score-012', 'deb-007', 'modelo-v2', 0.0610, 'CRITICO', '2026-06-01')
ON CONFLICT (id_score) DO NOTHING;

-- =============================================================================
-- 7. LOGS DE AUDITORIA (simulação de acessos)
-- =============================================================================
INSERT INTO tributario.log_auditoria
    (id_log, id_analista, timestamp_acesso, filtros_aplicados, justificativa_lgpd)
VALUES
    ('log-001', 'analista-002',
     '2026-09-10 08:30:00',
     '{"tipo_tributo":"IPTU","status":"VENCIDO","setor":"SU-02"}',
     'Auditoria trimestral de inadimplência IPTU - Resolução Municipal 42/2026'),

    ('log-002', 'analista-002',
     '2026-09-15 14:10:00',
     '{"nivel_inadimplencia":"CRITICO"}',
     'Levantamento para notificação extrajudicial - Processo Adm. 2026/0091'),

    ('log-003', 'analista-001',
     '2026-09-20 09:00:00',
     '{"tipo_tributo":"ISS","status":"PENDENTE"}',
     'Revisão administrativa mensal - Competência Setembro/2026'),

    ('log-004', 'analista-004',
     '2026-09-23 16:45:00',
     '{"cpf_cnpj":"11.222.333/0001-44"}',
     'Consulta pontual solicitada pelo Departamento Jurídico - Ofício DJ-205/2026')
ON CONFLICT (id_log) DO NOTHING;

-- =============================================================================
-- FIM DOS DADOS PILOTO
-- =============================================================================
