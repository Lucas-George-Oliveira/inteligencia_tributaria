# Portfólio do Projeto Integrador — Inteligência Tributária (Sefin Palmas)

**Curso:** Bacharelado Interdisciplinar em Inteligência Artificial (BIINAR/UFT) — Eixo II (2026/2)  
**Repositório:** `https://github.com/Lucas-George-Oliveira/inteligencia-tributaria`

Este diretório reúne os componentes técnicos, analíticos e de governança ética do sistema de predição de inadimplência e priorização da Dívida Ativa (IPTU/ISS) de Palmas-TO, organizados para avaliação da banca.

## 1. Os Três Componentes Principais + Trava Ética (Sprint 5 — E4)

| Componente | Documento / Código | Descrição e Evidências |
| :--- | :--- | :--- |
| **1. MVP (Painel Interativo)** | [`docs/MVP.md`](MVP.md)<br>[`src/painel/painel_sefin.py`](../src/painel/painel_sefin.py) | Ranking priorizado por retorno esperado, mapa de calor por setor urbano, curva de projeção de arrecadação, simulador ao vivo e métricas por subgrupo (`RF01`, `RF03`, `RF06`). |
| **2. Model Card (E1)** | [`docs/model_card.md`](model_card.md)<br>[`src/ml/model_card_metricas.py`](../src/ml/model_card_metricas.py) | Documentação no padrão Mitchell et al. (2019): detalhes do modelo (`Regressao_Logistica_Temporal`), usos previstos e proibidos, avaliação temporal, sub-representações e auditoria por subgrupo. |
| **3. Relatório de Impacto Algorítmico — RIA (E2)** | [`docs/RIA.md`](RIA.md)<br>[`src/ml/ria_fairness_mitigacao.py`](../src/ml/ria_fairness_mitigacao.py)<br>[`src/ml/ria_explicabilidade_shap.py`](../src/ml/ria_explicabilidade_shap.py) | Mapeamento LGPD e bases legais, auditoria e mitigação de viés via *Fairlearn* (paridade demográfica e igualdade de oportunidade), explicabilidade global/local via SHAP (Art. 20 LGPD) e plano de auditoria contínua. |
| **Proteção IPTU Social (E3 / RNF01)** | [`src/ml/protecao_iptu_social.py`](../src/ml/protecao_iptu_social.py)<br>[`tests/test_iptu_social.py`](../tests/test_iptu_social.py) | Trava determinística *fail-safe* fundamentada na LC nº 285/2013 (art. 20, II), garantindo **0 beneficiários** (idosos, aposentados, pensionistas e PcD de baixa renda) nas ações preditivas de cobrança. |

## 2. Documentação Complementar de Engenharia e Dados

* **Requisitos e Priorização MoSCoW:** [`docs/requisitos.md`](requisitos.md)
* **Arquitetura do Sistema:** [`docs/arquitetura.md`](arquitetura.md)
* **Modelagem de Dados (3FN):** [`docs/DER.md`](DER.md) e [`src/database/schema/`](../src/database/schema/)
* **Pipeline ETL e Coleta Pública:** [`docs/GUIA_ETL_E2.md`](GUIA_ETL_E2.md) e [`docs/relatorio_eda.md`](relatorio_eda.md)

## 3. Guia Rápido de Reprodução

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar testes automatizados (inclui RNF01 / IPTU Social, painel, ETL e modelo)
python -m pytest -v

# 3. Iniciar o painel interativo (MVP)
streamlit run src/painel/painel_sefin.py