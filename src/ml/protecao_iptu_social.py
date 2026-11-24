"""
Proteção do IPTU Social — RNF01 (Sprint 5, E3).

Regra formal que exclui os beneficiários do IPTU Social de QUALQUER ação
preditiva de cobrança: treino, scoring, carteira escorada e ranking do painel.

Grupos protegidos
-----------------
O Código Tributário de Palmas (Lei Complementar nº 285/2013, art. 20, II) isenta
do IPTU o imóvel cujo contribuinte seja:

    idoso        — idade superior a 65 anos;
    aposentado   — aposentado;
    pensionista  — pensionista;
    pcd          — pessoa com deficiência física incapacitada para o trabalho.

O § 1º do mesmo artigo exige, cumulativamente: único imóvel edificado no
Município, renda mensal de até 2 salários mínimos, uso exclusivamente
residencial e imposto (sem descontos) inferior a 150 UFIP. É por isso que o
enunciado fala em grupos "de baixa renda".

Quem decide se a pessoa é beneficiária é a Sefin, ao deferir a isenção. Este
módulo NÃO recalcula elegibilidade a partir de idade, renda ou deficiência (a
base não tem esses dados e o modelo não deve tratá-los). Ele consome o
resultado oficial do cadastro, em duas formas aceitas:

    1. indicador booleano: ``is_iptu_social`` (nome usado no pipeline),
       ``iptu_social`` (carteira sintética) ou ``boolean_is_iptu_social`` (DER);
    2. código do grupo (opcional): ``grupo_iptu_social`` com um dos códigos de
       ``GRUPOS_PROTEGIDOS``.

O registro é protegido se QUALQUER uma das formas indicar proteção.

Valores nulos ou inválidos (fail-safe)
--------------------------------------
Na política padrão (``"proteger"``), indicador nulo ou inválido é tratado como
protegido: o registro sai da cobrança preditiva e fica pendente de correção
cadastral. O erro mais grave possível aqui é cobrar um beneficiário; tirar da
fila alguém sem classificação só adia a cobrança até a revisão humana.
A política ``"erro"`` interrompe o pipeline em vez de proteger.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from numbers import Number
from pathlib import Path
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)

FUNDAMENTO_LEGAL = "Lei Complementar nº 285/2013 (Código Tributário de Palmas), art. 20, II e § 1º"

GRUPOS_PROTEGIDOS: dict[str, str] = {
    "idoso": "Contribuinte com idade superior a 65 anos",
    "aposentado": "Contribuinte aposentado",
    "pensionista": "Contribuinte pensionista",
    "pcd": "Pessoa com deficiência física incapacitada para o trabalho",
}

CONDICOES_CUMULATIVAS: tuple[str, ...] = (
    "Único imóvel edificado no Município de Palmas",
    "Renda mensal de até 2 salários mínimos",
    "Imóvel de uso exclusivamente residencial",
    "Imposto, sem descontos, inferior a 150 UFIP",
)

COLUNAS_INDICADOR: tuple[str, ...] = ("is_iptu_social", "iptu_social", "boolean_is_iptu_social")
COLUNA_GRUPO = "grupo_iptu_social"
COLUNA_ID = "id_contribuinte"
CAMINHO_CARTEIRA_BRUTA = Path("data/bruto/carteira_contribuintes_sintetica.csv")

POLITICAS = ("proteger", "erro")

_VERDADEIROS = {"1", "true", "verdadeiro", "sim", "s", "t", "yes", "y"}
_FALSOS = {"0", "false", "falso", "nao", "não", "n", "f", "no"}


class ViolacaoProtecaoIPTUSocial(AssertionError):
    """Um beneficiário do IPTU Social chegou a uma saída de cobrança preditiva."""


@dataclass
class RelatorioProtecao:
    """Resumo auditável de uma aplicação da regra."""

    total_registros: int
    protegidos: int
    indefinidos: int
    elegiveis: int
    por_motivo: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def normalizar_indicador(valor) -> bool | None:
    """
    Converte o indicador de IPTU Social em True/False.

    Retorna None quando o valor é nulo ou inválido (ex.: "", "talvez", 2, -1).
    """
    if valor is None or valor is pd.NA:
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, Number):
        if isinstance(valor, float) and math.isnan(valor):
            return None
        if valor == 1:
            return True
        if valor == 0:
            return False
        return None
    if hasattr(valor, "item"):  # numpy.bool_, numpy.int64...
        return normalizar_indicador(valor.item())
    texto = str(valor).strip().lower()
    if texto in _VERDADEIROS:
        return True
    if texto in _FALSOS:
        return False
    return None


def normalizar_grupo(valor) -> str | None:
    """
    Normaliza o código do grupo protegido.

    Retorna o código ("idoso", "aposentado", "pensionista", "pcd"), "" quando
    não há grupo informado, ou None quando o código é desconhecido.
    """
    if valor is None or valor is pd.NA or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    texto = str(valor).strip().lower()
    if texto in ("", "nenhum", "nao_se_aplica"):
        return ""
    return texto if texto in GRUPOS_PROTEGIDOS else None


# ---------------------------------------------------------------------------
# Regra
# ---------------------------------------------------------------------------
def _colunas_presentes(df: pd.DataFrame) -> tuple[list[str], bool]:
    indicadores = [c for c in COLUNAS_INDICADOR if c in df.columns]
    return indicadores, COLUNA_GRUPO in df.columns


def classificar_protecao(df: pd.DataFrame, politica: str = "proteger") -> pd.DataFrame:
    """
    Classifica cada registro e explica o motivo.

    Retorna um DataFrame com o mesmo índice e as colunas:
      - ``protegido`` (bool): True = não pode receber ação preditiva de cobrança;
      - ``motivo``: "indicador_iptu_social", "grupo:<codigo>",
        "indicador_indefinido" ou "nao_protegido".
    """
    if politica not in POLITICAS:
        raise ValueError(f"Política inválida: {politica!r}. Use uma de {POLITICAS}.")

    indicadores, tem_grupo = _colunas_presentes(df)
    if not indicadores and not tem_grupo:
        raise ValueError(
            "Coluna de IPTU Social não encontrada "
            f"(esperado uma de {list(COLUNAS_INDICADOR)} ou '{COLUNA_GRUPO}'). "
            "Sem ela não é possível garantir o RNF01."
        )

    protegido = pd.Series(False, index=df.index)
    indefinido = pd.Series(False, index=df.index)
    motivo = pd.Series("nao_protegido", index=df.index, dtype=object)

    for coluna in indicadores:
        valores = df[coluna].map(normalizar_indicador)
        sim = valores.map(lambda v: v is True).astype(bool)
        nulo = valores.isna()
        motivo[sim & ~protegido] = "indicador_iptu_social"
        protegido |= sim
        indefinido |= nulo

    if tem_grupo:
        grupos = df[COLUNA_GRUPO].map(normalizar_grupo)
        valido = grupos.map(lambda g: bool(g)).astype(bool)
        desconhecido = grupos.isna()
        motivo[valido & ~protegido] = "grupo:" + grupos[valido & ~protegido].astype(str)
        protegido |= valido
        indefinido |= desconhecido

    # Indefinido só importa se nenhuma outra fonte já protegeu o registro
    pendente = indefinido & ~protegido
    if pendente.any():
        if politica == "erro":
            raise ValueError(
                f"Existem {int(pendente.sum())} indicadores de IPTU Social nulos ou inválidos."
            )
        logger.warning(
            "%d registro(s) com indicador de IPTU Social nulo/inválido foram tratados "
            "como protegidos (fail-safe) e precisam de correção cadastral.",
            int(pendente.sum()),
        )
        motivo[pendente] = "indicador_indefinido"
        protegido |= pendente

    return pd.DataFrame({"protegido": protegido.astype(bool), "motivo": motivo})


def eh_grupo_protegido(dados: pd.DataFrame | dict, politica: str = "proteger"):
    """
    Diz se o(s) contribuinte(s) pertencem a um grupo protegido pelo IPTU Social.

    Aceita um DataFrame (retorna Series[bool]) ou um único registro em dict
    (retorna bool).
    """
    if isinstance(dados, dict):
        return bool(classificar_protecao(pd.DataFrame([dados]), politica)["protegido"].iloc[0])
    return classificar_protecao(dados, politica)["protegido"]


def excluir_grupos_protegidos(
    df: pd.DataFrame, politica: str = "proteger"
) -> tuple[pd.DataFrame, RelatorioProtecao]:
    """Remove os protegidos e devolve a base elegível com o relatório da exclusão."""
    classificacao = classificar_protecao(df, politica)
    elegivel = df[~classificacao["protegido"]].copy()
    contagem = classificacao.loc[classificacao["protegido"], "motivo"].value_counts()
    relatorio = RelatorioProtecao(
        total_registros=len(df),
        protegidos=int(classificacao["protegido"].sum()),
        indefinidos=int((classificacao["motivo"] == "indicador_indefinido").sum()),
        elegiveis=len(elegivel),
        por_motivo={str(k): int(v) for k, v in contagem.items()},
    )
    logger.info("RNF01: %s", relatorio)
    return elegivel, relatorio


def remover_colunas_de_protecao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove os indicadores depois do filtro.

    O código do grupo pode revelar deficiência (dado sensível, LGPD art. 11),
    então ele não segue para o modelo nem para as saídas.
    """
    return df.drop(columns=[*COLUNAS_INDICADOR, COLUNA_GRUPO], errors="ignore")


