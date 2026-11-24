# Arquitetura do Sistema — Inteligência Tributária (Sefin Palmas)

**Projeto Integrador — BIINAR/UFT | Eixo II (2026/2)**

## 1. Visão Geral em Camadas

O sistema foi estruturado em cinco camadas desacopladas, cobrindo desde a ingestão de dados públicos e cadastrais até a priorização auditável da dívida ativa de Palmas-TO:

```text
[Fontes de Dados]                  [Processamento & Banco]               [IA, Governança & Entrega]
──────────────────                 ───────────────────────               ──────────────────────────
API Transparência Palmas ──▶ Coleta & ETL Idempotente ──▶ PostgreSQL / SQLite
(sgreceitas / NUCLEOGOV)     (src/etl_sefin.py)           (schema tributario)
                                                                 │
API IBGE (Censo 2022)    ──▶ Enriquecimento Territorial ─────────┤
(src/api/coleta_ibge.py)     (engenharia_atributos.py)           ▼
                                                         Preparo & Trava RNF01
Carteira de Contribuintes ─▶ Pseudonimização LGPD ─────▶ (protecao_iptu_social.py)
(Camada Individual)          (src/ml/preparar_base.py)           │
                                                                 ▼
                                                         Modelagem Temporal & Scoring
                                                         (models/*.joblib)
                                                                 │
                                        ┌────────────────────────┼────────────────────────┐
                                        ▼                        ▼                        ▼
                                Auditoria Fairness         Explicabilidade          Painel MVP
                                (Fairlearn / RIA)          (SHAP Art. 20)           (Streamlit)