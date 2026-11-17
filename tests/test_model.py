"""Testes automatizados de serialização, carregamento e inferência do modelo (Entrega E3)."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from src.ml.preparar_base import preparar_base
from src.ml.scoring_recuperabilidade import (
    ATRIBUTOS_CATEGORICOS,
    ATRIBUTOS_NUMERICOS,
    gerar_scoring_recuperabilidade,
)

CAMINHO_MODELO = Path("models/modelo_campeao_recuperabilidade.joblib")
CAMINHO_PREPROC = Path("models/preprocessador_inadimplencia.joblib")


@pytest.fixture
def amostra_contribuintes() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "area_construida_m2": 120.0,
            "valor_venal": 250000.0,
            "valor_iptu_anual": 2000.0,
            "distancia_centro_km": 3.5,
            "exercicios_inadimplentes_5a": 0,
            "tempo_inadimplencia_dias": 0,
            "valor_divida_consolidada": 0.0,
            "qtd_parcelamentos_anteriores": 0,
            "parcelamento_rompido": 0,
            "qtd_notificacoes": 0,
            "tipo_imovel": "residencial",
            "setor_urbano": "SU-01",
        },
        {
            "area_construida_m2": 450.0,
            "valor_venal": 980000.0,
            "valor_iptu_anual": 14700.0,
            "distancia_centro_km": 11.2,
            "exercicios_inadimplentes_5a": 4,
            "tempo_inadimplencia_dias": 540,
            "valor_divida_consolidada": 48500.0,
            "qtd_parcelamentos_anteriores": 2,
            "parcelamento_rompido": 1,
            "qtd_notificacoes": 5,
            "tipo_imovel": "terreno",
            "setor_urbano": "SU-04",
        },
    ])


def test_artefatos_serializados_existem():
    assert CAMINHO_MODELO.is_file(), f"Artefato ausente: {CAMINHO_MODELO}"
    assert CAMINHO_PREPROC.is_file(), f"Pré-processador ausente: {CAMINHO_PREPROC}"


def test_carregamento_e_predicao_modelo_joblib(amostra_contribuintes):
    modelo = joblib.load(CAMINHO_MODELO)
    X = amostra_contribuintes[ATRIBUTOS_NUMERICOS + ATRIBUTOS_CATEGORICOS]

    preds = modelo.predict(X)
    probs = modelo.predict_proba(X)

    assert len(preds) == len(X)
    assert set(preds).issubset({0, 1})
    assert probs.shape == (len(X), 2)
    assert not np.isnan(probs).any()
    assert np.all((probs >= 0.0) & (probs <= 1.0))
    assert np.allclose(probs.sum(axis=1), 1.0)


def test_preprocessador_lida_com_categoria_desconhecida(amostra_contribuintes):
    preproc = joblib.load(CAMINHO_PREPROC)
    dados_novos = amostra_contribuintes.copy()
    dados_novos.loc[0, "setor_urbano"] = "SU-99-INEDITO"

    matriz = preproc.transform(dados_novos[ATRIBUTOS_NUMERICOS + ATRIBUTOS_CATEGORICOS])
    assert matriz.shape[0] == len(dados_novos)


def test_integracao_scoring_e_protecao_iptu_social(amostra_contribuintes):
    base_bruta = amostra_contribuintes.copy()
    base_bruta["cpf_cnpj"] = ["111.111.111-11", "222.222.222-22"]
    base_bruta["nome"] = ["Beneficiário Social", "Devedor Comum"]
    base_bruta["is_iptu_social"] = [True, False]

    base_elegivel = preparar_base(base_bruta)
    assert len(base_elegivel) == 1
    assert "cpf_cnpj" not in base_elegivel.columns

    resultado = gerar_scoring_recuperabilidade(base_elegivel, caminho_modelo=str(CAMINHO_MODELO))
    assert "score_recuperabilidade" in resultado.columns
    assert "faixa_recuperabilidade" in resultado.columns
    score = int(resultado["score_recuperabilidade"].iloc[0])
    assert 0 <= score <= 1000
