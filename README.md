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

---

## 3. Sprint 3 — Pipeline ETL e Análise Exploratória

Nesta sprint o dado passa a fluir sozinho: a coleta automatizada busca as receitas na API da Prefeitura de Palmas, o pipeline `src/etl_sefin.py` limpa, valida e carrega os registros no banco, e os notebooks de análise exploratória (EDA) descrevem os padrões encontrados.

> **Escopo dos dados.** A API disponível (`sgreceitas`) fornece **receitas orçamentárias agregadas** (previsto x arrecadado por tipo de receita), e não débitos individuais de contribuintes. Por isso a EDA descreve a arrecadação, e o mapa de inadimplência usa os **dados piloto fictícios** do banco apenas como demonstração do método. Detalhes em [`docs/relatorio_eda.md`](docs/relatorio_eda.md).

### 3.1 Estrutura de pastas

```text
inteligencia_tributaria/
├── data/
│   ├── bruto/            # dados como vieram da fonte, datados (nunca editados)
│   │   ├── coleta_api_AAAAMMDD_HHMMSS.json   # coleta da API da Prefeitura
│   │   └── ibge/         # malha do Censo 2022 (baixada pelo notebook; não versionada)
│   ├── processado/       # dados limpos e prontos: receitas_tratadas_*.csv + resumo_etl_*.json
│   └── rejeitados/       # registros reprovados na validação, para revisão
├── docs/
│   ├── relatorio_eda.md  # Relatório de Análise Exploratória (E3)
│   ├── figuras/          # gráficos e mapas estáticos (PNG) usados no relatório
│   ├── mapas/            # mapas interativos (HTML, abrir no navegador)
│   └── GUIA_ETL_E2.md    # documentação detalhada do pipeline ETL
├── notebooks/
│   ├── eda_receitas.ipynb        # estatísticas e gráficos da EDA
│   └── mapas_geoespaciais.ipynb  # mapa de inadimplência (piloto) e mapa IBGE
├── logs/                 # logs de execução do ETL (gerados automaticamente)
├── src/
│   ├── api/              # coleta: coleta_dados.py (Prefeitura) e coleta_ibge.py (IBGE)
│   ├── core/             # limpeza_receitas.py, engenharia_atributos.py, grafo_vinculos.py
│   ├── database/         # carga_receitas.py, esquema SQL (schema/V1..V4) e dados piloto
│   └── etl_sefin.py      # orquestrador do pipeline (extração → limpeza → carga)
├── tests/                # testes automatizados (pytest)
├── requirements.txt          # dependências gerais (instaladas automaticamente no Codespace)
├── requirements-etl.txt      # dependências extras do pipeline ETL
└── requirements-postgres.txt # driver do PostgreSQL (só para carga em Postgres)
```

As camadas pedidas na tarefa correspondem às pastas assim: **bruto** = `data/bruto/`; **limpo** = `data/processado/receitas_tratadas_*.csv` (após limpeza e validação); **pronto** = tabela `receitas_sefin_etl` no banco, carregada pelo pipeline.

### 3.2 Como executar do zero

Os passos abaixo foram testados em um GitHub Codespace (Python 3.10) a partir de um clone limpo do repositório.

**Passo 1 — Abrir o ambiente.** No GitHub, clique em **Code → Codespaces → Create codespace on main**. O ambiente já vem com Python 3.10 e instala o `requirements.txt` automaticamente. Para rodar localmente, use Python 3.10 ou superior e crie um ambiente virtual.

**Passo 2 — Instalar as dependências que faltam.** O Codespace instala só o `requirements.txt`; o pipeline e os notebooks precisam também destas:

```bash
pip install -r requirements.txt -r requirements-etl.txt ipykernel openpyxl
```

**Passo 3 — Rodar o pipeline sem banco (teste rápido).** Lê o JSON bruto mais recente de `data/bruto/`, limpa, valida e gera o CSV tratado em `data/processado/`:

```bash
python -m src.etl_sefin --sem-carga
```

Saída esperada: `Transformação: entrada=3000, válidos=3000, rejeitados=0`.

**Passo 4 — (Opcional) Fazer uma nova coleta na API.** Respeita paginação e intervalo entre requisições; salva um novo JSON datado em `data/bruto/` sem alterar os anteriores:

