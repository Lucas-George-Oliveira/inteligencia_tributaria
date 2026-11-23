import pandas as pd

from src.ml.protecao_iptu_social import (
    excluir_grupos_protegidos,
    remover_colunas_de_protecao,
)


def preparar_base(dados: pd.DataFrame, politica_indefinido: str = "proteger") -> pd.DataFrame:
    """
    Prepara a base para a modelagem preditiva.

    Exclui os beneficiarios do IPTU Social (RNF01) pela regra formal de
    src/ml/protecao_iptu_social.py e remove identificadores pessoais diretos.

    politica_indefinido:
        "proteger" (padrao) trata indicador nulo/invalido como protegido;
        "erro" interrompe o preparo.
    """

    df = dados.copy()

    # RNF01: exclui os grupos protegidos da base preditiva.
    # A funcao falha se nao houver coluna de IPTU Social na base.
    df, _ = excluir_grupos_protegidos(df, politica=politica_indefinido)

    # Remove identificadores pessoais diretos
    colunas_sensiveis = [
        "cpf_cnpj",
        "nome",
        "contato",
        "logradouro",
        "inscricao_imobiliaria",
    ]

    df = df.drop(columns=colunas_sensiveis, errors="ignore")

    # Remove os indicadores ja utilizados no filtro
    # (o codigo do grupo pode revelar deficiencia: dado sensivel)
    return remover_colunas_de_protecao(df)
