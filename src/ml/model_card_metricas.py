"""
Métricas por subgrupo para o Model Card (Sprint 5 — E1).

Lê a carteira de teste escorada pelo modelo campeão e calcula, para cada
subgrupo (faixa de renda do setor, setor urbano e tipo de imóvel):
  - taxa real de inadimplência (base rate);
  - taxa de seleção (quantos o modelo sinaliza)  -> paridade demográfica;
  - taxa de verdadeiros positivos (recall/TPR)    -> igualdade de oportunidade;
  - taxa de falsos positivos (FPR), precisão e ROC AUC.

Como rodar (na raiz do repositório):
    python -m src.ml.model_card_metricas

Saídas:
    models/metricas_subgrupos.json
    docs/figuras/mc_taxas_por_renda.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ARQ_CARTEIRA = RAIZ / "data" / "processado" / "carteira_teste_escorada.csv"
ARQ_METADADOS = RAIZ / "models" / "metadados_modelo_campeao.json"
ARQ_SAIDA = RAIZ / "models" / "metricas_subgrupos.json"
ARQ_FIGURA = RAIZ / "docs" / "figuras" / "mc_taxas_por_renda.png"

SUBGRUPOS = ["faixa_renda_setor", "setor_urbano", "tipo_imovel"]
ALVO = "inadimplente_proximo_periodo"


def metricas_grupo(y_real: pd.Series, prob: pd.Series, limiar: float) -> dict:
    """Métricas de classificação e de fairness para um grupo."""
    y_real = y_real.astype(int)
    prev = (prob >= limiar).astype(int)
    positivos, negativos = y_real == 1, y_real == 0
    return {
        "n": int(len(y_real)),
        "taxa_real": float(y_real.mean()),
        "taxa_selecao": float(prev.mean()),
        "tpr_recall": float(prev[positivos].mean()) if positivos.any() else None,
        "fpr": float(prev[negativos].mean()) if negativos.any() else None,
        "precisao": float(y_real[prev == 1].mean()) if (prev == 1).any() else None,
        "roc_auc": float(roc_auc_score(y_real, prob)) if y_real.nunique() == 2 else None,
    }


def tabela_subgrupo(df: pd.DataFrame, coluna: str, limiar: float) -> pd.DataFrame:
    linhas = [{"grupo": g, **metricas_grupo(x[ALVO], x["prob_inadimplencia"], limiar)}
              for g, x in df.groupby(coluna)]
    return pd.DataFrame(linhas)


def resumo_fairness(tabela: pd.DataFrame) -> dict:
    """
    Paridade demográfica: menor taxa de seleção ÷ maior (regra dos 4/5: < 0,8 indica disparidade).
    Igualdade de oportunidade: maior diferença de TPR entre grupos.
    """
    sel, tpr, fpr = tabela["taxa_selecao"], tabela["tpr_recall"], tabela["fpr"]
    return {
        "razao_paridade_demografica": float(sel.min() / sel.max()),
        "diferenca_taxa_selecao": float(sel.max() - sel.min()),
        "diferenca_igualdade_oportunidade_tpr": float(tpr.max() - tpr.min()),
        "diferenca_fpr": float(fpr.max() - fpr.min()),
        "diferenca_taxa_real": float(tabela["taxa_real"].max() - tabela["taxa_real"].min()),
    }


def grafico_renda(tabela: pd.DataFrame, caminho: Path) -> None:
    ordem = ["baixa", "media", "alta"]
    t = tabela.set_index("grupo").reindex(ordem)
    x = range(len(ordem))
    largura = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    series = [("taxa_real", "Inadimplência real", "#2a78d6", -largura / 2),
              ("taxa_selecao", "Sinalizados pelo modelo", "#eb6834", largura / 2)]
    for coluna, rotulo, cor, desloc in series:
        barras = ax.bar([i + desloc for i in x], t[coluna], width=largura - 0.03,
                        color=cor, label=rotulo)
        for b in barras:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                    f"{b.get_height():.0%}", ha="center", fontsize=9, color="#333")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["Baixa renda", "Média renda", "Alta renda"])
    ax.set_ylim(0, 0.85)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel("% dos contribuintes")
    ax.set_title("Inadimplência real x sinalizada pelo modelo, por faixa de renda do setor")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e5")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.01, -0.02, "Conjunto de teste (out–dez/2024, dados sintéticos), limiar de decisão 0,23.",
             fontsize=8, color="#555")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, bbox_inches="tight", dpi=130)
    plt.close(fig)


def main() -> dict:
    meta = json.loads(ARQ_METADADOS.read_text(encoding="utf-8"))
    limiar = float(meta["limiar_decisao_f1"])
    df = pd.read_csv(ARQ_CARTEIRA, sep=";", encoding="utf-8-sig")

    resultado = {
        "modelo": meta["modelo_campeao"],
        "limiar_decisao": limiar,
        "conjunto": "teste (split temporal)",
        "periodos_teste": sorted(df["data_referencia_simulada"].astype(str).unique().tolist()),
        "registros_teste": int(len(df)),
        "geral": metricas_grupo(df[ALVO], df["prob_inadimplencia"], limiar),
        "subgrupos": {},
    }
    for coluna in SUBGRUPOS:
        tab = tabela_subgrupo(df, coluna, limiar)
        resultado["subgrupos"][coluna] = {
            "metricas": tab.round(4).to_dict(orient="records"),
            "fairness": {k: round(v, 4) for k, v in resumo_fairness(tab).items()},
        }
        if coluna == "faixa_renda_setor":
            grafico_renda(tab, ARQ_FIGURA)

    ARQ_SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Métricas por subgrupo salvas em", ARQ_SAIDA.relative_to(RAIZ))
    print("Figura salva em", ARQ_FIGURA.relative_to(RAIZ))
    for coluna in SUBGRUPOS:
        f = resultado["subgrupos"][coluna]["fairness"]
        print(f"  {coluna}: paridade demográfica = {f['razao_paridade_demografica']:.2f} | "
              f"diferença de TPR = {f['diferenca_igualdade_oportunidade_tpr']:.3f}")
    return resultado


if __name__ == "__main__":
    main()
