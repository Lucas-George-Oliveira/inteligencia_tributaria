"""Testes das métricas por subgrupo do Model Card (Sprint 5 - E1)."""
import pandas as pd
import pytest

from src.ml.model_card_metricas import metricas_grupo, resumo_fairness, tabela_subgrupo


def test_metricas_grupo_casos_conhecidos():
    y = pd.Series([1, 1, 0, 0])
    prob = pd.Series([0.9, 0.1, 0.8, 0.2])
    m = metricas_grupo(y, prob, limiar=0.5)
    assert m["taxa_real"] == 0.5
    assert m["taxa_selecao"] == 0.5
    assert m["tpr_recall"] == 0.5
    assert m["fpr"] == 0.5
    assert m["precisao"] == 0.5


def test_resumo_fairness_detecta_disparidade():
    df = pd.DataFrame({
        "grupo": ["a"] * 4 + ["b"] * 4,
        "inadimplente_proximo_periodo": [1, 0, 0, 0, 1, 0, 0, 0],
        "prob_inadimplencia": [0.9, 0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.1],
    })
    tab = tabela_subgrupo(df, "grupo", limiar=0.5)
    f = resumo_fairness(tab)
    assert f["razao_paridade_demografica"] == pytest.approx(0.25 / 0.75)
    assert f["diferenca_taxa_real"] == 0
    assert f["diferenca_fpr"] == pytest.approx(2 / 3 - 0)