```bash
python -m src.etl_sefin --coletar --paginas 3 --sem-carga
```

**Passo 5 — Carregar no banco.** Crie um arquivo `.env` na raiz (ele **não** é versionado) com a URL do banco. Para testar sem PostgreSQL, use o SQLite de demonstração:

```bash
echo "ETL_DATABASE_URL=sqlite:///./data/sefin_demo.db" > .env
python -m src.etl_sefin --criar-tabela
```

Saída esperada: `Carga concluída: inseridos=3000`. Rodar de novo não duplica nada (`sem alteração=3000`), porque a carga é idempotente. Para o PostgreSQL da Sprint 2, instale `requirements-postgres.txt` e siga a seção 5 do [`docs/GUIA_ETL_E2.md`](docs/GUIA_ETL_E2.md).

**Passo 6 — Gerar a EDA e os mapas.** Abra os notebooks na pasta `notebooks/`, selecione o kernel **Python 3.10** e clique em **Run All** (Executar Tudo), nesta ordem:

1. `eda_receitas.ipynb` → gera `docs/figuras/g1` a `g4`. Se ainda não existir CSV tratado, o próprio notebook roda o pipeline do Passo 3.
2. `mapas_geoespaciais.ipynb` → baixa a malha do IBGE (cerca de 75 MB, só na primeira vez) e gera `docs/mapas/*.html` e `docs/figuras/m1` e `m2`.

**Passo 7 — Rodar os testes.**

```bash
python -m pytest tests/test_etl.py tests/test_engenharia_atributos.py tests/test_coleta_ibge.py -v
```

O teste `test_coleta_ibge` consulta a API do IBGE e precisa de internet.

### 3.3 O que cada execução gera

| Arquivo | Gerado por | Conteúdo |
| :--- | :--- | :--- |
| `data/bruto/coleta_api_*.json` | coleta (Passo 4) | Resposta original da API, com data e hora no nome |
| `data/processado/receitas_tratadas_*.csv` | pipeline (Passos 3 e 5) | Registros limpos e validados |
| `data/processado/resumo_etl_*.json` | pipeline | Totais de entrada, válidos, rejeitados e status |
| `data/rejeitados/receitas_rejeitadas_*.csv` | pipeline | Registros reprovados, para revisão |
| `logs/etl_sefin.log` | pipeline | Log de cada etapa, com sucessos e falhas |
| `docs/figuras/*.png`, `docs/mapas/*.html` | notebooks (Passo 6) | Gráficos e mapas do relatório |

### 3.4 Divisão de trabalho na Sprint 3

Conforme o histórico de commits e pull requests da sprint:

| Integrante | Entregável | O que fez |
| :--- | :--- | :--- |
| Lucas George Oliveira Nascimento | E1 — Coleta | Coleta automatizada via API REST com paginação e intervalos entre requisições; primeiro lote bruto datado; revisão e merge dos PRs |
| Geovana Souza Mendonça | E2 — ETL, limpeza e carga | Orquestrador `etl_sefin.py`, rotinas de limpeza e validação, carga idempotente no banco e logs |
| Jacinto Pereira Brito | E2 — Enriquecimento | Coleta de indicadores do IBGE e engenharia de atributos (tempo de inadimplência, sazonalidade, faixas de valor) |
| Pedro Santos Magalhães Neto | E3 e E4 — EDA e reprodutibilidade | Notebooks de EDA e mapas geoespaciais, relatório de EDA e este README |
| Rafael Vieira Lima | *(a preencher pela equipe)* | |

### 3.5 Limitações e problemas conhecidos

- **Os dados coletados não são de inadimplência.** O modelo da Sprint 4 precisa de uma base de débitos da dívida ativa, individual e anonimizada, com a localização do imóvel.
- **A coleta cobre cerca de 1,7% da API** (3 de cerca de 181 páginas): apenas setembro (incompleto) e outubro de 2026. Recomenda-se ampliar `--paginas` e coletar só meses fechados.
- **`tests/test_app.py` depende de `fastapi`,** que não está em nenhum `requirements`. Por isso o comando do Passo 7 lista os testes do pipeline separadamente.
- **O Codespace instala só o `requirements.txt`.** O Passo 2 completa as dependências.
