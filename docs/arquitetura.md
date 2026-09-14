# Arquitetura e Estrutura do Repositório

Este documento especifica a organização dos diretórios, a finalidade dos arquivos do commit inicial e as diretrizes de evolução arquitetural para o sistema de Inteligência Tributária (Sefin/Palmas-TO).

---

## 1. Visão Geral da Arquitetura

O projeto adota uma estrutura modular baseada em boas práticas de Engenharia de Software, promovendo a separação de responsabilidades (SoC), reprodutibilidade, auditabilidade e conformidade integral com a LGPD. Para o início da Sprint 1, foi estabelecida uma arquitetura enxuta (*lean*) que garante a facilidade de integração contínua sem criar sobrecarga de arquivos vazios.

---

## 2. Estrutura do Repositório (Commit Inicial)

```text
inteligencia-tributaria-palmas/
├── .github/
│   ├── CODEOWNERS                    # Configuração do PO como revisor obrigatório de PRs
│   └── PULL_REQUEST_TEMPLATE.md      # Template com checklist de testes e conformidade LGPD
├── data/
│   └── .gitkeep                      # Estrutura reservada para dados (ignorada no versionamento)
├── docs/
│   ├── requisitos.md                 # Tabela de Requisitos Funcionais, Não Funcionais e MoSCoW
│   └── arquitetura.md                # Este documento de especificação da arquitetura
├── notebooks/
│   └── .gitkeep                      # Espaço para análises exploratórias preliminares (.ipynb)
├── src/
│   ├── __init__.py                   # Inicializador do pacote Python
│   └── app.py                        # Ponto de entrada da aplicação Streamlit
├── .gitignore                        # Filtro de arquivos ignorados (dados sensíveis, .env e caches)
├── README.md                         # Documentação principal, identificação do time e regras
└── requirements.txt                  # Dependências Python com versões fixadas
