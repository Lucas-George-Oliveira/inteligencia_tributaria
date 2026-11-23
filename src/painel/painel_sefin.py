"""
Painel Sefin — MVP da Sprint 4 (E4)

Painel interativo para o analista da Sefin Palmas:
  1. ranking de devedores por score de recuperabilidade;
  2. mapa de calor de inadimplência por setor urbano;
  3. projeção de arrecadação potencial;
  4. simulador que aplica o modelo serializado em /models a um contribuinte;
  5. métricas do modelo, inclusive por subgrupo (insumo da Sprint 5).

Como rodar (na raiz do repositório):
    streamlit run src/painel/painel_sefin.py

Fontes (geradas pelo pipeline da Sprint 4, não editadas à mão):
  - data/processado/carteira_teste_escorada.csv  (saída de src/ml/scoring_recuperabilidade.py)
  - models/modelo_campeao_recuperabilidade.joblib e models/metadados_modelo_campeao.json

ATENÇÃO: a camada individual do dado é SINTÉTICA. Os números demonstram que o
pipeline funciona de ponta a ponta, não que o modelo funciona no mundo real.
"""

import json
import sys
from pathlib import Path

import altair as alt
import joblib
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:  # permite importar src.ml rodando via "streamlit run"
    sys.path.insert(0, str(RAIZ))

from src.ml.scoring_recuperabilidade import (  # noqa: E402
    ATRIBUTOS_CATEGORICOS,
    ATRIBUTOS_NUMERICOS,
    classificar_estrategia_sefin,
)
from src.ml.protecao_iptu_social import (  # noqa: E402
    FUNDAMENTO_LEGAL,
    carregar_ids_protegidos,
    remover_protegidos_da_saida,
)

ARQ_CARTEIRA = RAIZ / "data" / "processado" / "carteira_teste_escorada.csv"
ARQ_MODELO = RAIZ / "models" / "modelo_campeao_recuperabilidade.joblib"
ARQ_METADADOS = RAIZ / "models" / "metadados_modelo_campeao.json"
# Cadastro com o indicador de IPTU Social, usado só para a trava do RNF01
ARQ_CADASTRO = RAIZ / "data" / "bruto" / "carteira_contribuintes_sintetica.csv"

# Posição APROXIMADA do centro de cada região urbana de Palmas (WGS84).
# Serve só para posicionar os círculos no mapa; não é a localização de imóveis.
COORD_SETORES = {
    "Plano Diretor Norte": (-10.160, -48.328),
    "Setor Comercial Central": (-10.185, -48.334),
    "Plano Diretor Sul": (-10.220, -48.330),
    "Taquari": (-10.297, -48.350),
    "Aureny": (-10.298, -48.309),
    "Jardim Aureny IV": (-10.311, -48.294),
    "Taquaralto": (-10.326, -48.305),
    "Area de Expansao": (-10.340, -48.325),
}

# Rampa sequencial azul (claro -> escuro) para magnitude de risco
RAMPA_AZUL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
COR_SERIE = "#2a78d6"

AVISO_SINTETICO = (
    "**Dados sintéticos.** A carteira de contribuintes foi gerada artificialmente pela equipe, "
    "porque a Sefin ainda não disponibilizou a base individual da dívida ativa. Os resultados "
    "demonstram que o pipeline funciona de ponta a ponta, **não** que o modelo funciona no mundo real."
)


# ---------------------------------------------------------------------------
# Carga de dados (funções puras, testadas em tests/test_painel.py)
# ---------------------------------------------------------------------------
def carregar_carteira(caminho: Path = ARQ_CARTEIRA, caminho_cadastro: Path = ARQ_CADASTRO) -> pd.DataFrame:
    """
    Lê a carteira escorada e mantém só a foto mais recente de cada contribuinte.

    RNF01: retira qualquer beneficiário do IPTU Social que tenha chegado à
    carteira, para que ele nunca apareça no ranking, no mapa ou na projeção.
    """
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype={"id_contribuinte": str},
                     parse_dates=["data_referencia_simulada", "data_disponibilidade_alvo"])
    ultima = df["data_referencia_simulada"].max()
    atual = df[df["data_referencia_simulada"] == ultima].copy()
    atual, _ = remover_protegidos_da_saida(atual, carregar_ids_protegidos(caminho_cadastro))
    return atual.drop_duplicates(subset="id_contribuinte").reset_index(drop=True)


