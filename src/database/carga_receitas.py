"""Carga transacional e idempotente dos dados tratados para uma tabela de integração.

A tabela é separada das tabelas de negócio preexistentes da Sprint 2.
A integração direta às tabelas da Sprint 2 exige conhecer o DDL/modelos reais.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

import pandas as pd
from sqlalchemy import (
    Column, DateTime, Integer, MetaData, Numeric, String, Table, Text,
    bindparam, create_engine, inspect, select, update,
)
from sqlalchemy.engine import Engine

from src.core.limpeza_receitas import CAMPOS_BANCO


@dataclass
class ResultadoCarga:
    inseridos: int = 0
    atualizados: int = 0
    sem_alteracao: int = 0


def _identificador_valido(nome: str, campo: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", nome):
        raise ValueError(f"{campo} deve conter somente letras, números ou _ e não pode iniciar por número.")
    return nome


def definir_tabela(nome: str = "receitas_sefin_etl", schema: str | None = None) -> Table:
    _identificador_valido(nome, "ETL_TABELA")
    if schema:
        _identificador_valido(schema, "ETL_SCHEMA")
    metadados = MetaData()
    return Table(
        nome, metadados,
        Column("chave_registro", String(64), primary_key=True),
        Column("hash_conteudo", String(64), nullable=False),
        Column("orgao", String(50), nullable=False),
        Column("orgao_nome", String(255)),
        Column("unidade_id", String(70)),
        Column("unidade_nome", String(255)),
        Column("codigo", String(120), nullable=False),
        Column("codigo_original", String(120)),
        Column("ano", Integer, nullable=False),
        Column("mes", Integer, nullable=False),
        Column("descricao", Text, nullable=False),
        Column("valor_orcado", Numeric(20, 2)),
        Column("valor_arrecado_mes", Numeric(20, 2)),
        Column("valor_arrecado_periodo", Numeric(20, 2)),
        Column("covid", String(20)),
        Column("origem_arquivo", String(255), nullable=False),
        Column("processado_em", DateTime(timezone=True), nullable=False),
        schema=schema,
    )


def _verificar_estrutura(engine: Engine, tabela: Table) -> Table:
    insp = inspect(engine)
    if not insp.has_table(tabela.name, schema=tabela.schema):
        raise RuntimeError(
            f"Tabela {tabela.name!r} ainda não existe no banco. "
            "Para criá-la explicitamente, execute com --criar-tabela."
        )
    real = Table(tabela.name, MetaData(), schema=tabela.schema, autoload_with=engine)
    ausentes = set(tabela.c.keys()) - set(real.c.keys())
    if ausentes:
        raise RuntimeError(
            "A tabela existente não é compatível com o modelo deste ETL. "
            f"Colunas ausentes: {', '.join(sorted(ausentes))}. "
            "Não apontar ETL_TABELA para uma tabela da Sprint 2 sem adaptar o mapeamento."
        )
    # A unicidade de chave é necessária para impedir duplicatas em execuções concorrentes.
    pk = insp.get_pk_constraint(tabela.name, schema=tabela.schema).get("constrained_columns") or []
    unicas = [u.get("column_names") or [] for u in insp.get_unique_constraints(tabela.name, schema=tabela.schema)]
    unicas.extend(idx.get("column_names") or [] for idx in insp.get_indexes(tabela.name, schema=tabela.schema) if idx.get("unique"))
    if "chave_registro" not in pk and not any(cols == ["chave_registro"] for cols in unicas):
        raise RuntimeError("A tabela precisa de PRIMARY KEY ou UNIQUE em chave_registro.")
    return real


def carregar_receitas(
    validos: pd.DataFrame,
    url_banco: str,
    origem_arquivo: str,
    criar_tabela: bool = False,
    nome_tabela: str = "receitas_sefin_etl",
    schema: str | None = None,
    tamanho_lote: int = 500,
) -> ResultadoCarga:
    """Insere novos, atualiza alterados e ignora registros idênticos.

    Usa uma única transação: qualquer erro desfaz toda a carga desta execução.
    """
    if not url_banco:
        raise ValueError("Defina ETL_DATABASE_URL (ou DATABASE_URL) no .env antes da carga.")
    if tamanho_lote < 1:
        raise ValueError("tamanho_lote precisa ser positivo")
    if not isinstance(validos, pd.DataFrame):
        raise TypeError("validos deve ser um pandas.DataFrame")
    if validos.empty:
        return ResultadoCarga()
    ausentes = set(CAMPOS_BANCO) - set(validos.columns)
    if ausentes:
        raise ValueError(f"DataFrame sem colunas obrigatórias: {sorted(ausentes)}")

    modelo = definir_tabela(nome_tabela, schema)
    engine = create_engine(url_banco, pool_pre_ping=True)
    try:
        if criar_tabela:
            modelo.metadata.create_all(engine, tables=[modelo], checkfirst=True)
        tabela = _verificar_estrutura(engine, modelo)
        resultado = ResultadoCarga()
        instante = datetime.now(timezone.utc)
        registros: list[dict[str, Any]] = []
        for linha in validos.to_dict(orient="records"):
            registro = {campo: linha[campo] for campo in CAMPOS_BANCO}
            registro["origem_arquivo"] = origem_arquivo[:255]
            registro["processado_em"] = instante
            registros.append(registro)

        # Toda a execução é atômica, inclusive quando contém vários lotes.
        with engine.begin() as conexao:
            for inicio in range(0, len(registros), tamanho_lote):
                lote = registros[inicio : inicio + tamanho_lote]
                chaves = [item["chave_registro"] for item in lote]
                existentes = dict(conexao.execute(
                    select(tabela.c.chave_registro, tabela.c.hash_conteudo)
                    .where(tabela.c.chave_registro.in_(chaves))
                ).all())
                novos, modificados = [], []
                for item in lote:
                    hash_anterior = existentes.get(item["chave_registro"])
                    if hash_anterior is None:
                        novos.append(item)
                    elif hash_anterior != item["hash_conteudo"]:
                        modificados.append(item)
                    else:
                        resultado.sem_alteracao += 1

                if novos:
                    conexao.execute(tabela.insert(), novos)  # executemany / inserção em lote
                    resultado.inseridos += len(novos)
                if modificados:
                    campos_alteraveis = [c for c in tabela.c.keys() if c != "chave_registro"]
                    comando = (
                        update(tabela)
                        .where(tabela.c.chave_registro == bindparam("b_chave"))
                        .values(**{col: bindparam(f"b_{col}") for col in campos_alteraveis})
                    )
                    parametros = [
                        {"b_chave": item["chave_registro"], **{
                            f"b_{col}": item[col] for col in campos_alteraveis
                        }} for item in modificados
                    ]
                    conexao.execute(comando, parametros)
                    resultado.atualizados += len(modificados)
        return resultado
    finally:
        engine.dispose()
