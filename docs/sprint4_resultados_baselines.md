# Resultados e Interpretação dos Baselines — Sprint 4 (Entrega E1)

## 1. Baselines temporais (limite padrão de 0,50)
Nesta etapa da Sprint 4, avaliamos dois modelos iniciais (Regressão Logística e Árvore de Decisão) utilizando a divisão temporal dos dados e o limite padrão de classificação de 0,50. Os resultados obtidos no conjunto de teste foram:

| Modelo | Acurácia (Teste) | F1-score (Teste) |
| :--- | :--- | :--- |
| **Regressão Logística** | 75,16% | 5,24% |
| **Árvore de Decisão** | 74,97% | 5,65% |

**Interpretação dos números:** Apesar de a acurácia parecer alta (em torno de 75%), o **F1-score muito baixo** (5,24% e 5,65%) revela que os modelos praticamente não conseguiram identificar os contribuintes inadimplentes. Isso acontece porque os dados são desbalanceados: no conjunto de teste, existem **41.990 não inadimplentes (75,22%)** e **13.831 inadimplentes (24,78%)**. Na prática, um modelo que previsse sempre "não inadimplente" para todo mundo já alcançaria 75,22% de acurácia sem detectar nenhum caso real de inadimplência.

## 2. Ajuste do limite de probabilidade com a validação
Para corrigir essa baixa detecção de inadimplentes, diferentes limites de probabilidade (thresholds) foram testados exclusivamente no conjunto de validação. O limite escolhido foi **0,23** para ambos os modelos. Somente após essa escolha os modelos foram reavaliados no conjunto de teste:

| Modelo | Acurácia | Precisão | Recall | F1-score |
| :--- | :--- | :--- | :--- | :--- |
| **Regressão Logística** | 49,60% | 29,42% | 73,91% | 42,09% |
| **Árvore de Decisão** | 48,99% | 29,18% | 74,20% | 41,89% |

## 3. Conclusões e análise crítica dos resultados
* **Ganho na detecção (Recall e F1):** Com o ajuste do limite para 0,23, o F1-score subiu expressivamente para cerca de **42%** e o Recall ficou próximo de **74%**, mostrando que os modelos passaram a capturar a maior parte dos inadimplentes reais.
* **Custo em falsos positivos e acurácia:** Esse ganho teve um custo claro: a precisão ficou próxima de **29%**, indicando um volume elevado de falsos positivos (contribuintes adimplentes classificados incorretamente como inadimplentes). Como consequência, a acurácia geral caiu para cerca de **49%**.
* **Comparação entre os modelos:** A Regressão Logística alcançou um F1-score ligeiramente superior (42,09% contra 41,89% da Árvore de Decisão), mas o comportamento geral de ambos é bastante próximo.
* **Maturidade para uso prático:** Os resultados deixam claro que esses modelos ainda são baselines exploratórios e **não estão prontos para orientar ações reais de cobrança** pela prefeitura.

## 4. Diferença entre o experimento aleatório e o experimento temporal
Em testes preliminares realizados com divisão aleatória da base (onde a Regressão Logística obteve 65,64% de acurácia e 65,66% de F1-score, contra 63,41% de acurácia e 64,36% de F1-score da Árvore de Decisão), os números apresentavam um comportamento diferente.

Contudo, **não se deve comparar os dois experimentos como se fossem iguais**. O teste aleatório anterior buscava prever a variável-alvo `inadimplente_proximo_exercicio`, enquanto o experimento atual utiliza divisão cronológica e prevê `inadimplente_proximo_periodo`. Como a construção dos dados e o alvo previsto são distintos, diferenças nas métricas não podem ser atribuídas apenas ao método de divisão (aleatório vs. temporal).

## 5. Fontes e arquivos de referência consultados
As métricas e regras analisadas neste documento foram verificadas nos seguintes arquivos do repositório:
* `models/metricas_baselines.json`
* `models/metricas_baselines_temporais.json`
* `models/metricas_limites_temporais.json`
* `src/ml/baselines_temporais.py`
