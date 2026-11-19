# Relatório de Impacto Algorítmico (RIA) — Modelo de Recuperabilidade da Dívida Ativa (Sefin Palmas)

**Projeto Integrador — Inteligência Tributária | BIINAR UFT, Eixo II 2026/2 | Sprint 5 — E2**

---

## 1. Mapeamento de Dados Pessoais/Sensíveis e Conformidade com a LGPD

O sistema processa dados cadastrais, imobiliários e fiscais estruturados conforme o Modelo Entidade-Relacionamento (`docs/DER.md`). Para mitigar riscos à privacidade desde a concepção (*Privacy by Design*), os identificadores diretos são descartados antes da modelagem (`src/ml/preparar_base.py`), substituindo chaves naturais por hashes pseudonimizados.

### 1.1 Inventário de Dados e Bases Legais (Lei nº 13.709/2018)

| Entidade (`DER.md`) | Atributos Mapeados | Classificação LGPD | Uso no Pipeline / Modelo | Base Legal (LGPD) |
| :--- | :--- | :--- | :--- | :--- |
| `CONTRIBUINTE` | `cnpj_cpf`, `nome`, `contato` | Dado Pessoal Direto | **Excluídos** antes do treino e inferência; mantidos apenas na base restrita da Sefin para contato administrativo. | Art. 7º, III (Execução de políticas públicas) e Art. 7º, II (Cumprimento de obrigação legal - CTN). |
| `CONTRIBUINTE` | `boolean_is_iptu_social` | Dado Pessoal / Indicador de Vulnerabilidade | Usado exclusivamente como **filtro de exclusão formal** (`src/ml/preparar_base.py`), removendo 1.393 beneficiários (idosos, aposentados, pensionistas e PcD de baixa renda) antes de qualquer predição. | Art. 7º, III e Art. 11, II, 'b' (Políticas públicas de proteção social e isenção tributária). |
| `IMOVEL` | `inscricao_imobiliaria`, `logradouro` | Dado Pessoal Indireto | **Excluídos** da base analítica de modelagem. | Art. 7º, III (Execução de políticas públicas). |
| `IMOVEL` | `bairro`, `setor_urbano`, `area_edificada` | Dado Cadastral / Territorial | `setor_urbano` e `area_edificada` entram como variáveis do modelo. `faixa_renda_setor` não entra no treino (usada apenas na auditoria de viés). | Art. 7º, III (Execução de políticas públicas). |
| `DEBITO_TRIBUTARIO` | `tipo_tributo`, `valor_debito`, `data_vencimento`, `status_pagamento` | Dado Financeiro / Fiscal | Variáveis agregadas (dívida consolidada, exercícios inadimplentes, parcelamentos) alimentam o modelo. | Art. 7º, III (Gestão da dívida ativa) e Art. 7º, X (Proteção do crédito público). |
| `LOG_AUDITORIA` / `ANALISTA_FISCAL` | `id_analista`, `nome`, `perfil`, `timestamp`, `filtros_aplicados`, `justificativa_lgpd` | Dado Pessoal Funcional | Rastreabilidade interna de acessos e consultas feitas por servidores da Sefin e Procuradoria. | Art. 7º, II e Art. 37 (Registro de operações de tratamento para auditoria). |

### 1.2 Armazenamento, Retenção e Segurança
* **Minimização e Dados Sensíveis:** Nenhum atributo sensível (raça, origem étnica, saúde, deficiência) ou demográfico (idade, sexo) entra como variável no modelo.
* **Ambiente Atual:** A base utilizada (`data/bruto/carteira_contribuintes_sintetica.csv`) é sintética, gerada apenas para validação acadêmica.
* **Retenção Proposta (Produção):** Os registros de auditoria (`LOG_AUDITORIA`) devem ser retidos por 5 anos (alinhado ao prazo prescricional tributário do Art. 174 do CTN) com acesso restrito por perfil (`ANALISTA_FISCAL`). Os scores (`SCORE_RECUPERABILIDADE`) têm validade mensal, sendo atualizados a cada ciclo de escoragem.

