"""Testes das funções de dados do painel Streamlit (Sprint 4 - E4)."""
import pandas as pd
import pytest

from src.painel.painel_sefin import (
    ARQ_CARTEIRA,
    COORD_SETORES,
    carregar_carteira,
    curva_arrecadacao,
    metricas_por_subgrupo,
    resumo_por_setor,
)


@pytest.fixture(scope="module")
def carteira():
    if not ARQ_CARTEIRA.exists():
        pytest.skip("carteira escorada ainda não gerada pelo pipeline")
    return carregar_carteira()


def test_uma_linha_por_contribuinte(carteira):
    assert carteira["id_contribuinte"].is_unique
    assert carteira["data_referencia_simulada"].nunique() == 1


def test_todos_os_setores_tem_coordenada(carteira):
    assert set(carteira["setor_urbano"]) <= set(COORD_SETORES)


def test_resumo_por_setor_soma_a_carteira(carteira):
    resumo = resumo_por_setor(carteira, limiar=0.23)
    assert resumo["contribuintes"].sum() == len(carteira)
    assert resumo["arrecadacao_esperada"].sum() == pytest.approx(carteira["retorno_esperado_estimado"].sum())


def test_curva_de_arrecadacao_e_crescente_e_fecha_no_total(carteira):
    curva = curva_arrecadacao(carteira)
    assert curva["arrecadacao_acumulada"].is_monotonic_increasing
    assert curva["arrecadacao_acumulada"].iloc[-1] == pytest.approx(carteira["retorno_esperado_estimado"].sum())


def test_metricas_por_subgrupo():
    df = pd.DataFrame({
        "grupo": ["a", "a", "b", "b"],
        "inadimplente_proximo_periodo": [1, 0, 1, 0],
        "prob_inadimplencia": [0.9, 0.1, 0.1, 0.9],
    })
    tab = metricas_por_subgrupo(df, "grupo", limiar=0.5).set_index("grupo")
    assert tab.loc["a", "recall"] == 1.0 and tab.loc["a", "acuracia"] == 1.0
    assert tab.loc["b", "recall"] == 0.0 and tab.loc["b", "acuracia"] == 0.0
