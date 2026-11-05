#"""Testes automatizados da engenharia de atributos."""

import numpy as np
import pandas as pd
import pytest

from src.core.engenharia_atributos import engenharia_atributos


@pytest.fixture
def dados_exemplo():
    """Cria uma base fictícia para testar os atributos."""

    return pd.DataFrame({
        "valor_debito": [500.00, 2000.00, 8000.00, 15000.00],
        "data_vencimento": [
            "2026-10-01",
            "2026-09-01",
            "2026-06-01",
            "2026-01-01",
        ],
        "tipo_tributo": ["IPTU", "ISS", "IPTU", "ISS"],
        "status_pagamento": [
            "INADIMPLENTE",
            "INADIMPLENTE",
            "INADIMPLENTE",
            "INADIMPLENTE",
        ],
    })


def test_criacao_dos_atributos(dados_exemplo):
    """Verifica se as novas colunas foram criadas."""

    resultado = engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    colunas_esperadas = [
        "dias_atraso",
        "meses_atraso",
        "indicador_atraso",
        "mes_vencimento",
        "trimestre_vencimento",
        "vencimento_fim_ano",
        "mes_seno",
        "mes_cosseno",
        "faixa_divida",
    ]

    for coluna in colunas_esperadas:
        assert coluna in resultado.columns


def test_calculo_dias_atraso(dados_exemplo):
    """Verifica o cálculo dos dias de atraso."""

    resultado = engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    assert resultado["dias_atraso"].tolist() == [
        33, 63, 155, 306
    ]


def test_calculo_meses_atraso(dados_exemplo):
    """Verifica os meses aproximados de atraso."""

    resultado = engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    assert resultado["meses_atraso"].tolist() == [
        1, 2, 5, 10
    ]


def test_faixas_de_divida(dados_exemplo):
    """Verifica a categorização dos valores das dívidas."""

    resultado = engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    assert resultado["faixa_divida"].astype(str).tolist() == [
        "BAIXA",
        "MEDIA",
        "ALTA",
        "MUITO_ALTA",
    ]


def test_indicador_de_sazonalidade(dados_exemplo):
    """Verifica a identificação de vencimentos no fim do ano."""

    resultado = engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    assert resultado["vencimento_fim_ano"].tolist() == [
        0, 0, 0, 0
    ]


def test_dados_originais_nao_sao_modificados(dados_exemplo):
    """Verifica se a função preserva a base original."""

    original = dados_exemplo.copy()

    engenharia_atributos(
        dados_exemplo,
        data_referencia="2026-11-03",
    )

    pd.testing.assert_frame_equal(
        dados_exemplo,
        original,
    )


def test_erro_quando_coluna_obrigatoria_esta_ausente():
    """Verifica a validação das colunas obrigatórias."""

    dados = pd.DataFrame({
        "valor_debito": [100.00],
    })

    with pytest.raises(ValueError):
        engenharia_atributos(
            dados,
            data_referencia="2026-11-03",
        )
