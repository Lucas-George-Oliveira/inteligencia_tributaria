# Metodologia de Dados e Preparação — Sprint 4 (Entrega E1)

## 1. Objetivo e origem dos dados
Este documento registra a etapa de preparação da base, as regras de proteção de dados e a divisão temporal utilizadas nos modelos iniciais (baselines) da Entrega E1. O foco desta etapa é garantir que o experimento seja claro, transparente e reproduzível para a equipe e para a avaliação do projeto.

Os dados utilizados neste estudo não vêm de um cadastro real de moradores ou contribuintes de Palmas. Trata-se de uma carteira individual sintética (gerada artificialmente para fins acadêmicos), extraída do repositório de Prova de Conceito (PoC) disponibilizado pelo professor da disciplina:
* **Repositório de origem:** `github.com/DavidNadlerPrata/poc-inteligencia-tributaria-palmas`

## 2. Preparação, filtragem e proteção de dados (LGPD e RNF01)
Todo o processo de limpeza e filtragem da base foi implementado no script `src/ml/preparar_base.py`. Partindo da base sintética original, aplicamos as seguintes regras:
* **Exclusão do IPTU Social:** A base inicial continha **20.000 registros**. Desse total, **1.393 registros** pertenciam a beneficiários do IPTU Social e foram removidos da amostra, restando **18.607 perfis elegíveis** para a modelagem.
* **Verificação de qualidade:** Durante a checagem dos dados preparados, confirmamos que não há falhas de preenchimento: foram encontrados **0 valores ausentes** e **0 IDs duplicados**.
* **Conformidade com o RNF01:** Para respeitar o requisito não funcional RNF01, o indicador de isenção social não pode ser usado como variável para prever inadimplência. Na implementação do código, a coluna original `iptu_social` (vinda do arquivo CSV) foi tratada e adaptada para `is_iptu_social` dentro da função de preparo.
* **Cuidados com a LGPD:** A base utiliza identificadores pseudonimizados e teve dados sensíveis/identificadores diretos removidos antes do treinamento. Ainda assim, deixamos registrado que essa remoção reduz riscos de exposição, mas não deve ser tratada como uma anonimização irreversível nem como conformidade total e definitiva com a LGPD.

## 3. Como o histórico mensal foi construído
Para simular o comportamento dos contribuintes ao longo do tempo, o script `src/ml/gerar_historico_sintetico.py` expandiu os 18.607 perfis elegíveis ao longo de 12 períodos mensais (janeiro a dezembro de 2024), gerando um total de **223.284 observações simuladas**.

Nesse processo, o gerador só atualiza determinados atributos financeiros após o fechamento do resultado de cada mês, evitando que o modelo tenha acesso antecipado ao que vai acontecer. Além disso, enquanto o teste inicial usava uma divisão aleatória para prever a inadimplência no próximo exercício (`inadimplente_proximo_exercicio`), esta etapa temporal passou a utilizar como alvo a variável `inadimplente_proximo_periodo`.

## 4. Divisão temporal dos conjuntos
Em vez de misturar meses passados e futuros aleatoriamente, a separação dos dados foi feita respeitando a ordem cronológica por meio do arquivo `src/ml/divisao_temporal.py`. A função ordena os registros por data, garante que registros da mesma data fiquem juntos no mesmo grupo e divide os 12 meses simulados da seguinte forma:

| Conjunto | Período simulado | Quantidade de observações |
| :--- | :--- | :--- |
| **Treino** | Jan.–jul./2024 | 130.249 |
| **Validação** | Ago.–set./2024 | 37.214 |
| **Teste** | Out.–dez./2024 | 55.821 |

## 5. Cuidados contra vazamento de dados e limitações
Para evitar o chamado *data leakage* (quando o modelo "cola" usando informações que não teria na vida real), adotamos três cuidados principais:
1. O pré-processamento (como escalonamento e ajustes estatísticos) foi calculado apenas sobre o conjunto de treino e depois aplicado aos demais.
2. Os resultados de cada mês só entram como informação quando já estão fechados no tempo.
3. Identificadores (IDs), faixas de renda protegidas e resultados de períodos futuros foram removidos da lista de variáveis explicativas.

**Limitações conhecidas:** Embora esses cuidados diminuam bastante o risco de vazamento de dados, eles não garantem sua ausência absoluta. Além disso, como os mesmos 18.607 perfis aparecem repetidamente ao longo dos 12 meses simulados, este experimento avalia como o modelo projeta períodos futuros para uma carteira já conhecida — não sendo possível afirmar, apenas com este teste, que ele teria o mesmo comportamento para contribuintes totalmente novos. Vale ressaltar também que uma validação cronológica ainda mais ampla segue prevista para as próximas etapas de evolução do projeto.
