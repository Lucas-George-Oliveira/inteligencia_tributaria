import pytest
import pandas as pd
import networkx as nx
from src.core.grafo_vinculos import construir_grafo_vinculos, identificar_grupos_risco

def test_construir_grafo_vinculos():
    dados = pd.DataFrame([
        {"cpf_cnpj_hash": "hash_1", "valor_debito": 5000.0, "bairro": "Centro"},
        {"cpf_cnpj_hash": "hash_2", "valor_debito": 15000.0, "bairro": "Centro"},
    ])
    G = construir_grafo_vinculos(dados)
    
    assert isinstance(G, nx.Graph)
    assert G.number_of_nodes() == 3  # 2 devedores + 1 bairro
    assert G.nodes["hash_1"]["total_debito"] == 5000.0

def test_identificar_grupos_risco():
    dados = pd.DataFrame([
        {"cpf_cnpj_hash": "hash_1", "valor_debito": 5000.0, "bairro": "Plano Diretor Sul"},
        {"cpf_cnpj_hash": "hash_2", "valor_debito": 10000.0, "bairro": "Plano Diretor Sul"},
    ])
    G = construir_grafo_vinculos(dados)
    grupos = identificar_grupos_risco(G)

    assert len(grupos) == 1
    assert grupos[0]["tamanho_grupo"] == 2
    assert grupos[0]["total_debito"] == 15000.0