# ---------------------------------------------------------------------------
# Trava na saída (scoring, carteira escorada, ranking do painel)
# ---------------------------------------------------------------------------
def ids_protegidos(df: pd.DataFrame, coluna_id: str = COLUNA_ID, politica: str = "proteger") -> frozenset:
    """Conjunto de IDs pseudonimizados que nunca podem aparecer em uma saída de cobrança."""
    if coluna_id not in df.columns:
        raise ValueError(f"Coluna de identificação ausente: {coluna_id}")
    protegido = eh_grupo_protegido(df, politica)
    return frozenset(df.loc[protegido, coluna_id].astype(str))


def carregar_ids_protegidos(
    caminho: str | Path = CAMINHO_CARTEIRA_BRUTA, coluna_id: str = COLUNA_ID
) -> frozenset:
    """Lê o cadastro bruto (com o indicador) e devolve os IDs protegidos."""
    bruto = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype={coluna_id: str})
    return ids_protegidos(bruto, coluna_id)


def remover_protegidos_da_saida(
    saida: pd.DataFrame, protegidos: Iterable[str], coluna_id: str = COLUNA_ID
) -> tuple[pd.DataFrame, int]:
    """Retira da saída qualquer registro cujo ID esteja na lista de protegidos."""
    protegidos = frozenset(map(str, protegidos))
    if coluna_id not in saida.columns:
        raise ValueError(f"Coluna de identificação ausente na saída: {coluna_id}")
    vazou = saida[coluna_id].astype(str).isin(protegidos)
    if vazou.any():
        logger.warning("RNF01: %d registro(s) protegido(s) removido(s) da saída.", int(vazou.sum()))
    return saida[~vazou].copy(), int(vazou.sum())


def garantir_sem_protegidos(
    saida: pd.DataFrame, protegidos: Iterable[str], coluna_id: str = COLUNA_ID
) -> None:
    """
    Interrompe o pipeline se algum beneficiário estiver na saída.

    Também barra saídas que ainda tragam o indicador marcado como verdadeiro.
    """
    protegidos = frozenset(map(str, protegidos))
    if coluna_id not in saida.columns:
        raise ValueError(f"Coluna de identificação ausente na saída: {coluna_id}")
    vazados = set(saida[coluna_id].astype(str)) & protegidos
    if vazados:
        raise ViolacaoProtecaoIPTUSocial(
            f"RNF01 violado: {len(vazados)} beneficiário(s) do IPTU Social na saída de cobrança."
        )
    indicadores, tem_grupo = _colunas_presentes(saida)
    if indicadores or tem_grupo:
        if eh_grupo_protegido(saida).any():
            raise ViolacaoProtecaoIPTUSocial(
                "RNF01 violado: a saída contém registros marcados como IPTU Social."
            )
