
import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import accuracy_score, f1_score

from src.ml.divisao_temporal import dividir_temporal


# 1. Carrega o historico sintetico
df = pd.read_csv(
    "data/tratado/historico_temporal_sintetico.csv",
    parse_dates=[
        "data_referencia_simulada",
        "data_disponibilidade_alvo"
    ]
)

# 2. Divide cronologicamente
treino, validacao, teste = dividir_temporal(
    df,
    coluna_data="data_referencia_simulada"
)

print("Treino:", len(treino))
print("Validacao:", len(validacao))
print("Teste:", len(teste))

# 3. Confere disponibilidade dos resultados
assert (
    treino["data_disponibilidade_alvo"].max()
    <= validacao["data_referencia_simulada"].min()
)

assert (
    validacao["data_disponibilidade_alvo"].max()
    <= teste["data_referencia_simulada"].min()
)

# 4. Define somente atributos preditivos permitidos
numericas = [
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

categoricas = [
    "tipo_imovel",
    "setor_urbano"
]

atributos = numericas + categoricas
alvo = "inadimplente_proximo_periodo"

# IDs, datas futuras, faixa de renda e resultados
# de outros periodos nao entram como preditores.
X_treino = treino[atributos]
y_treino = treino[alvo]

X_validacao = validacao[atributos]
y_validacao = validacao[alvo]

X_teste = teste[atributos]
y_teste = teste[alvo]

# 5. Define os dois modelos baseline
modelos = {
    "Regressao Logistica": LogisticRegression(
        max_iter=2000,
        random_state=42
    ),
    "Arvore de Decisao": DecisionTreeClassifier(
        max_depth=6,
        random_state=42
    )
}

Path("models").mkdir(exist_ok=True)
resultados = {}

# 6. Treina e avalia cada modelo
for nome, classificador in modelos.items():

    preparo = ColumnTransformer([
        ("numericas", StandardScaler(), numericas),
        (
            "categoricas",
            OneHotEncoder(handle_unknown="ignore"),
            categoricas
        )
    ])

    pipeline = Pipeline([
        ("preparo", preparo),
        ("modelo", classificador)
    ])

    # Ajusta o preprocessamento e o modelo
    # exclusivamente com os dados de treino
    pipeline.fit(X_treino, y_treino)

    metricas = {}

    for etapa, X, y in [
        ("validacao", X_validacao, y_validacao),
        ("teste", X_teste, y_teste)
    ]:
        previsoes = pipeline.predict(X)

        metricas[etapa] = {
            "acuracia": round(
                float(accuracy_score(y, previsoes)), 4
            ),
            "f1_score": round(
                float(f1_score(y, previsoes, zero_division=0)),
                4
            )
        }

    resultados[nome] = metricas

    print(f"\n{nome}")
    print(metricas)

    arquivo = (
        "regressao_logistica_temporal.joblib"
        if nome == "Regressao Logistica"
        else "arvore_decisao_temporal.joblib"
    )

    joblib.dump(pipeline, Path("models") / arquivo)

# 7. Salva as metricas
with open(
    "models/metricas_baselines_temporais.json",
    "w",
    encoding="utf-8"
) as arquivo:
    json.dump(
        resultados,
        arquivo,
        indent=2,
        ensure_ascii=False
    )

print("\nBaselines temporais executados com sucesso!")
