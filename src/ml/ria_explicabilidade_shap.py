import json
from pathlib import Path
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

RAIZ = Path(__file__).resolve().parents[2]
ARQ_MODELO = RAIZ / 'models' / 'modelo_campeao_recuperabilidade.joblib'
ARQ_CARTEIRA = RAIZ / 'data' / 'processado' / 'carteira_teste_escorada.csv'
ARQ_METADADOS = RAIZ / 'models' / 'metadados_modelo_campeao.json'
DIR_FIGURAS = RAIZ / 'docs' / 'figuras'
ARQ_SAIDA_JSON = RAIZ / 'models' / 'ria_explicabilidade_shap.json'


def main():
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    meta = json.loads(ARQ_METADADOS.read_text(encoding='utf-8'))
    limiar = float(meta['limiar_decisao_f1'])

    pipeline = joblib.load(ARQ_MODELO)
    preprocessador = pipeline.named_steps[list(pipeline.named_steps.keys())[0]]
    classificador = pipeline.named_steps[list(pipeline.named_steps.keys())[-1]]

    df = pd.read_csv(ARQ_CARTEIRA, sep=';', encoding='utf-8-sig')
    colunas_modelo = list(preprocessador.feature_names_in_)
    X = df[colunas_modelo].copy()

    X_trans = preprocessador.transform(X)
    if hasattr(X_trans, 'toarray'):
        X_trans = X_trans.toarray()

    nomes_features = [
        n.replace('num__', '').replace('cat__', '')
        for n in preprocessador.get_feature_names_out()
    ]

    amostra_bg = shap.sample(X_trans, min(1000, len(X_trans)), random_state=42)
    explainer = shap.LinearExplainer(classificador, amostra_bg)
    shap_values = explainer.shap_values(X_trans)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    # 1. Importancia Global (media absoluta dos valores SHAP)
    imp_media = np.abs(shap_values).mean(axis=0)
    idx_top = np.argsort(imp_media)[::-1][:12]
    top_globais = [
        {'feature': nomes_features[i], 'shap_medio_abs': round(float(imp_media[i]), 4)}
        for i in idx_top
    ]

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    nomes_plot = [nomes_features[i] for i in idx_top][::-1]
    vals_plot = [imp_media[i] for i in idx_top][::-1]
    ax.barh(nomes_plot, vals_plot, color='#2b5c8f')
    ax.set_xlabel('Impacto Medio Absoluto na Predicao (|SHAP|)')
    ax.set_title('Importancia Global das Variaveis - Regressao Logistica Temporal')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(DIR_FIGURAS / 'ria_shap_global.png', dpi=200)
    plt.close(fig)

    # 2. Caso Individual Real (Art. 20 LGPD - contribuinte acima do limiar)
    candidatos = df.index[df['prob_inadimplencia'] >= max(limiar + 0.15, 0.45)].tolist()
    idx_caso = candidatos[0] if candidatos else int(df['prob_inadimplencia'].idxmax())

    sv_caso = shap_values[idx_caso]
    ordem_local = np.argsort(np.abs(sv_caso))[::-1][:10]
    fatores_locais = [
        {
            'feature': nomes_features[i],
            'valor_transformado': round(float(X_trans[idx_caso, i]), 4),
            'contribuicao_shap': round(float(sv_caso[i]), 4),
            'direcao': 'Aumenta risco' if sv_caso[i] > 0 else 'Reduz risco',
        }
        for i in ordem_local
    ]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    nomes_loc = [nomes_features[i] for i in ordem_local][::-1]
    vals_loc = [sv_caso[i] for i in ordem_local][::-1]
    cores = ['#d95f02' if v > 0 else '#1b9e77' for v in vals_loc]
    ax.barh(nomes_loc, vals_loc, color=cores)
    ax.axvline(0, color='#333333', linewidth=0.9)
    ax.set_xlabel('Contribuicao SHAP (Log-Odds de Inadimplencia)')
    ax.set_title(f'Explicacao Individual (Art. 20 LGPD) - Registro #{idx_caso}')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    fig.tight_layout()
    fig.savefig(DIR_FIGURAS / 'ria_shap_individual.png', dpi=200)
    plt.close(fig)

    dados_brutos_caso = {
        k: (None if pd.isna(v) else (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer, int)) else str(v))))
        for k, v in df.loc[idx_caso, colunas_modelo + ['prob_inadimplencia']].to_dict().items()
    }

    saida = {
        'modelo': meta['modelo_campeao'],
        'limiar_decisao': limiar,
        'valor_base_log_odds': round(float(explainer.expected_value), 4),
        'importancia_global_top12': top_globais,
        'exemplo_individual_art20': {
            'indice_teste': int(idx_caso),
            'dados_entrada': dados_brutos_caso,
            'principais_fatores_shap': fatores_locais,
        },
    }
    ARQ_SAIDA_JSON.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
