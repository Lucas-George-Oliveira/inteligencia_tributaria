from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from src.ml.divisao_temporal import dividir_temporal
from src.ml.protecao_iptu_social import (
    COLUNA_ID,
    COLUNAS_INDICADOR,
    COLUNA_GRUPO,
    carregar_ids_protegidos,
    excluir_grupos_protegidos,
    garantir_sem_protegidos,
    remover_colunas_de_protecao,
    remover_protegidos_da_saida,
)


ATRIBUTOS_NUMERICOS = [
    "area_construida_m2",
    "valor_venal",
    "valor_iptu_anual",
    "distancia_centro_km",
    "exercicios_inadimplentes_5a",
    "tempo_inadimplencia_dias",
    "valor_divida_consolidada",
    "qtd_parcelamentos_anteriores",
    "parcelamento_rompido",
    "qtd_notificacoes"
]
ATRIBUTOS_CATEGORICOS = ["tipo_imovel", "setor_urbano"]


def classificar_estrategia_sefin(score: int, valor_divida: float) -> tuple[str, str]:
    """
    Define a faixa de recuperabilidade e a ação tributária recomendada
    para a Secretaria da Fazenda de Palmas-TO.
    """
    if score >= 750:
        return (
            "Faixa A - Alta Recuperabilidade",
            "Notificação Digital Preventiva (SMS/E-mail/DTE) - Alta propensão de pagamento espontâneo"
        )
    elif score >= 450:
        return (
            "Faixa B - Média Recuperabilidade",
            "Cobrança Administrativa Ativa + Oferta de Parcelamento Ordinário"
        )
    elif score >= 200:
        if valor_divida >= 1500.0:
            return (
                "Faixa C1 - Baixa Recuperabilidade / Alto Valor",
                "Protesto Extrajudicial em Cartório / Priorizar Execução Fiscal"
            )
        return (
            "Faixa C2 - Baixa Recuperabilidade / Baixo Valor",
            "Protesto em Cartório (Evitar ajuizamento pelo custo processual)"
        )
    else:
        return (
            "Faixa D - Crítica / Baixíssima Recuperabilidade",
            "Cobrança Passiva / Elegível para mutirões fiscais (REFIS)"
        )


def gerar_scoring_recuperabilidade(
    df: pd.DataFrame,
    caminho_modelo: str = "models/modelo_campeao_recuperabilidade.joblib",
    ids_protegidos=None,
) -> pd.DataFrame:
    """
    Aplica o modelo campeão e calcula o Score de Recuperabilidade (0 a 1000).

    RNF01: beneficiários do IPTU Social nunca recebem score nem ação.
      - se a base ainda tiver o indicador de IPTU Social, os protegidos são
        excluídos antes da predição;
      - se ``ids_protegidos`` for informado, qualquer ID dessa lista é retirado
        e a saída é conferida antes de ser devolvida.
    """
    if any(c in df.columns for c in (*COLUNAS_INDICADOR, COLUNA_GRUPO)):
        df, _ = excluir_grupos_protegidos(df)
        df = remover_colunas_de_protecao(df)
    if ids_protegidos is not None and COLUNA_ID in df.columns:
        df, _ = remover_protegidos_da_saida(df, ids_protegidos)

    modelo = joblib.load(caminho_modelo)
    X = df[ATRIBUTOS_NUMERICOS + ATRIBUTOS_CATEGORICOS]

    # Alvo original: 1 = inadimplente_proximo_periodo.
    # Recuperabilidade = 1 - P(inadimplente_proximo_periodo).
    prob_inadimplencia = modelo.predict_proba(X)[:, 1]
    prob_recuperacao = 1.0 - prob_inadimplencia
    scores = np.round(prob_recuperacao * 1000).astype(int)

    resultado = df.copy()
    resultado["prob_inadimplencia"] = np.round(prob_inadimplencia, 4)
    resultado["prob_recuperabilidade"] = np.round(prob_recuperacao, 4)
    resultado["score_recuperabilidade"] = scores

    estrategias = [
        classificar_estrategia_sefin(s, v)
        for s, v in zip(scores, resultado["valor_divida_consolidada"])
    ]
    resultado["faixa_recuperabilidade"] = [e[0] for e in estrategias]
    resultado["acao_recomendada_sefin"] = [e[1] for e in estrategias]

    # Índice de prioridade: combina chance de pagar com o valor financeiro da dívida
    resultado["retorno_esperado_estimado"] = np.round(
        resultado["prob_recuperabilidade"] * resultado["valor_divida_consolidada"], 2
    )

    resultado = resultado.sort_values(by="retorno_esperado_estimado", ascending=False)

    if ids_protegidos is not None and COLUNA_ID in resultado.columns:
        garantir_sem_protegidos(resultado, ids_protegidos)

    return resultado


if __name__ == "__main__":
    df = pd.read_csv(
        "data/tratado/historico_temporal_sintetico.csv",
        parse_dates=["data_referencia_simulada", "data_disponibilidade_alvo"]
    )
    _, _, teste = dividir_temporal(df, coluna_data="data_referencia_simulada")

    # RNF01: IDs protegidos lidos do cadastro bruto (que ainda tem o indicador)
    protegidos = carregar_ids_protegidos()
    carteira_escorada = gerar_scoring_recuperabilidade(teste, ids_protegidos=protegidos)

    Path("data/processado").mkdir(parents=True, exist_ok=True)
    carteira_escorada.to_csv(
        "data/processado/carteira_teste_escorada.csv",
        sep=";",
        index=False
    )

    print("\nDistribuição por Faixa de Recuperabilidade (Período de Teste):")
    print(carteira_escorada["faixa_recuperabilidade"].value_counts())
    print("\nTop 5 contribuintes prioritários (Maior Retorno Esperado):")
    print(
        carteira_escorada[
            [
                "valor_divida_consolidada",
                "score_recuperabilidade",
                "retorno_esperado_estimado",
                "faixa_recuperabilidade"
            ]
        ].head()
    )