### 2.  Análise de Fairness (Justiça Algorítmica) e Mitigação de Vieses
##  2.1 Metodologia e Métricas Avaliadas
Para verificar se o modelo campeão (Regressão Logística Temporal, com limiar de decisão original de $0{,}23$ e $F_1\text{-Score}$ 
global de $0{,}4209$) reproduz ou amplifica desigualdades socioeconômicas ou territoriais sobre a carteira de teste  ( $N = 55.
821$ registros), realizou-se uma auditoria quantitativa utilizando a biblioteca Fairlearn. Foram avaliados três recortes   
sensíveis — faixa de renda do setor, setor urbano e tipo de imóvel — sob dois critérios formais de equidade:

#   Paridade Demográfica (Demographic Parity):  
Avalia se a proporção de contribuintes  sinalizados como risco de inadimplência ($\hat{Y} = 1$, chamada de Taxa de Seleção) é 
equilibrada entre os grupos. Adota-se como referência regulatória a Regra dos Quatro  Quintos (4/5), segundo a qual a razão entre 
a menor e a maior taxa de seleção deve ser $\ge 0{,}80$.

#   Igualdade de Oportunidade (Equal Opportunity):
Mede se a Taxa de Verdadeiros Positivos ($TPR / \text{Recall}$) é equivalente entre os grupos para os contribuintes que 
efetivamente se tornaram inadimplentes ($Y = 1$), garantindo que nenhum subgrupo tenha capacidade preditiva sistematicamente 
inferior.

### 2.2 Resultados Obtidos (Cenário Original vs. Cenário Mitigado)

##  A) Recorte por Faixa de Renda do Setor (faixa_renda_setor)

Subgrupo,   Amostras (N),  Taxa Real (Y=1),  Taxa de Seleção (Original),   Taxa de Seleção (Mitigado),  Igualdade de Oportunidade / TPR (Original),   Igualdade de Oportunidade / TPR (Mitigado),Limiar Ajustado
Alta Renda,11.844,"23,33%","55,75%","68,00%","68,33%","79,41%","0,220"
Média Renda,20.049,"24,26%","58,22%","64,66%","70,56%","76,07%","0,220"
Baixa Renda,23.928,"25,93%","68,88%","68,88%","79,05%","79,05%","0,230"

#   Indicadores de Disparidade:
No modelo original, a Razão de Paridade Demográfica foi de $0{,}8094$ (no limite inferior da faixa aceitável de $0{,}80$), com 
diferença de $13{,}13$ p.p. na taxa de seleção e $10{,}71$ p.p. na Igualdade de Oportunidade ($TPR$) entre baixa e alta renda. 
Após o ajuste fino de limiares ($0{,}22$ para alta e média renda; $0{,}23$ para baixa renda), a Razão de Paridade Demográfica 
subiu para $0{,}9388$ e a diferença de $TPR$ caiu para $3{,}34$ p.p., mantendo o $F_1\text{-Score}$ global praticamente 
inalterado ($0{,}4207$).
.(Inserir aqui a figura: docs/figuras/ria_mitigacao_faixa_renda_setor.png)

##  B) Recorte por Setor Urbano (setor_urbano)
Subgrupo Amostras(N) Taxa Real (Y=1)  Taxa de Seleção(Original) Taxa de Seleção(Mitigado)  Igualdade de Oportunidade / TPR (Original)Igualdade de Oportunidade / TPR (Mitigado)Limiar Ajustado Área de Expansão2.
92524,31%58,53%75,62%70,18%83,83%0,210Aureny9.54625,75%68,12%69,12%79,29%80,19%0,225Jardim Aureny IV4.04722,81%59,03%70,84%70,
42%80,50%0,215Plano Diretor Norte8.28923,42%52,74%70,41%65,53%81,30%0,215Plano Diretor Sul13.07724,70%57,90%66,16%70,68%77,43%0,
220Setor Comercial Central3.55523,12%62,76%68,10%74,94%80,90%0,225Taquaralto10.32326,28%68,53%74,92%78,07%82,82%0,220Taquari4.
05925,45%71,54%71,54%81,03%81,03%0,230

