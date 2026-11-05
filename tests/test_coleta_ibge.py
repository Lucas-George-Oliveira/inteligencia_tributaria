import pytest
import pandas as pd
from src.api.coleta_ibge import obter_indicadores_ibge, estruturar_dados_socioeconomicos

def test_obter_indicadores_ibge_sucesso():
    dados = obter_indicadores_ibge()
    assert isinstance(dados, dict)
    assert dados.get("status") == "sucesso"
    assert dados.get("codigo_ibge") == "1721000"

def test_estruturar_dados_socioeconomicos():
    dados_mock = {
        "status": "sucesso",
        "dados_brutos": [
            {"id": 30255, "resumida": [{"valor": "300000"}]}
        ]
    }
    df = estruturar_dados_socioeconomicos(dados_mock)
    assert isinstance(df, pd.DataFrame)
    assert "codigo_ibge" in df.columns
    assert "valor" in df.columns
    assert len(df) == 1