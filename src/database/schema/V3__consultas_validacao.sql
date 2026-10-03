-- =============================================================================
-- SISTEMA TRIBUTÁRIO - CONSULTAS DE VALIDAÇÃO
-- Script: V3__consultas_validacao.sql
-- Descrição: Consultas para verificar integridade dos dados, regras de negócio
--            e cálculos de inadimplência após a carga do piloto.
-- =============================================================================

SET search_path TO tributario, public;

-- =============================================================================
-- BLOCO 1: VERIFICAÇÃO DE INTEGRIDADE ESTRUTURAL
-- =============================================================================

-- 1.1 Conta registros em cada tabela
SELECT 'contribuinte'           AS tabela, COUNT(*) AS total FROM tributario.contribuinte
UNION ALL
SELECT 'analista_fiscal',                  COUNT(*) FROM tributario.analista_fiscal
UNION ALL
SELECT 'imovel',                           COUNT(*) FROM tributario.imovel
UNION ALL
SELECT 'debito_tributario',                COUNT(*) FROM tributario.debito_tributario
UNION ALL
SELECT 'modelo_predicao',                  COUNT(*) FROM tributario.modelo_predicao
UNION ALL
SELECT 'score_recuperabilidade',           COUNT(*) FROM tributario.score_recuperabilidade
UNION ALL
SELECT 'log_auditoria',                    COUNT(*) FROM tributario.log_auditoria
ORDER BY tabela;

-- Resultado esperado:
-- analista_fiscal          | 4
-- contribuinte             | 8
-- debito_tributario        | 10
-- imovel                   | 7
-- log_auditoria            | 4
-- modelo_predicao          | 3
-- score_recuperabilidade   | 12

-- =============================================================================
-- BLOCO 2: ÍNDICE GERAL DE INADIMPLÊNCIA POR TIPO DE TRIBUTO
-- =============================================================================

-- 2.1 Taxa de inadimplência global (débitos VENCIDOS / total não cancelados)
SELECT
    tipo_tributo,
    COUNT(*)                                                          AS total_debitos,
    COUNT(*) FILTER (WHERE status_pagamento = 'VENCIDO')             AS total_vencidos,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status_pagamento = 'VENCIDO')
        / NULLIF(COUNT(*) FILTER (WHERE status_pagamento <> 'CANCELADO'), 0),
        2
    )                                                                 AS perc_inadimplencia,
    SUM(valor_debito)                                                 AS valor_total_lancado,
    SUM(valor_debito) FILTER (WHERE status_pagamento = 'VENCIDO')    AS valor_total_vencido
FROM tributario.debito_tributario
GROUP BY tipo_tributo
ORDER BY perc_inadimplencia DESC;

-- =============================================================================
-- BLOCO 3: RANKING DE INADIMPLENTES POR SCORE CRÍTICO
-- =============================================================================

-- 3.1 Top inadimplentes - nível CRÍTICO ordenados pelo menor score (maior risco)
SELECT
    c.cpf_cnpj,
    c.nome,
    c.is_iptu_social,
    d.tipo_tributo,
    d.valor_debito,
    d.data_vencimento,
    d.status_pagamento,
    sr.score_valor,
    sr.nivel_inadimplencia,
    mp.versao                           AS modelo_usado,
    DATE_PART('day', NOW() - d.data_vencimento::TIMESTAMP) AS dias_atraso
FROM tributario.score_recuperabilidade sr
JOIN tributario.debito_tributario d  ON d.id_debito  = sr.id_debito
JOIN tributario.contribuinte      c  ON c.cpf_cnpj   = d.cpf_cnpj
JOIN tributario.modelo_predicao   mp ON mp.id_modelo  = sr.id_modelo
WHERE sr.nivel_inadimplencia IN ('CRITICO', 'ALTO')
  AND d.status_pagamento = 'VENCIDO'
ORDER BY sr.score_valor ASC, d.valor_debito DESC;

-- =============================================================================
-- BLOCO 4: ANÁLISE POR SETOR URBANO (IPTU)
-- =============================================================================

-- 4.1 Inadimplência IPTU por setor urbano
SELECT
    i.setor_urbano,
    COUNT(DISTINCT d.id_debito)                                              AS qtd_debitos,
    SUM(d.valor_debito)                                                      AS valor_lancado,
    SUM(d.valor_debito) FILTER (WHERE d.status_pagamento = 'VENCIDO')       AS valor_vencido,
    ROUND(
        100.0 * SUM(d.valor_debito) FILTER (WHERE d.status_pagamento = 'VENCIDO')
        / NULLIF(SUM(d.valor_debito) FILTER (WHERE d.status_pagamento <> 'CANCELADO'), 0),
        2
    )                                                                        AS perc_inadimplencia_valor
FROM tributario.debito_tributario d
JOIN tributario.imovel i ON i.inscricao_imobiliaria = d.inscricao_imobiliaria
WHERE d.tipo_tributo = 'IPTU'
GROUP BY i.setor_urbano
ORDER BY perc_inadimplencia_valor DESC;

-- =============================================================================
-- BLOCO 5: DISTRIBUIÇÃO DOS SCORES POR NÍVEL DE INADIMPLÊNCIA
-- =============================================================================

-- 5.1 Distribuição dos níveis de inadimplência (modelo mais recente)
SELECT
    sr.nivel_inadimplencia,
    COUNT(*)                        AS qtd_debitos,
    ROUND(AVG(sr.score_valor), 4)  AS score_medio,
    ROUND(MIN(sr.score_valor), 4)  AS score_minimo,
    ROUND(MAX(sr.score_valor), 4)  AS score_maximo,
    SUM(d.valor_debito)            AS valor_total_envolvido
