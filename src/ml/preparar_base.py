
import pandas as pd


def preparar_base(dados: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara a base para a modelagem preditiva.

    Exclui beneficiarios do IPTU Social
    e remove identificadores pessoais diretos.
    """

    df = dados.copy()

        # Compatibilidade com a base sintetica do professor
    if "is_iptu_social" not in df.columns and "iptu_social" in df.columns:
        df = df.rename(columns={
            "iptu_social": "is_iptu_social"
        })

    # Verifica se a coluna obrigatoria existe
    if "is_iptu_social" not in df.columns:
        raise ValueError(
            "Coluna is_iptu_social nao encontrada."
        )

    # Impede o uso de registros sem classificacao
    if not df["is_iptu_social"].isin([True, False]).all():
        raise ValueError(
            "Existem indicadores de IPTU Social invalidos."
        )

    # RNF01: exclui beneficiarios da base preditiva
    df = df[df["is_iptu_social"] == False].copy()

    # Remove identificadores pessoais diretos
    colunas_sensiveis = [
        "cpf_cnpj",
        "nome",
        "contato",
        "logradouro",
        "inscricao_imobiliaria",
    ]

    df = df.drop(columns=colunas_sensiveis, errors="ignore")

    # Remove o indicador que ja foi utilizado no filtro
    df = df.drop(columns=["is_iptu_social"])

    return df
