"""Transformação e validação dos registros de receitas da API NUCLEOGOV.

Regras conservadoras: valores monetários inválidos NÃO viram zero;
registros ambíguos são rejeitados para revisão, nunca escolhidos silenciosamente.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
import unicodedata

import pandas as pd

CAMPOS_TEXTO = (
    "orgao", "orgao_nome", "unidade_id", "unidade_nome", "codigo",
    "codigo_original", "descricao", "covid",
)
CAMPOS_DINHEIRO = ("valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo")
CAMPOS_IDENTIDADE = (
    "orgao", "unidade_id", "ano", "mes", "codigo", "codigo_original", "descricao",
)
CAMPOS_CONTEUDO = (
    "orgao", "orgao_nome", "unidade_id", "unidade_nome", "codigo",
    "codigo_original", "ano", "mes", "descricao", *CAMPOS_DINHEIRO, "covid",
)
CAMPOS_BANCO = ("chave_registro", "hash_conteudo", *CAMPOS_CONTEUDO)

_VAZIOS = {"", "null", "none", "nan", "n/a", "<na>"}
_DINHEIRO_SIMPLES = re.compile(r"^[+-]?\d+(?:[.,]\d{1,2})?$")
_DINHEIRO_BR = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?$")
_DINHEIRO_US = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?$")


@dataclass
class ResultadoLimpeza:
    validos: pd.DataFrame
    rejeitados: pd.DataFrame
    total_entrada: int
    duplicados: int
    grupos_conflitantes: int


def normalizar_texto(valor: Any) -> str | None:
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (ValueError, TypeError):
        pass
    texto = unicodedata.normalize("NFC", str(valor))
    texto = re.sub(r"\s+", " ", texto).strip()
    return None if texto.casefold() in _VAZIOS else texto


def converter_moeda(valor: Any) -> tuple[Decimal | None, bool]:
    """Devolve (valor_decimal, invalido). Ausência legítima => (None, False).

    Aceita '29442709.54', '29.442.709,54', '29,442,709.54' e '18.5'.
    Não admite mais de duas casas decimais, números incompletos ou infinitos.
    """
    if valor is None or (not isinstance(valor, (list, dict)) and pd.isna(valor)):
        return None, False
    if isinstance(valor, bool):
        return None, True
    texto = str(valor).replace("\u00a0", " ").replace("R$", "").strip().replace(" ", "")
    if texto.casefold() in _VAZIOS:
        return None, False
    negativo_parenteses = texto.startswith("(") and texto.endswith(")")
    if negativo_parenteses:
        texto = texto[1:-1]
    if _DINHEIRO_BR.fullmatch(texto):
        texto = texto.replace(".", "").replace(",", ".")
    elif _DINHEIRO_US.fullmatch(texto):
        texto = texto.replace(",", "")
    elif _DINHEIRO_SIMPLES.fullmatch(texto):
        texto = texto.replace(",", ".")
    else:
        return None, True
    try:
        numero = Decimal(texto)
        if negativo_parenteses:
            numero *= -1
        if not numero.is_finite() or abs(numero) >= Decimal("1000000000000000000"):
            return None, True
        return numero.quantize(Decimal("0.01")), False
    except (InvalidOperation, ValueError):
        return None, True


def _sha256_de_campos(registro: pd.Series, campos: tuple[str, ...]) -> str:
    valores = []
    for campo in campos:
        valor = registro[campo]
        if valor is None or (not isinstance(valor, Decimal) and pd.isna(valor)):
            valores.append(None)
        elif isinstance(valor, Decimal):
            valores.append(format(valor, ".2f"))
        elif campo in CAMPOS_IDENTIDADE and isinstance(valor, str):
            valores.append(valor.casefold())
        else:
            valores.append(valor)
    conteudo = json.dumps(valores, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def limpar_receitas(registros: list[dict[str, Any]]) -> ResultadoLimpeza:
    """Produz DataFrames válidos e rejeitados, sem modificar o JSON original."""
    if not isinstance(registros, list):
        raise ValueError("O arquivo JSON precisa conter uma lista de registros.")
    if not registros:
        raise ValueError("O arquivo JSON está vazio; carga cancelada.")
    if not all(isinstance(item, dict) for item in registros):
        raise ValueError("Todos os itens do JSON precisam ser objetos (dicionários).")

    df = pd.DataFrame(registros, dtype=object)  # preserva identificadores como texto/int original
    df["linha_origem"] = range(1, len(df) + 1)
    df["registro_original"] = [json.dumps(item, ensure_ascii=False, default=str) for item in registros]

    for campo in (*CAMPOS_TEXTO, "ano", "mes", *CAMPOS_DINHEIRO):
        if campo not in df.columns:
            df[campo] = None

    for campo in CAMPOS_TEXTO:
        df[campo] = df[campo].map(normalizar_texto)

    erros = {idx: [] for idx in df.index}
    for campo in ("ano", "mes"):
        numeros = pd.to_numeric(df[campo], errors="coerce")
        minimo, maximo = (1900, 2100) if campo == "ano" else (1, 12)
        valido = numeros.notna() & numeros.between(minimo, maximo) & (numeros == numeros.round())
        for idx in df.index[~valido]:
            erros[idx].append(f"{campo} ausente ou fora do intervalo")
        df[campo] = [int(numeros.loc[idx]) if valido.loc[idx] else None for idx in df.index]

    for campo in ("orgao", "codigo", "descricao"):
        for idx in df.index[df[campo].isna()]:
            erros[idx].append(f"{campo} obrigatório ausente")

    for campo in CAMPOS_DINHEIRO:
        resultados = df[campo].map(converter_moeda)
        df[campo] = resultados.map(lambda par: par[0])
        invalidos = resultados.map(lambda par: par[1])
        for idx in df.index[invalidos]:
            erros[idx].append(f"{campo} com formato inválido")

    for idx in df.index:
        if all(df.at[idx, c] is None for c in CAMPOS_DINHEIRO):
            erros[idx].append("todos os campos monetários ausentes")

    df["motivo_rejeicao"] = ["; ".join(erros[idx]) for idx in df.index]
    rejeitados = df[df["motivo_rejeicao"] != ""].copy()
    candidatos = df[df["motivo_rejeicao"] == ""].copy()

    if candidatos.empty:
        return ResultadoLimpeza(
            validos=pd.DataFrame(columns=(*CAMPOS_BANCO, "linha_origem")),
            rejeitados=rejeitados.reset_index(drop=True),
            total_entrada=len(registros), duplicados=0, grupos_conflitantes=0,
        )

    candidatos["chave_registro"] = candidatos.apply(
        lambda linha: _sha256_de_campos(linha, CAMPOS_IDENTIDADE), axis=1
    )
    candidatos["hash_conteudo"] = candidatos.apply(
        lambda linha: _sha256_de_campos(linha, CAMPOS_CONTEUDO), axis=1
    )

    # Se a mesma identidade tiver dados divergentes, rejeitar TODAS as versões:
    # não temos um ID de origem para decidir qual é a correta.
    quantidades_hash = candidatos.groupby("chave_registro")["hash_conteudo"].transform("nunique")
    conflitantes = candidatos[quantidades_hash > 1].copy()
    grupos_conflitantes = conflitantes["chave_registro"].nunique()
    if not conflitantes.empty:
        conflitantes["motivo_rejeicao"] = "mesma chave lógica com conteúdo divergente"
        rejeitados = pd.concat([rejeitados, conflitantes], ignore_index=True)

    sem_conflitos = candidatos[quantidades_hash == 1].copy()
    mascara_duplicados = sem_conflitos.duplicated(subset=["chave_registro"], keep="first")
    duplicados = int(mascara_duplicados.sum())
    validos = sem_conflitos[~mascara_duplicados].copy()

    return ResultadoLimpeza(
        validos=validos[[*CAMPOS_BANCO, "linha_origem"]].reset_index(drop=True),
        rejeitados=rejeitados.sort_values("linha_origem").reset_index(drop=True),
        total_entrada=len(registros), duplicados=duplicados,
        grupos_conflitantes=int(grupos_conflitantes),
    )
