import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_analisar_risco_endpoint():
    payload = [
        {
            "cpf_cnpj": "12345678901",
            "valor_debito": 15000.0,
            "data_vencimento": "2023-01-10",
            "tipo_tributo": "IPTU",
            "bairro": "Centro"
        }
    ]
    response = client.post("/api/v1/analise-risco", json=payload)
    assert response.status_code == 200
    dados = response.json()
    assert len(dados) == 1
    assert "cpf_cnpj_hash" in dados[0]
    assert dados[0]["faixa_valor_debito"] == "Alto"

def test_consultar_ibge_palmas_endpoint():
    response = client.get("/api/v1/ibge/palmas")
    assert response.status_code == 200
    assert isinstance(response.json(), list)