def carregar_metadados(caminho: Path = ARQ_METADADOS) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def resumo_por_setor(df: pd.DataFrame, limiar: float) -> pd.DataFrame:
    """Indicadores de inadimplência e arrecadação por setor urbano."""
    tmp = df.assign(previsto_inadimplente=(df["prob_inadimplencia"] >= limiar).astype(int))
    resumo = (tmp.groupby("setor_urbano")
              .agg(contribuintes=("id_contribuinte", "count"),
                   prob_media_inadimplencia=("prob_inadimplencia", "mean"),
                   taxa_prevista=("previsto_inadimplente", "mean"),
                   divida_total=("valor_divida_consolidada", "sum"),
                   arrecadacao_esperada=("retorno_esperado_estimado", "sum"),
                   score_medio=("score_recuperabilidade", "mean"))
              .reset_index())
    resumo["lat"] = resumo["setor_urbano"].map(lambda s: COORD_SETORES.get(s, (np.nan, np.nan))[0])
    resumo["lon"] = resumo["setor_urbano"].map(lambda s: COORD_SETORES.get(s, (np.nan, np.nan))[1])
    return resumo.sort_values("prob_media_inadimplencia", ascending=False).reset_index(drop=True)


def curva_arrecadacao(df: pd.DataFrame) -> pd.DataFrame:
    """Arrecadação esperada acumulada ao acionar os contribuintes em ordem de prioridade."""
    ordenado = df.sort_values("retorno_esperado_estimado", ascending=False).reset_index(drop=True)
    return pd.DataFrame({
        "contribuintes_acionados": np.arange(1, len(ordenado) + 1),
        "arrecadacao_acumulada": ordenado["retorno_esperado_estimado"].cumsum(),
    })


def metricas_por_subgrupo(df: pd.DataFrame, coluna: str, limiar: float) -> pd.DataFrame:
    """Precisão, recall e taxas por subgrupo (ex.: faixa de renda), para a análise de fairness."""
    linhas = []
    for grupo, g in df.groupby(coluna):
        real = g["inadimplente_proximo_periodo"].astype(int)
        prev = (g["prob_inadimplencia"] >= limiar).astype(int)
        vp = int(((prev == 1) & (real == 1)).sum())
        fp = int(((prev == 1) & (real == 0)).sum())
        fn = int(((prev == 0) & (real == 1)).sum())
        linhas.append({
            coluna: grupo,
            "contribuintes": len(g),
            "taxa_real": real.mean(),
            "taxa_prevista": prev.mean(),
            "precisao": vp / (vp + fp) if vp + fp else np.nan,
            "recall": vp / (vp + fn) if vp + fn else np.nan,
            "acuracia": (prev == real).mean(),
        })
    return pd.DataFrame(linhas)


def cor_por_risco(valor: float, minimo: float, maximo: float) -> list:
    """Converte um valor de risco em cor RGB da rampa azul (mais escuro = mais risco)."""
    frac = 0.0 if maximo == minimo else (valor - minimo) / (maximo - minimo)
    hexa = RAMPA_AZUL[min(int(frac * len(RAMPA_AZUL)), len(RAMPA_AZUL) - 1)]
    return [int(hexa[i:i + 2], 16) for i in (1, 3, 5)] + [210]


def brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor: float) -> str:
    return f"{valor:.1%}".replace(".", ",")


def inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def brl_curto(valor: float) -> str:
    """Formato compacto para os indicadores: R$ 61,8 mi / R$ 950,2 mil."""
    for divisor, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if abs(valor) >= divisor:
            return f"R$ {valor / divisor:.1f} {sufixo}".replace(".", ",")
    return brl(valor)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Painel Sefin — Recuperabilidade", page_icon="📊", layout="wide")
    st.title("Painel de Recuperabilidade da Dívida Ativa — Palmas/TO")
    st.caption("Projeto Integrador BIINAR/UFT — Sprint 4 (MVP) · Modelo e scores gerados pelo pipeline em `src/ml/`")
    st.warning(AVISO_SINTETICO, icon="⚠️")

    if not ARQ_CARTEIRA.exists() or not ARQ_MODELO.exists() or not ARQ_CADASTRO.exists():
        st.error("Artefatos do pipeline não encontrados. Execute primeiro o notebook "
                 "`notebooks/modelo_inadimplencia.ipynb` (seção 9) ou `python -m src.ml.scoring_recuperabilidade`.")
        st.stop()

    carteira = st.cache_data(carregar_carteira)()
    meta = carregar_metadados()
    limiar = float(meta.get("limiar_decisao_f1", 0.5))
    data_ref = carteira["data_referencia_simulada"].max().strftime("%m/%Y")

    # ---- Filtros (barra lateral) -------------------------------------------
    st.sidebar.header("Filtros")
    setores = sorted(carteira["setor_urbano"].unique())
    faixas = sorted(carteira["faixa_recuperabilidade"].unique())
    rendas = ["baixa", "media", "alta"]
    sel_setores = st.sidebar.multiselect("Setor urbano", setores, default=setores)
    sel_faixas = st.sidebar.multiselect("Faixa de recuperabilidade", faixas, default=faixas)
    sel_rendas = st.sidebar.multiselect("Faixa de renda do setor", rendas, default=rendas)
    divida_min = st.sidebar.number_input("Dívida mínima (R$)", min_value=0.0, value=0.0, step=500.0)
    st.sidebar.caption(f"Foto da carteira: {data_ref} · {inteiro(len(carteira))} contribuintes")

    df = carteira[carteira["setor_urbano"].isin(sel_setores)
                  & carteira["faixa_recuperabilidade"].isin(sel_faixas)
                  & carteira["faixa_renda_setor"].isin(sel_rendas)
                  & (carteira["valor_divida_consolidada"] >= divida_min)]
    if df.empty:
        st.info("Nenhum contribuinte com esses filtros.")
        st.stop()

    # ---- Indicadores ------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contribuintes", inteiro(len(df)))
    c2.metric("Dívida consolidada", brl_curto(df["valor_divida_consolidada"].sum()))
    c3.metric("Arrecadação potencial esperada", brl_curto(df["retorno_esperado_estimado"].sum()),
              help="Soma de P(recuperação) × dívida de cada contribuinte.")
    c4.metric("Score médio", f"{df['score_recuperabilidade'].mean():.0f} / 1000")

    aba_rank, aba_mapa, aba_proj, aba_sim, aba_met = st.tabs(
        ["🏆 Ranking", "🗺️ Mapa por setor", "💰 Projeção de arrecadação", "🧮 Simulador", "📈 Métricas do modelo"])

    # ---- 1. Ranking -------------------------------------------------------
    with aba_rank:
        st.subheader("Ranking de devedores por prioridade de cobrança")
        criterio = st.radio("Ordenar por", ["Retorno esperado (R$)", "Score de recuperabilidade"], horizontal=True)
        col_ord = "retorno_esperado_estimado" if criterio.startswith("Retorno") else "score_recuperabilidade"
        top_n = st.slider("Quantos contribuintes mostrar", 10, 500, 50, step=10)
        ranking = (df.sort_values(col_ord, ascending=False).head(top_n)
                   [["id_contribuinte", "setor_urbano", "tipo_imovel", "valor_divida_consolidada",
                     "score_recuperabilidade", "prob_recuperabilidade", "retorno_esperado_estimado",
                     "faixa_recuperabilidade", "acao_recomendada_sefin"]]
                   .reset_index(drop=True))
        ranking.index = ranking.index + 1
        st.dataframe(ranking, use_container_width=True, column_config={
            "id_contribuinte": st.column_config.TextColumn("ID (pseudonimizado)"),
            "setor_urbano": "Setor",
            "tipo_imovel": "Imóvel",
            "valor_divida_consolidada": st.column_config.NumberColumn("Dívida (R$)", format="%.2f"),
            "score_recuperabilidade": st.column_config.ProgressColumn("Score", min_value=0, max_value=1000, format="%d"),
            "prob_recuperabilidade": st.column_config.NumberColumn("P(recuperar)", format="%.2f"),
            "retorno_esperado_estimado": st.column_config.NumberColumn("Retorno esperado (R$)", format="%.2f"),
            "faixa_recuperabilidade": "Faixa",
            "acao_recomendada_sefin": "Ação recomendada",
        })
        st.download_button("Baixar ranking (CSV)", ranking.to_csv(sep=";", index_label="posicao").encode("utf-8-sig"),
                           file_name="ranking_recuperabilidade.csv", mime="text/csv")
        st.caption("Os IDs são hashes: nenhum CPF/CNPJ é exibido (LGPD). "
                   "Beneficiários do IPTU Social não aparecem no ranking (RNF01).")

    # ---- 2. Mapa de calor por setor --------------------------------------
    with aba_mapa:
        st.subheader("Inadimplência prevista por setor urbano")
        setor = resumo_por_setor(df, limiar)
        mn, mx = setor["prob_media_inadimplencia"].min(), setor["prob_media_inadimplencia"].max()
        setor["cor"] = setor["prob_media_inadimplencia"].map(lambda v: cor_por_risco(v, mn, mx))
        setor["raio"] = 300 + 900 * np.sqrt(setor["contribuintes"] / setor["contribuintes"].max())
        setor["risco_txt"] = setor["prob_media_inadimplencia"].map(pct)
        setor["divida_txt"] = setor["divida_total"].map(brl)
        camada = pdk.Layer("ScatterplotLayer", data=setor.dropna(subset=["lat"]),
                           get_position="[lon, lat]", get_fill_color="cor", get_radius="raio",
                           pickable=True, stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=2)
        st.pydeck_chart(pdk.Deck(
            layers=[camada],
            initial_view_state=pdk.ViewState(latitude=-10.25, longitude=-48.32, zoom=10.8),
            tooltip={"html": "<b>{setor_urbano}</b><br/>Prob. média de inadimplência: {risco_txt}"
                             "<br/>Contribuintes: {contribuintes}<br/>Dívida: {divida_txt}"},
        ))
        st.caption("Cor: probabilidade média de inadimplência prevista (mais escuro = maior risco). "
                   "Tamanho: número de contribuintes. Posições aproximadas do centro de cada região.")

        col_a, col_b = st.columns(2)
        with col_a:
            barras = alt.Chart(setor).mark_bar(color=COR_SERIE, cornerRadiusEnd=4).encode(
                x=alt.X("prob_media_inadimplencia:Q", title="Prob. média de inadimplência", axis=alt.Axis(format="%")),
                y=alt.Y("setor_urbano:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("setor_urbano:N", title="Setor"),
                         alt.Tooltip("prob_media_inadimplencia:Q", title="Prob. média", format=".1%"),
                         alt.Tooltip("contribuintes:Q", title="Contribuintes")],
            ).properties(height=300, title="Ranking de risco por setor")
            st.altair_chart(barras, use_container_width=True)
        with col_b:
            matriz = df.pivot_table(index="setor_urbano", columns="tipo_imovel",
                                    values="prob_inadimplencia", aggfunc="mean")
            matriz.index.name, matriz.columns.name = "Setor", None
            st.markdown("**Mapa de calor: setor × tipo de imóvel** (prob. média de inadimplência)")
            st.dataframe(matriz.style.format(pct, na_rep="—")
                         .background_gradient(cmap="Blues", axis=None)
                         .highlight_null(color="white"),
                         use_container_width=True)
        pior = setor.iloc[0]
        st.info(f"**Leitura:** o setor com maior risco previsto é **{pior['setor_urbano']}** "
                f"({pct(pior['prob_media_inadimplencia'])} de probabilidade média de inadimplência), "
                f"com {brl(pior['divida_total'])} em dívida. Dados sintéticos: não usar para decisão real.")

    # ---- 3. Projeção de arrecadação --------------------------------------
    with aba_proj:
        st.subheader("Quanto a Sefin pode recuperar priorizando a cobrança?")
        curva = curva_arrecadacao(df)
        total = curva["arrecadacao_acumulada"].iloc[-1]
        capacidade = st.slider("Capacidade de atendimento da equipe (contribuintes acionados)",
                               min_value=100, max_value=len(curva), value=min(1000, len(curva)), step=100)
        alcancado = curva["arrecadacao_acumulada"].iloc[capacidade - 1]
        k1, k2, k3 = st.columns(3)
        k1.metric("Arrecadação esperada com essa capacidade", brl_curto(alcancado))
        k2.metric("% do potencial total", f"{alcancado / total:.0%}")
        k3.metric("% dos contribuintes acionados", f"{capacidade / len(curva):.0%}")

        passo = max(1, len(curva) // 400)  # reduz pontos para o gráfico ficar leve
        linha = alt.Chart(curva.iloc[::passo]).mark_line(color=COR_SERIE, strokeWidth=2).encode(
            x=alt.X("contribuintes_acionados:Q", title="Contribuintes acionados (em ordem de prioridade)"),
            y=alt.Y("arrecadacao_acumulada:Q", title="Arrecadação esperada acumulada (R$)"),
            tooltip=[alt.Tooltip("contribuintes_acionados:Q", title="Acionados"),
                     alt.Tooltip("arrecadacao_acumulada:Q", title="Acumulado (R$)", format=",.0f")],
        )
        marca = alt.Chart(pd.DataFrame({"x": [capacidade]})).mark_rule(color="#888", strokeDash=[4, 4]).encode(x="x:Q")
        st.altair_chart((linha + marca).properties(height=320), use_container_width=True)

        por_acao = (df.groupby("acao_recomendada_sefin")
                    .agg(contribuintes=("id_contribuinte", "count"),
                         divida=("valor_divida_consolidada", "sum"),
                         arrecadacao_esperada=("retorno_esperado_estimado", "sum"))
                    .sort_values("arrecadacao_esperada", ascending=False))
        st.markdown("**Arrecadação esperada por ação recomendada**")
        por_acao = por_acao.rename(columns={"contribuintes": "Contribuintes", "divida": "Dívida",
                                            "arrecadacao_esperada": "Arrecadação esperada"})
        por_acao.index.name = "Ação recomendada"
        st.dataframe(por_acao.style.format({"Contribuintes": inteiro, "Dívida": brl, "Arrecadação esperada": brl}),
                     use_container_width=True)
        st.info(f"**Leitura:** acionando os {inteiro(capacidade)} contribuintes de maior retorno esperado "
                f"({capacidade / len(curva):.0%} da carteira filtrada), a Sefin alcançaria cerca de "
                f"{alcancado / total:.0%} do potencial de recuperação ({brl(alcancado)}). "
                "A projeção é uma estimativa do modelo sobre dados sintéticos.")

    # ---- 4. Simulador -----------------------------------------------------
    with aba_sim:
        st.subheader("Simular o score de um contribuinte")
        st.caption("Aplica ao vivo o modelo serializado em `models/modelo_campeao_recuperabilidade.joblib`.")
        modelo = st.cache_resource(joblib.load)(ARQ_MODELO)
        exemplo = carteira.iloc[0]
        with st.form("simulador"):
            a, b, c = st.columns(3)
            entrada = {
                "setor_urbano": a.selectbox("Setor urbano", setores),
                "tipo_imovel": b.selectbox("Tipo de imóvel", sorted(carteira["tipo_imovel"].unique())),
                "area_construida_m2": c.number_input("Área construída (m²)", 10.0, 5000.0, float(exemplo["area_construida_m2"])),
                "valor_venal": a.number_input("Valor venal (R$)", 1000.0, 1e8, float(exemplo["valor_venal"]), step=1000.0),
                "valor_iptu_anual": b.number_input("IPTU anual (R$)", 0.0, 1e6, float(exemplo["valor_iptu_anual"])),
                "distancia_centro_km": c.number_input("Distância ao centro (km)", 0.0, 60.0, float(exemplo["distancia_centro_km"])),
                "exercicios_inadimplentes_5a": a.slider("Exercícios inadimplentes (5 anos)", 0, 5, int(exemplo["exercicios_inadimplentes_5a"])),
                "tempo_inadimplencia_dias": b.number_input("Tempo de inadimplência (dias)", 0, 5000, int(exemplo["tempo_inadimplencia_dias"])),
                "valor_divida_consolidada": c.number_input("Dívida consolidada (R$)", 0.0, 1e7, float(exemplo["valor_divida_consolidada"])),
                "qtd_parcelamentos_anteriores": a.slider("Parcelamentos anteriores", 0, 10, int(exemplo["qtd_parcelamentos_anteriores"])),
                "parcelamento_rompido": int(b.checkbox("Já rompeu parcelamento", bool(exemplo["parcelamento_rompido"]))),
                "qtd_notificacoes": c.slider("Notificações recebidas", 0, 20, int(exemplo["qtd_notificacoes"])),
            }
            beneficiario = st.checkbox(
                "Beneficiário do IPTU Social (idoso, aposentado, pensionista ou PcD de baixa renda)",
                help=f"Fundamento: {FUNDAMENTO_LEGAL}.")
            enviado = st.form_submit_button("Calcular score")
        if enviado and beneficiario:
            st.info("**Contribuinte protegido pelo IPTU Social (RNF01).** O modelo não é aplicado e "
                    "nenhuma ação preditiva de cobrança é recomendada.")
        elif enviado:
            X = pd.DataFrame([entrada])[ATRIBUTOS_NUMERICOS + ATRIBUTOS_CATEGORICOS]
            p_inad = float(modelo.predict_proba(X)[0, 1])
            score = int(round((1 - p_inad) * 1000))
            faixa, acao = classificar_estrategia_sefin(score, entrada["valor_divida_consolidada"])
            r1, r2, r3 = st.columns(3)
            r1.metric("Score de recuperabilidade", f"{score} / 1000")
            r2.metric("Prob. de inadimplência", pct(p_inad))
            r3.metric("Retorno esperado", brl((1 - p_inad) * entrada["valor_divida_consolidada"]))
            st.success(f"**{faixa}** → {acao}")

    # ---- 5. Métricas ------------------------------------------------------
    with aba_met:
        st.subheader(f"Modelo campeão: {meta.get('modelo_campeao', '—')}")
        m = meta.get("metricas_teste", {})
        cols = st.columns(5)
        for col, (rotulo, chave) in zip(cols, [("Acurácia", "Acuracia_Teste"), ("Precisão", "Precisao_Teste"),
                                               ("Recall", "Recall_Teste"), ("F1", "F1_Teste"), ("ROC AUC", "ROC_AUC_Teste")]):
            col.metric(rotulo, f"{m.get(chave, float('nan')):.3f}".replace(".", ","))
        st.caption(f"Métricas no conjunto de teste (split temporal), limiar de decisão = {limiar}. "
                   "Fonte: `models/metadados_modelo_campeao.json`.")
        st.markdown("**Métricas por subgrupo** (insumo para a análise de fairness da Sprint 5)")
        sub = st.radio("Subgrupo", ["faixa_renda_setor", "setor_urbano"], horizontal=True,
                       format_func={"faixa_renda_setor": "Faixa de renda", "setor_urbano": "Setor urbano"}.get)
        tabela = metricas_por_subgrupo(carteira, sub, limiar).rename(columns={
            sub: "Grupo", "contribuintes": "Contribuintes", "taxa_real": "Inadimplência real",
            "taxa_prevista": "Inadimplência prevista", "precisao": "Precisão", "recall": "Recall",
            "acuracia": "Acurácia"})
        st.dataframe(tabela.style.format({"Contribuintes": inteiro, **{c: pct for c in
                     ["Inadimplência real", "Inadimplência prevista", "Precisão", "Recall", "Acurácia"]}}),
                     use_container_width=True, hide_index=True)
        st.caption("Calculado sobre a foto mais recente da carteira de teste, sem filtros. "
                   "Diferenças grandes de recall entre grupos indicam possível viés a investigar na Sprint 5.")


if __name__ == "__main__":
    main()
