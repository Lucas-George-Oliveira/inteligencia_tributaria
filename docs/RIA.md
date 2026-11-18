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
