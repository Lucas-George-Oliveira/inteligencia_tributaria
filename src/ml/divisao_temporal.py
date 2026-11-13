
import pandas as pd


def dividir_temporal(
    dados: pd.DataFrame,
    coluna_data: str = "data_vencimento",
    proporcao_treino: float = 0.60,
    proporcao_validacao: float = 0.20,
):
    """
    Divide os dados cronologicamente em treino,
    validacao e teste, mantendo datas iguais
    no mesmo conjunto.
    """

    # Verifica se a coluna de data existe
    if coluna_data not in dados.columns:
        raise ValueError(
            f"Coluna obrigatoria ausente: {coluna_data}"
        )

    # Verifica se existem registros
    if dados.empty:
        raise ValueError("A base de dados esta vazia.")

    # Valida as proporcoes
    if not (
        0 < proporcao_treino < 1
        and 0 < proporcao_validacao < 1
        and proporcao_treino + proporcao_validacao < 1
    ):
        raise ValueError("Proporcoes invalidas.")

    # Cria uma copia para preservar a base original
    df = dados.copy()

    # Converte as datas para o formato correto
    df[coluna_data] = pd.to_datetime(
        df[coluna_data], errors="coerce"
    )

    if df[coluna_data].isna().any():
        raise ValueError("Existem datas invalidas ou vazias.")

    # Ordena os registros cronologicamente
    df = df.sort_values(coluna_data).reset_index(drop=True)

    # Identifica as datas diferentes existentes
    datas = df[coluna_data].drop_duplicates().tolist()
    total_datas = len(datas)

    if total_datas < 3:
        raise ValueError(
            "Sao necessarias pelo menos 3 datas distintas."
        )

    # Calcula os limites de cada conjunto
    n_treino = max(1, int(total_datas * proporcao_treino))
    n_validacao = max(
        1, int(total_datas * proporcao_validacao)
    )

    if n_treino + n_validacao >= total_datas:
        raise ValueError(
            "Datas insuficientes para os tres conjuntos."
        )

    limite_treino = datas[n_treino - 1]
    limite_validacao = datas[
        n_treino + n_validacao - 1
    ]

    # Separa os registros pelos limites temporais
    treino = df[
        df[coluna_data] <= limite_treino
    ].copy()

    validacao = df[
        (df[coluna_data] > limite_treino)
        & (df[coluna_data] <= limite_validacao)
    ].copy()

    teste = df[
        df[coluna_data] > limite_validacao
    ].copy()

    return treino, validacao, teste
