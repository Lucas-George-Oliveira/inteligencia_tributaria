# Inteligência Tributária em Palmas
Projeto Integrador: Inteligência Tributaria: Predição de Inadimplência e Priorização da Dívida Ativa de Palmas-TO

## 2.1. Identificação da Equipe e Links

| Nome do Integrante | Matrícula | Usuário GitHub (@) | Papel Principal no Time |
| :--- | :--- | :--- | :--- |
| Lucas George Oliveira Nascimento | 2026111523 | `@Lucas-George-Oliveira` | Product Owner (PO) / Repo Owner |
| Jacinto Pereira Brito | 2026111953 | `@Jacintopereirabrito-Design` | Scrum Master (SM) |
| Pedro Santos Magalhães Neto | 2026111909 | `@pedroneto-git` | Developer Backend |
| Rafael Vieira Lima | 2026112215 | `@rafaelvlima18` | Developer ML (AI) |
| Geovana Souza Mendonça | 2026112336 | `@geomendonca` | Developer Frontend |

* **Repositório do Projeto:** `https://github.com/Lucas-George-Oliveira/inteligencia-tributaria`
* **Painel de Gestão Ágil (Kanban):** `https://github.com/users/Lucas-George-Oliveira/projects/1`

---

## 2.2. Fundamentação e Dinâmica dos Papéis Ágeis

| Papel | Integrante(s) | Principais Atribuições e Responsabilidades | Mecanismo de Validação e Controle |
| :--- | :--- | :--- | :--- |
| **Product Owner (PO) & Repo Owner** | Lucas George | * Gerenciamento do Product Backlog e priorização MoSCoW.<br>* Configuração da arquitetura e segurança do repositório (`.github/CODEOWNERS`).<br>* Garantia de conformidade com a LGPD (Art. 20) e isenção de 100% do IPTU Social nas cobranças. | * **Revisor Único Obrigatório:** Aprovação exclusiva de todos os Pull Requests para a branch `main`.<br>* Validação dos Critérios de Aceite e métricas de desempenho/fairness nas entregas das Sprints. |
| **Scrum Master (SM)** | Jacinto Brito | * Facilitador dos rituais Scrum (Sprints, Dailies, Reviews).<br>* Remoção de impedimentos técnicos da equipe.<br>* Gestão do quadro Kanban (GitHub Projects) e padronização dos *Conventional Commits*. | * Acompanhamento da velocidade do time e cumprimento de prazos.<br>* Organização dos canais de comunicação assíncrona e reuniões síncronas de 15 minutos. |
| **Equipe de Desenvolvimento (Dev Team)** | Pedro Neto,<br>Rafael Vieira,<br>Geovana Mendonça | * Desenvolvimento da ingestão via API REST, scripts ETL e anonimização.<br>* Treinamento e serialização do modelo preditivo de inadimplência.<br>* Construção do painel interativo em Streamlit. | * **Workflow Estrito:** Trabalho em branches `feature/*`.<br>* Proibição de push direto na `main`.<br>* Submissão de PRs com preenchimento do template de testes obrigatório. |

### Rituais e Comunicação

* **Daily Standups:** Reuniões síncronas de 15 minutos diárias via Discord.
* **Comunicação Assíncrona:** Acompanhamento diário no canal do time e registro de *issues* no GitHub Projects.
* **Política de Integração:** Fluxo de aprovação estrita via Pull Request supervisionado e validado pelo Product Owner.