# Indicadores de Disparidade: Antes da mitigação, o recorte territorial violava a Regra dos 4/5, apresentando Razão de Paridade 
Demográfica de $0{,}7372$ (comparando Plano Diretor Norte, com $52{,}74\%$, e Taquari, com $71{,}54\%$) e diferença de $15{,}49$ 
p.p. no $TPR$. Com a calibração de limiares específicos por setor (variando entre $0{,}210$ e $0{,}230$), a Razão de Paridade 
Demográfica elevou-se para $0{,}8749$ (dentro da conformidade $\ge 0{,}80$) e a diferença de $TPR$ reduziu-se para $6{,}40$ p.p. 
($F_1\text{-Score}$ global de $0{,}4199$).
.(Inserir aqui a figura: docs/figuras/ria_mitigacao_setor_urbano.png)

##  C) Recorte por Tipo de Imóvel (tipo_imovel)
SubgrupoAmostras (N)Taxa Real (Y=1)Taxa de Seleção (Original)Taxa de Seleção (Mitigado)Igualdade de Oportunidade / TPR (Original)
Igualdade de Oportunidade / TPR (Mitigado)Limiar AjustadoComercial10.36223,89%59,60%85,43%72,20%91,84%0,175Industrial1.62324,
46%61,18%84,47%75,06%91,69%0,170Residencial39.91224,67%60,63%85,47%72,22%91,27%0,175Terreno3.92428,36%86,31%86,31%92,36%92,36%0,
230

# Indicadores de Disparidade: Este foi o recorte de maior assimetria no modelo original, com Razão de Paridade Demográfica de $0
{,}6905$ (abaixo do limiar de $0{,}80$) e diferença de $20{,}16$ p.p. no $TPR$ entre imóveis comerciais ($72{,}20\%$) e terrenos 
($92{,}36\%$). Após a mitigação pós-processamento, a Razão de Paridade Demográfica atingiu $0{,}9787$ e a diferença de $TPR$ caiu 
para apenas $1{,}10$ p.p. ($F_1\text{-Score}$ global de $0{,}4111$)
.(Inserir aqui a figura: docs/figuras/ria_mitigacao_tipo_imovel.png)

##  2.3 Discussão Honesta dos Vieses e Estratégia de Mitigação
# 1. Diagnóstico das Causas: 
Observa-se que o modelo original tende a sinalizar proporcionalmente mais contribuintes de baixa renda ($68{,}88\%$ vs. $55{,}75\%$ na alta renda) e de regiões periféricas/em expansão (Taquari com $71{,}54\%$ e Taquaralto com $68{,}53\%$ vs. Plano Diretor 
Norte com $52{,}74\%$), embora a diferença na inadimplência real entre esses grupos seja de apenas $2{,}6$ a $3{,}5$ pontos 
percentuais. Isso ocorre porque variáveis socioeconômicas territoriais e o histórico de parcelamentos anteriores possuem forte 
correlação com a renda do setor, fazendo com que o algoritmo penalize desproporcionalmente contribuintes de áreas vulneráveis 
(aumentando a taxa de falsos positivos nesses grupos, com diferença de $FPR$ de $19{,}47$ p.p. entre setores urbanos). No recorte 
por tipo de imóvel, terrenos apresentam maior inadimplência real ($28{,}36\%$) e comportamento histórico 
mais volátil, levando o limiar único a sub-sinalizar imóveis comerciais e residenciais.

#  2. Eficácia e Trade-off da Mitigação:
A aplicação de mitigação pós-processamento via otimização de limiares por subgrupo demonstrou-se eficaz para restaurar a equidade 
sem necessidade de alterar a arquitetura do modelo treinado. Em todos os recortes, a Razão de Paridade Demográfica passou a 
$\58\%$. Contudo, assume-se de forma transparente o trade-off operacional: ao reduzir o limiar de corte para equalizar o $TPR$ 
(especialmente no recorte de tipo de imóvel, onde os limiares caíram para $0{,}170\text{–}0{,}175$), há elevação na taxa global 
de seleção e leve queda na precisão média (de $\sim 29\%$ para $\sim 26\%$). Portanto, recomenda-se que a mitigação por limiar 
seja utilizada em conjunto com triagem humana e réguas de cobrança amigável (preventiva), evitando medidas coercitivas 
automáticas baseadas exclusivamente no escore.