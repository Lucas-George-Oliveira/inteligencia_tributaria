# Documentação do MVP — Painel de Recuperabilidade da Dívida Ativa (Sefin Palmas)

**Projeto Integrador — Inteligência Tributária | BIINAR/UFT, Eixo II 2026/2**  
**Entregáveis:** Sprint 4 (E4) e Sprint 5 (E4 — Portfólio Revisado)  
**Código-fonte:** [`src/painel/painel_sefin.py`](../src/painel/painel_sefin.py) e [`src/ml/scoring_recuperabilidade.py`](../src/ml/scoring_recuperabilidade.py)

---

## 1. Objetivo e Escopo

O MVP operacionaliza o modelo preditivo (`models/modelo_campeao_recuperabilidade.joblib`) em uma interface interativa para analistas e auditores fiscais da Secretaria da Fazenda (Sefin) de Palmas-TO, permitindo priorizar ações de cobrança administrativa com base na propensão de pagamento e no retorno financeiro esperado.

> **Aviso de Dados Sintéticos:** A carteira individual de contribuintes (`data/bruto/carteira_contribuintes_sintetica.csv`) é sintética, gerada pela equipe para validar o fluxo técnico e ético de ponta a ponta enquanto a base real da dívida ativa não é disponibilizada pela Sefin. O painel exibe esse alerta de forma permanente no topo da aplicação.

---

## 2. Regras de Negócio e Régua de Cobrança

1. **Exclusão Obrigatória do IPTU Social (`RNF01`):** Antes de renderizar qualquer indicador, tabela ou mapa, `carregar_carteira()` aplica `remover_protegidos_da_saida()` (`src/ml/protecao_iptu_social.py`). Dos 20.000 contribuintes da carteira sintética, os **1.393 beneficiários** são excluídos e apenas os **18.607 elegíveis** são exibidos. No simulador, marcar a opção de beneficiário bloqueia o cálculo do score.
2. **Pseudonimização (`RNF04`):** CPF/CNPJ, nome, contato, logradouro e inscrição imobiliária são removidos antes da modelagem (`src/ml/preparar_base.py`). O painel exibe apenas hashes (`id_contribuinte`).
3. **Fórmulas de Priorização:**
   * $\text{Score de Recuperabilidade} = \text{round}((1 - P(\text{inadimplência})) \times 1000)$, na escala de `0` a `1000`.
   * $\text{Retorno Esperado (R\$)} = (1 - P(\text{inadimplência})) \times \text{Dívida Consolidada}$.
4. **Faixas e Ações Recomendadas (`classificar_estrategia_sefin`):**

| Faixa | Score | Regra Adicional | Ação Recomendada à Sefin |
| :--- | :---: | :--- | :--- |
| **Faixa A — Alta Recuperabilidade** | $\ge 750$ | — | Notificação digital preventiva (SMS/E-mail/DTE) |
| **Faixa B — Média Recuperabilidade** | $450 \text{ a } 749$ | — | Cobrança administrativa ativa + oferta de parcelamento ordinário |
| **Faixa C1 — Baixa / Alto Valor** | $200 \text{ a } 449$ | Dívida $\ge \text{R\$ } 1.500,00$ | Protesto extrajudicial em cartório / priorizar execução fiscal (com revisão humana) |
| **Faixa C2 — Baixa / Baixo Valor** | $200 \text{ a } 449$ | Dívida $< \text{R\$ } 1.500,00$ | Protesto em cartório (evitar ajuizamento pelo custo processual) |
| **Faixa D — Crítica** | $< 200$ | — | Cobrança passiva / elegível para mutirões fiscais (REFIS) |

---

## 3. Funcionalidades do Painel (5 Abas)

* **Filtros Laterais (`RF03`):** Filtragem simultânea por setor urbano (8 regiões de Palmas), faixa de recuperabilidade, faixa de renda do setor e valor mínimo da dívida, atualizando os 4 KPIs superiores em tempo real.
* **Aba 1 — Ranking (`RF01`, `RF06`):** Ordenação dinâmica por retorno esperado (R$) ou score de recuperabilidade, controle de Top-N e exportação direta em CSV (`ranking_recuperabilidade.csv`).
* **Aba 2 — Mapa por Setor (`RF01`, `RF10`):** Mapa interativo (`pydeck`) com centroides dos 8 setores urbanos de Palmas (cor por probabilidade média de inadimplência e raio proporcional ao total de contribuintes), acompanhado de ranking em barras e matriz de calor `Setor × Tipo de Imóvel`.
* **Aba 3 — Projeção de Arrecadação:** Curva acumulada de retorno esperado conforme a capacidade de atendimento da equipe e tabela consolidada por ação recomendada.
* **Aba 4 — Simulador:** Inferência ao vivo utilizando `models/modelo_campeao_recuperabilidade.joblib`, respeitando a trava de proteção do IPTU Social.
* **Aba 5 — Métricas do Modelo:** Métricas globais no conjunto de teste (`Acurácia`, `Precisão`, `Recall`, `F1`, `ROC AUC` com limiar `0,23`) e tabela desagregada por subgrupo (`faixa_renda_setor` e `setor_urbano`).

---

## 4. Como Executar

```bash
pip install -r requirements.txt
streamlit run src/painel/painel_sefin.py