FROM tributario.score_recuperabilidade sr
JOIN tributario.debito_tributario d ON d.id_debito = sr.id_debito
JOIN tributario.modelo_predicao   m ON m.id_modelo  = sr.id_modelo
WHERE m.versao = 'v3.0-gradient-boosting'   -- modelo mais recente
GROUP BY sr.nivel_inadimplencia
ORDER BY score_medio ASC;

-- =============================================================================
-- BLOCO 6: CONTRIBUINTES COM IPTU SOCIAL E SEUS DÉBITOS
-- =============================================================================

-- 6.1 Verifica se contribuintes com isenção social têm débitos críticos
SELECT
    c.cpf_cnpj,
    c.nome,
    d.tipo_tributo,
    d.valor_debito,
    d.status_pagamento,
    sr.nivel_inadimplencia,
    sr.score_valor
FROM tributario.contribuinte c
JOIN tributario.debito_tributario        d  ON d.cpf_cnpj  = c.cpf_cnpj
LEFT JOIN tributario.score_recuperabilidade sr ON sr.id_debito = d.id_debito
WHERE c.is_iptu_social = TRUE
ORDER BY sr.score_valor ASC NULLS LAST;

-- =============================================================================
-- BLOCO 7: COMPARAÇÃO ENTRE MODELOS (EVOLUÇÃO DA ACURÁCIA)
-- =============================================================================

-- 7.1 Diferença de score entre modelos para o mesmo débito
SELECT
    d.id_debito,
    c.nome                                                AS contribuinte,
    d.tipo_tributo,
    d.valor_debito,
    MAX(sr.score_valor) FILTER (WHERE m.versao = 'v2.0-random-forest')       AS score_v2,
    MAX(sr.score_valor) FILTER (WHERE m.versao = 'v3.0-gradient-boosting')   AS score_v3,
    ROUND(
        MAX(sr.score_valor) FILTER (WHERE m.versao = 'v3.0-gradient-boosting')
        - MAX(sr.score_valor) FILTER (WHERE m.versao = 'v2.0-random-forest'),
        4
    )                                                     AS variacao_score
FROM tributario.score_recuperabilidade sr
JOIN tributario.debito_tributario d ON d.id_debito  = sr.id_debito
JOIN tributario.modelo_predicao   m ON m.id_modelo  = sr.id_modelo
JOIN tributario.contribuinte      c ON c.cpf_cnpj   = d.cpf_cnpj
GROUP BY d.id_debito, c.nome, d.tipo_tributo, d.valor_debito
HAVING COUNT(DISTINCT sr.id_modelo) > 1    -- só débitos avaliados por 2+ modelos
ORDER BY ABS(
    MAX(sr.score_valor) FILTER (WHERE m.versao = 'v3.0-gradient-boosting')
    - MAX(sr.score_valor) FILTER (WHERE m.versao = 'v2.0-random-forest')
) DESC;

-- =============================================================================
-- BLOCO 8: TRILHA DE AUDITORIA LGPD
-- =============================================================================

-- 8.1 Acessos por analista e quantidade de consultas
SELECT
    af.id_analista,
    af.nome                         AS analista,
    af.perfil,
    COUNT(la.id_log)               AS total_acessos,
    MIN(la.timestamp_acesso)       AS primeiro_acesso,
    MAX(la.timestamp_acesso)       AS ultimo_acesso
FROM tributario.analista_fiscal af
LEFT JOIN tributario.log_auditoria la ON la.id_analista = af.id_analista
GROUP BY af.id_analista, af.nome, af.perfil
ORDER BY total_acessos DESC;

-- 8.2 Logs com justificativa LGPD - listagem completa
SELECT
    la.id_log,
    af.nome                     AS analista,
    af.perfil,
    la.timestamp_acesso,
    la.filtros_aplicados,
    la.justificativa_lgpd
FROM tributario.log_auditoria la
JOIN tributario.analista_fiscal af ON af.id_analista = la.id_analista
ORDER BY la.timestamp_acesso DESC;

-- =============================================================================
-- BLOCO 9: VISÃO CONSOLIDADA - DASHBOARD EXECUTIVO
-- =============================================================================

-- 9.1 Resumo executivo para o painel gerencial
SELECT
    tipo_tributo                                                         AS tributo,
    COUNT(*)                                                             AS total_debitos,
    SUM(valor_debito)                                                    AS valor_total_R$,
    SUM(valor_debito) FILTER (WHERE status_pagamento = 'PAGO')          AS arrecadado_R$,
    SUM(valor_debito) FILTER (WHERE status_pagamento = 'VENCIDO')       AS inadimplente_R$,
    SUM(valor_debito) FILTER (WHERE status_pagamento = 'PENDENTE')      AS a_vencer_R$,
    SUM(valor_debito) FILTER (WHERE status_pagamento = 'PARCELADO')     AS parcelado_R$,
    ROUND(
        100.0 * SUM(valor_debito) FILTER (WHERE status_pagamento = 'PAGO')
        / NULLIF(SUM(valor_debito), 0), 2
    )                                                                    AS perc_arrecadado
FROM tributario.debito_tributario
GROUP BY tipo_tributo
ORDER BY tipo_tributo;

-- =============================================================================
-- FIM DAS CONSULTAS DE VALIDAÇÃO
-- =============================================================================
