
import json
from pathlib import Path

import joblib
import pandas as pd

from src.ml.preparar_base import preparar_base

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import accuracy_score, f1_score

# Carrega a base sintetica original
caminho = "data/bruto/carteira_contribuintes_sintetica.csv"
df_original = pd.read_csv(caminho, sep=";")

# Aplica o tratamento e a exclusao do IPTU Social
df = preparar_base(df_original)

print("Registros originais:", len(df_original))
print("Registros preparados:", len(df))
print("Beneficiarios excluidos:", len(df_original) - len(df))

# Variável que queremos prever
alvo = "inadimplente_proximo_exercicio"

# Atributos disponíveis antes do resultado previsto
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

categoricas = ["tipo_imovel", "setor_urbano"]

# Não utilizamos IDs, grupo protegido, isenção
# ou o resultado futuro de recuperação como preditores.
X = df[numericas + categoricas]
y = df[alvo]

# Divisão aleatória apenas para diagnóstico dos baselines
X_temp, X_teste, y_temp, y_teste = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

X_treino, X_valid, y_treino, y_valid = train_test_split(
    X_temp, y_temp, test_size=0.25,
    random_state=42, stratify=y_temp
)

print("Treino:", len(X_treino))
print("Validação:", len(X_valid))
print("Teste:", len(X_teste))

modelos = {
    "Regressão Logística": LogisticRegression(max_iter=2000),
    "Árvore de Decisão": DecisionTreeClassifier(
        max_depth=6, random_state=42
    )
}

Path("models").mkdir(exist_ok=True)
resultados = {}

for nome, classificador in modelos.items():

    preparo = ColumnTransformer([
        ("numericas", StandardScaler(), numericas),
        ("categoricas", OneHotEncoder(handle_unknown="ignore"), categoricas)
    ])

    pipeline = Pipeline([
        ("preparo", preparo),
        ("modelo", classificador)
    ])

    pipeline.fit(X_treino, y_treino)

    metricas = {}

    for etapa, X_eval, y_eval in [
        ("validacao", X_valid, y_valid),
        ("teste", X_teste, y_teste)
    ]:
        previsoes = pipeline.predict(X_eval)
        metricas[etapa] = {
            "acuracia": round(float(accuracy_score(y_eval, previsoes)), 4),
            "f1_score": round(float(f1_score(y_eval, previsoes)), 4)
        }

    resultados[nome] = metricas

    print(f"\n{nome}")
    print(metricas)

    arquivo = (
        "regressao_logistica.joblib"
        if nome == "Regressão Logística"
        else "arvore_decisao.joblib"
    )
    joblib.dump(pipeline, Path("models") / arquivo)

with open("models/metricas_baselines.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print("\nBaselines executados com sucesso!")
