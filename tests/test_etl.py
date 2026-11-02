"""Testes que não acessam API nem o banco real da Sprint 2."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func

from src.core.limpeza_receitas import converter_moeda, limpar_receitas
from src.database.carga_receitas import carregar_receitas, definir_tabela


@pytest.fixture
def base():
    return {
        "orgao": "2798", "orgao_nome": "TESOURO MUNICIPAL",
        "unidade_id": None, "unidade_nome": None,
        "codigo": "1.7.2.1", "codigo_original": "172", "descricao": "RECEITAS MUNICIPAIS",
        "ano": "2026", "mes": "10", "valor_orcado": "240340546",
        "valor_arrecado_mes": "27271775.52", "valor_arrecado_periodo": "27271775.52",
        "covid": "0", "total": "180997",
    }


@pytest.mark.parametrize("entrada,esperado", [
    ("29442709.54", Decimal("29442709.54")),
    ("29.442.709,54", Decimal("29442709.54")),
    ("29,442,709.54", Decimal("29442709.54")),
    ("18.5", Decimal("18.50")),
    ("-25,33", Decimal("-25.33")),
    (None, None),
])
def test_moeda(entrada, esperado):
    assert converter_moeda(entrada) == (esperado, False)


def test_moeda_invalida():
    assert converter_moeda("abc")[1] is True
    assert converter_moeda("12.3456")[1] is True


def test_limpeza_duplicados_e_rejeitados(base):
    duplicado = deepcopy(base)
    ruim = deepcopy(base)
    ruim["mes"] = "13"
    resultado = limpar_receitas([base, duplicado, ruim])
    assert resultado.total_entrada == 3
    assert len(resultado.validos) == 1
    assert resultado.duplicados == 1
    assert len(resultado.rejeitados) == 1
    assert "mes" in resultado.rejeitados.iloc[0]["motivo_rejeicao"]
    assert resultado.validos.iloc[0]["valor_arrecado_mes"] == Decimal("27271775.52")


def test_mesma_chave_com_valores_divergentes_rejeita_ambos(base):
    outro = deepcopy(base)
    outro["valor_orcado"] = "999.00"
    resultado = limpar_receitas([base, outro])
    assert len(resultado.validos) == 0
    assert len(resultado.rejeitados) == 2
    assert resultado.grupos_conflitantes == 1


def test_nao_transforma_nulos_em_zero(base):
    base["valor_arrecado_mes"] = None
    resultado = limpar_receitas([base])
    assert len(resultado.validos) == 1
    assert resultado.validos.iloc[0]["valor_arrecado_mes"] is None


def test_carga_e_reexecucao_idempotente(base, tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'sefin.db'}"
    resultado = limpar_receitas([base])
    a = carregar_receitas(resultado.validos, url, "teste.json", criar_tabela=True)
    assert (a.inseridos, a.atualizados, a.sem_alteracao) == (1, 0, 0)
    b = carregar_receitas(resultado.validos, url, "teste.json")
    assert (b.inseridos, b.atualizados, b.sem_alteracao) == (0, 0, 1)
    outro = deepcopy(base)
    outro["valor_arrecado_mes"] = "1234.56"
    atual = limpar_receitas([outro])
    c = carregar_receitas(atual.validos, url, "teste_2.json")
    assert (c.inseridos, c.atualizados, c.sem_alteracao) == (0, 1, 0)
    engine = create_engine(url)
    tabela = definir_tabela()
    with engine.connect() as conexao:
        assert conexao.scalar(select(func.count()).select_from(tabela)) == 1
        assert conexao.scalar(select(tabela.c.valor_arrecado_mes)) == Decimal("1234.56")
    engine.dispose()


def test_nao_cria_tabela_sem_autorizacao(base, tmp_path):
    url = f"sqlite:///{tmp_path / 'vazio.db'}"
    resultado = limpar_receitas([base])
    with pytest.raises(RuntimeError, match="--criar-tabela"):
        carregar_receitas(resultado.validos, url, "teste.json")


def test_schema_automatico_postgresql():
    from sqlalchemy.engine import make_url
    assert make_url("postgresql+psycopg2://alguem:senha@localhost/exemplo").get_backend_name() == "postgresql"


def test_schema_automatico_sqlite():
    from sqlalchemy.engine import make_url
    assert make_url("sqlite:///./data/sefin_demo.db").get_backend_name() == "sqlite"
