import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import recall_score, precision_score, f1_score
from fairlearn.metrics import (
    MetricFrame,
    selection_rate,
    demographic_parity_difference,
    demographic_parity_ratio,
    true_positive_rate_difference,
    false_positive_rate_difference,
)

RAIZ = Path(__file__).resolve().parents[2]
ARQ_CARTEIRA = RAIZ / 'data' / 'processado' / 'carteira_teste_escorada.csv'
ARQ_METADADOS = RAIZ / 'models' / 'metadados_modelo_campeao.json'
DIR_FIGURAS = RAIZ / 'docs' / 'figuras'
ARQ_RELATORIO_JSON = RAIZ / 'models' / 'ria_auditoria_fairness.json'

SUBGRUPOS = ['faixa_renda_setor', 'setor_urbano', 'tipo_imovel']
ALVO = 'inadimplente_proximo_periodo'

def avaliar_fairlearn(y_true, y_pred, grupo):
    metricas = {
        'n': lambda yt, yp: int(len(yt)),
        'taxa_real': lambda yt, yp: float(yt.mean()),
        'paridade_demografica_selecao': selection_rate,
        'igualdade_oportunidade_tpr': recall_score,
        'precisao': lambda yt, yp: precision_score(yt, yp, zero_division=0),
    }
    mf = MetricFrame(metrics=metricas, y_true=y_true, y_pred=y_pred, sensitive_features=grupo)
    return {
        'por_grupo': mf.by_group.round(4).to_dict(orient='index'),
        'disparidades': {
            'razao_paridade_demografica_4_5': round(float(demographic_parity_ratio(y_true, y_pred, sensitive_features=grupo)), 4),
            'diferenca_paridade_demografica': round(float(demographic_parity_difference(y_true, y_pred, sensitive_features=grupo)), 4),
            'diferenca_igualdade_oportunidade_tpr': round(float(true_positive_rate_difference(y_true, y_pred, sensitive_features=grupo)), 4),
            'diferenca_fpr': round(float(false_positive_rate_difference(y_true, y_pred, sensitive_features=grupo)), 4),
        },
    }

def mitigar_igualdade_oportunidade(df, coluna_grupo, limiar_base):
    y_true = df[ALVO].astype(int)
    prob = df['prob_inadimplencia']
    prev_base = (prob >= limiar_base).astype(int)
    tprs_iniciais = {
        g: recall_score(sub[ALVO], (sub['prob_inadimplencia'] >= limiar_base).astype(int))
        for g, sub in df.groupby(coluna_grupo)
    }
    tpr_alvo = max(tprs_iniciais.values())
    limiares_ajustados = {}
    prev_mitigada = prev_base.copy()
    for grupo, sub in df.groupby(coluna_grupo):
        melhor_limiar = limiar_base
        menor_dist = abs(tprs_iniciais[grupo] - tpr_alvo)
        for cand in np.linspace(0.05, 0.60, 111):
            pred_cand = (sub['prob_inadimplencia'] >= cand).astype(int)
            tpr_cand = recall_score(sub[ALVO], pred_cand, zero_division=0)
            dist = abs(tpr_cand - tpr_alvo)
            if dist < menor_dist:
                menor_dist = dist
                melhor_limiar = float(round(cand, 4))
        limiares_ajustados[str(grupo)] = melhor_limiar
        mask = df[coluna_grupo] == grupo
        prev_mitigada.loc[mask] = (df.loc[mask, 'prob_inadimplencia'] >= melhor_limiar).astype(int)
    return prev_mitigada, limiares_ajustados

def salvar_grafico_comparativo(res_antes, res_depois, coluna, caminho):
    grupos = list(res_antes['por_grupo'].keys())
    tpr_antes = [res_antes['por_grupo'][g]['igualdade_oportunidade_tpr'] for g in grupos]
    tpr_depois = [res_depois['por_grupo'][g]['igualdade_oportunidade_tpr'] for g in grupos]
    x = np.arange(len(grupos))
    largura = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.4))
    b1 = ax.bar(x - largura / 2, tpr_antes, width=largura, label='Original (limiar unico)', color='#d95f02')
    b2 = ax.bar(x + largura / 2, tpr_depois, width=largura, label='Mitigado (limiar por grupo)', color='#1b9e77')
    for barras in (b1, b2):
        for b in barras:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, f'{b.get_height():.1%}', ha='center', fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels([str(g).capitalize() for g in grupos], rotation=12)
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel('Igualdade de Oportunidade (Recall / TPR)')
    ax.set_title(f'Mitigacao de Vies (TPR) por {coluna}')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.legend(frameon=False, loc='lower right')
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)

def main():
    meta = json.loads(ARQ_METADADOS.read_text(encoding='utf-8'))
    limiar_base = float(meta['limiar_decisao_f1'])
    df = pd.read_csv(ARQ_CARTEIRA, sep=';', encoding='utf-8-sig')
    y_true = df[ALVO].astype(int)
    y_pred_base = (df['prob_inadimplencia'] >= limiar_base).astype(int)
    auditoria = {
        'modelo': meta['modelo_campeao'],
        'limiar_original': limiar_base,
        'f1_global_original': round(float(f1_score(y_true, y_pred_base)), 4),
        'analise_por_subgrupo': {},
    }
    for coluna in SUBGRUPOS:
        res_antes = avaliar_fairlearn(y_true, y_pred_base, df[coluna])
        y_pred_mitigado, limiares_novos = mitigar_igualdade_oportunidade(df, coluna, limiar_base)
        res_depois = avaliar_fairlearn(y_true, y_pred_mitigado, df[coluna])
        auditoria['analise_por_subgrupo'][coluna] = {
            'antes_mitigacao': res_antes,
            'depois_mitigacao': {
                **res_depois,
                'limiares_ajustados': limiares_novos,
                'f1_global_pos_mitigacao': round(float(f1_score(y_true, y_pred_mitigado)), 4),
            },
        }
        fig_path = DIR_FIGURAS / f'ria_mitigacao_{coluna}.png'
        salvar_grafico_comparativo(res_antes, res_depois, coluna, fig_path)
    ARQ_RELATORIO_JSON.write_text(json.dumps(auditoria, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Concluido com sucesso!')

if __name__ == '__main__':
    main()
