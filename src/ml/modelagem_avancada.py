import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import PredefinedSplit, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.ml.divisao_temporal import dividir_temporal


def calcular_ks(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Calcula a estatística Kolmogorov-Smirnov (KS) para credit/collection scoring."""
    prob_classe_1 = y_prob[y_true == 1]
    prob_classe_0 = y_prob[y_true == 0]
    if len(prob_classe_1) == 0 or len(prob_classe_0) == 0:
        return 0.0
    return float(ks_2samp(prob_classe_1, prob_classe_0).statistic)


def executar_modelagem_avancada():
    # 1. Carrega o histórico temporal sintético (mesma base dos baselines temporais)
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

    # 3. Confere disponibilidade dos resultados (previne vazamento temporal)
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
    categoricas = ["tipo_imovel", "setor_urbano"]
    atributos = numericas + categoricas
    alvo = "inadimplente_proximo_periodo"

    X_treino, y_treino = treino[atributos], treino[alvo]
    X_validacao, y_validacao = validacao[atributos], validacao[alvo]
    X_teste, y_teste = teste[atributos], teste[alvo]

    # Prepara PredefinedSplit para tunar hiperparâmetros respeitando a ordem temporal
    X_tuning = pd.concat([X_treino, X_validacao], axis=0)
    y_tuning = pd.concat([y_treino, y_validacao], axis=0)
    split_index = np.concatenate([
        np.full(len(X_treino), -1),
        np.zeros(len(X_validacao))
    ])
    validacao_temporal = PredefinedSplit(test_fold=split_index)

    candidatos = {
        "RandomForest_Temporal_Tunado": {
            "estimador": RandomForestClassifier(
                random_state=42,
                class_weight="balanced",
                n_jobs=-1
            ),
            "params": {
                "modelo__n_estimators": [150, 250, 350],
                "modelo__max_depth": [6, 10, 14],
                "modelo__min_samples_split": [5, 10, 20],
                "modelo__min_samples_leaf": [2, 5, 10]
            }
        },
        "GradientBoosting_Temporal_Tunado": {
            "estimador": GradientBoostingClassifier(random_state=42),
            "params": {
                "modelo__n_estimators": [150, 250, 350],
                "modelo__learning_rate": [0.03, 0.05, 0.1],
                "modelo__max_depth": [3, 4, 6],
                "modelo__subsample": [0.8, 1.0]
            }
        }
    }

    Path("models").mkdir(exist_ok=True)
    resultados = {}
    melhor_auc = -1.0
    melhor_modelo = None
    melhor_nome = ""

    for nome, cfg in candidatos.items():
        print(f"\n--- Executando Tunagem Temporal: {nome} ---")
        preparo = ColumnTransformer([
            ("numericas", StandardScaler(), numericas),
            ("categoricas", OneHotEncoder(handle_unknown="ignore"), categoricas)
        ])

        pipeline = Pipeline([
            ("preparo", preparo),
            ("modelo", cfg["estimador"])
        ])

        busca = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=cfg["params"],
            n_iter=10,
            scoring="roc_auc",
            cv=validacao_temporal,
            random_state=42,
            n_jobs=-1
        )
        busca.fit(X_tuning, y_tuning)

        # Reajusta o melhor pipeline apenas no treino e calibra usando a validação temporal
        melhor_pipeline = busca.best_estimator_
        melhor_pipeline.fit(X_treino, y_treino)

        modelo_calibrado = CalibratedClassifierCV(
            estimator=melhor_pipeline,
            method="sigmoid",
            cv="prefit"
        )
        modelo_calibrado.fit(X_validacao, y_validacao)

        metricas = {"melhores_hiperparametros": busca.best_params_}

        for etapa, X_eval, y_eval in [
            ("validacao", X_validacao, y_validacao),
            ("teste", X_teste, y_teste)
        ]:
            previsoes = modelo_calibrado.predict(X_eval)
            probs = modelo_calibrado.predict_proba(X_eval)[:, 1]

            metricas[etapa] = {
                "acuracia": round(float(accuracy_score(y_eval, previsoes)), 4),
                "f1_score": round(float(f1_score(y_eval, previsoes, zero_division=0)), 4),
                "roc_auc": round(float(roc_auc_score(y_eval, probs)), 4),
                "ks": round(calcular_ks(y_eval.values, probs), 4)
            }

        resultados[nome] = metricas
        print(json.dumps(metricas, indent=2, ensure_ascii=False))

        joblib.dump(modelo_calibrado, Path("models") / f"{nome.lower()}.joblib")

        if metricas["teste"]["roc_auc"] > melhor_auc:
            melhor_auc = metricas["teste"]["roc_auc"]
            melhor_modelo = modelo_calibrado
            melhor_nome = nome

    joblib.dump(melhor_modelo, Path("models") / "modelo_campeao_recuperabilidade.joblib")
    resultados["modelo_campeao"] = melhor_nome

    with open("models/metricas_modelagem_avancada.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\nModelagem avançada concluída! Campeão: {melhor_nome} (ROC-AUC Teste: {melhor_auc})")


if __name__ == "__main__":
    executar_modelagem_avancada()