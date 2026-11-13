
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

from src.ml.divisao_temporal import dividir_temporal

# Carrega o historico sintetico
df = pd.read_csv(
    "data/tratado/historico_temporal_sintetico.csv",
    parse_dates=[
        "data_referencia_simulada",
        "data_disponibilidade_alvo"
    ]
)

# Divide os dados cronologicamente
treino, validacao, teste = dividir_temporal(
    df,
    coluna_data="data_referencia_simulada"
)

# Garante a disponibilidade dos resultados
assert (
    treino["data_disponibilidade_alvo"].max()
    <= validacao["data_referencia_simulada"].min()
)
assert (
    validacao["data_disponibilidade_alvo"].max()
    <= teste["data_referencia_simulada"].min()
)

# Apenas atributos preditivos permitidos
atributos = [
    "area_construida_m2",
    "valor_venal",
    "valor_iptu_anual",
    "distancia_centro_km",
    "exercicios_inadimplentes_5a",
    "tempo_inadimplencia_dias",
    "valor_divida_consolidada",
    "qtd_parcelamentos_anteriores",
    "parcelamento_rompido",
    "qtd_notificacoes",
    "tipo_imovel",
    "setor_urbano"
]

alvo = "inadimplente_proximo_periodo"

modelos = {
    "Regressao Logistica":
        "models/regressao_logistica_temporal.joblib",
    "Arvore de Decisao":
        "models/arvore_decisao_temporal.joblib"
}

resultados = {}

for nome, caminho in modelos.items():
    modelo = joblib.load(caminho)

    # Escolhe o limite usando somente a validacao
    probabilidades_validacao = modelo.predict_proba(
        validacao[atributos]
    )[:, 1]

    limites = np.round(
        np.arange(0.05, 0.51, 0.01), 2
    )

    pontuacoes = [
        f1_score(
            validacao[alvo],
            probabilidades_validacao >= limite,
            zero_division=0
        )
        for limite in limites
    ]

    indice = int(np.argmax(pontuacoes))
    melhor_limite = float(limites[indice])

    # Aplica o limite escolhido ao teste
    probabilidades_teste = modelo.predict_proba(
        teste[atributos]
    )[:, 1]

    previsoes = (
        probabilidades_teste >= melhor_limite
    ).astype(int)

    y_teste = teste[alvo]

    resultados[nome] = {
        "limite_selecionado": melhor_limite,
        "f1_validacao": round(
            float(pontuacoes[indice]), 4
        ),
        "teste": {
            "acuracia": round(
                accuracy_score(y_teste, previsoes), 4
            ),
            "precisao": round(
                precision_score(
                    y_teste, previsoes,
                    zero_division=0
                ), 4
            ),
            "recall": round(
                recall_score(
                    y_teste, previsoes,
                    zero_division=0
                ), 4
            ),
            "f1_score": round(
                f1_score(
                    y_teste, previsoes,
                    zero_division=0
                ), 4
            ),
            "matriz_confusao": confusion_matrix(
                y_teste, previsoes
            ).tolist()
        }
    }

    print(f"\n{nome}")
    print(resultados[nome])

# Salva os resultados sem sobrescrever
# as metricas originais dos baselines
Path("models").mkdir(exist_ok=True)

with open(
    "models/metricas_limites_temporais.json",
    "w",
    encoding="utf-8"
) as arquivo:
    json.dump(
        resultados,
        arquivo,
        indent=2,
        ensure_ascii=False
    )

print("\nResultados ajustados salvos com sucesso!")
