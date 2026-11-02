# Pipeline ETL da SEFIN — Sprint E2

## 1. Objetivo

Ler as receitas orçamentárias da API de transparência (`sgreceitas`) já coletadas em `data/bruto`, tratá-las em DataFrames do **pandas**, validar a qualidade dos registros e carregar os registros confiáveis em uma tabela de integração SQL usando **SQLAlchemy**. As operações são registradas em logs pelo **logging** nativo.

**Atenção ao escopo:** esses registros são de receitas orçamentárias, **não** de contribuintes inadimplentes. Não atribuir dados de IPTU/ISS ou pessoas a registros sem evidência.

**Conferência com o repositório GitHub em 31/10/2026:** `Lucas-George-Oliveira/inteligencia_tributaria` já contém `src/database/schema/V1__create_schema.sql`, com banco **PostgreSQL** e esquema **`tributario`**. As tabelas incluem `contribuinte`, `imovel`, `debito_tributario`, `analista_fiscal`, `log_auditoria`, `modelo_predicao` e `score_recuperabilidade`. Nenhuma delas tem a estrutura de registros de receitas da API. A entrega acrescenta migração **V4**, que cria `tributario.receitas_sefin_etl` sem alterar tabelas do projeto integrador. Revise permissões e convenção de migrações com a equipe do banco antes de executar.

## 2. Organização dos arquivos no repositório já existente

```text
inteligencia_tributaria/
├── .env.example                     NOVO: exemplo de configuração
├── .gitignore                        NOVO: proteções para dados e credenciais
├── .env                             CRIAR LOCALMENTE (não versionar)
├── requirements.txt                 EXISTENTE: preservar
├── requirements-etl.txt             NOVO: dependências da E2
├── requirements-postgres.txt        NOVO: usar caso o banco seja PostgreSQL
├── src/
│   ├── __init__.py                  EXISTENTE: preservar
│   ├── app.py                       EXISTENTE: preservar
│   ├── api/
│   │   └── coleta_dados.py          EXISTENTE: preservar
│   ├── core/
│   │   ├── __init__.py              EXISTENTE: preservar
│   │   ├── grafo_vinculos.py        EXISTENTE: preservar
│   │   └── limpeza_receitas.py      NOVO: tratamento e validação
│   ├── database/
│   │   ├── __init__.py              NOVO: marca o pacote Python (preservar se houver)
│   │   ├── carga_receitas.py        NOVO: carga transacional em lote
│   │   └── schema/
│   │       ├── V1...V3...          EXISTENTES: preservar
│   │       └── V4__create_receitas_sefin_etl.sql  NOVO: migração de receita
│   └── etl_sefin.py                 NOVO: orquestrador
├── data/
│   ├── bruto/
│   │   └── coleta_api_*.json        EXISTENTE: manter o JSON da coleta
│   ├── processado/                 NOVO: CSVs tratados e relatórios JSON
│   └── rejeitados/                 NOVO: CSVs rejeitados para auditoria
├── logs/
│   └── etl_sefin.log                GERADO na execução
├── tests/
│   └── test_etl.py                  NOVO: testes automatizados
└── docs/
    └── GUIA_ETL_E2.md               NOVO: esta documentação
```

**Observação:** este pacote é uma entrega incremental. **Não substitua** arquivos `src/app.py`, `src/api/coleta_dados.py`, `src/core/__init__.py`, `requirements.txt` e os códigos que vocês já criaram.

## 3. Instalação (terminal do Codespace, aberto na raiz do projeto)

```bash
python -m pip install -r requirements-etl.txt
```

O banco da Sprint 2 é PostgreSQL. O repositório já referencia `psycopg2-binary` no `requirements.txt`. Para instalar isoladamente as dependências de banco e ETL:

```bash
python -m pip install -r requirements-postgres.txt
```

## 4. Testar sem tocar no banco

O comando abaixo lê automaticamente o JSON `coleta_api_*.json` mais recente dentro de `data/bruto`:

```bash
python -m src.etl_sefin --sem-carga
```

Ou aponte para o arquivo de coleta já exibido na sua captura:

```bash
python -m src.etl_sefin --arquivo data/bruto/coleta_api_20261030_214038.json --sem-carga
```

Para testar apenas com dados fictícios incluídos na entrega:

```bash
python -m src.etl_sefin --arquivo exemplos/receitas_exemplo.json --sem-carga
```

O programa grava:

- `data/processado/receitas_tratadas_<timestamp>.csv`
- `data/rejeitados/receitas_rejeitadas_<timestamp>.csv`
- `data/processado/resumo_etl_<timestamp>.json`
- `logs/etl_sefin.log`

`total_bruto = validos + rejeitados + duplicados_exatos`. Linhas conflitantes são contabilizadas como rejeitadas. O `total` retornado em cada item da API indica o total informado pelo servidor: **não equivale necessariamente à quantidade de registros efetivamente coletada**, que no código original é limitada pelo número de páginas (`limite_paginas=3`).

## 5. Banco de dados da Sprint 2

O esquema **real** do banco foi localizado e conferido no GitHub: **`tributario`**, em PostgreSQL. Ele não inclui uma tabela destinada a dados de receitas orçamentárias. Por isso, a solução utiliza uma **tabela de integração separada**, `tributario.receitas_sefin_etl`, sem modificar `tributario.debito_tributario` nem fabricar dados pessoais.

Antes de fazer carga no banco compartilhado, confirme com o responsável pelo PostgreSQL se a tabela V4 pode ser criada em `tributario`. **Não mude `ETL_TABELA` para `debito_tributario`**: os dados da API não possuem CPF/CNPJ, valor de dívida, vencimento ou status de pagamento. Essa ligação exigiria uma fonte de dados tributários individualizados e uma implementação ETL específica.

### Passo A — criar `.env`

Copie `.env.example` para `.env`, na raiz do repositório. Configure uma URL real, **sem expor senha em commits ou prints**:

```dotenv
ETL_DATABASE_URL=postgresql+psycopg2://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO
ETL_TABELA=receitas_sefin_etl
# ETL_SCHEMA=public
```

Se quiser fazer uma prova de conceito local e independente do banco da Sprint 2, use em vez disso:

```dotenv
ETL_DATABASE_URL=sqlite:///./data/sefin_demo.db
ETL_TABELA=receitas_sefin_etl
# ETL_SCHEMA=tributario  # opcional: detectado automaticamente no PostgreSQL
```

### Passo B — criar a tabela com a migração V4 (recomendado)

Peça ao responsável pelo banco para aplicar o script **`src/database/schema/V4__create_receitas_sefin_etl.sql`** no banco PostgreSQL de desenvolvimento **após V1**, usando o processo de migração autorizado pela equipe. A migração é aditiva, com `CREATE TABLE IF NOT EXISTS`; não exclui nenhuma tabela. Depois rode a carga sem `--criar-tabela`:

```bash
python -m src.etl_sefin
```

### Alternativa — primeira carga com criação EXPLÍCITA da tabela

```bash
python -m src.etl_sefin --criar-tabela
```

Esse comando cria `tributario.receitas_sefin_etl` somente se ela não existir e carrega os registros válidos (requer o esquema `tributario` existente e permissão `CREATE`). Caso já tenha aplicado a migração V4, não é necessário usar essa opção. Para novas execuções, quando a tabela já estiver criada:

```bash
python -m src.etl_sefin
```

### Passo C — consultar dados no PostgreSQL

```sql
SELECT COUNT(*) AS linhas_carregadas FROM tributario.receitas_sefin_etl;
SELECT ano, mes, orgao, codigo, descricao, valor_arrecado_mes
FROM tributario.receitas_sefin_etl
ORDER BY ano DESC, mes DESC
LIMIT 10;
```

**Importante:** o pipeline é idempotente: novo registro = `INSERT`, registro com a mesma chave e conteúdo alterado = `UPDATE`, mesma chave sem alteração = ignorado. Cada execução usa transação única, que faz `ROLLBACK` integral se alguma operação falhar. O identificador do registro é um SHA-256 de órgão, unidade, ano, mês, código, código original e descrição. Essa é **uma chave lógica provisória**, porque a API mostrada não fornece um ID individual único. Se houver duas linhas com a mesma chave mas conteúdo diferente **na mesma coleta**, as duas são rejeitadas para revisão, em vez de uma sobrescrever a outra sem justificativa.

## 6. Executar extração + transformação + carga

Opcionalmente, para chamar o coletor existente antes de fazer o resto:

```bash
python -m src.etl_sefin --coletar --paginas 3
```

`--coletar` não faz uma coleta completa por padrão; o coletor original só consulta a quantidade de páginas indicada. O programa mantém o arquivo bruto novo, sem modificar os dados originais.

## 7. O que a limpeza faz

| Situação | Regra adotada |
|---|---|
| `unidade_nome`, `unidade_id` nulos | Mantidos como `NULL` (não inventar unidade) |
| `valor_arrecado_mes` nulo | Mantido como `NULL`; não converter para 0 |
| Valores financeiros como `29.442.709,54` ou `29442709.54` | Convertidos para `Decimal('29442709.54')` |
| Monetário inválido (`abc`, separadores inconsistentes) | Rejeitar e registrar o motivo |
| `ano` ausente/inválido ou `mes` fora de 1 a 12 | Rejeitar |
| Órgão, código ou descrição ausentes | Rejeitar |
| Todos os campos monetários ausentes | Rejeitar |
| Linhas logicamente idênticas na mesma coleta | Remover duplicata e contabilizar |
| Mesma chave lógica, mas conteúdos diferentes na mesma coleta | Rejeitar grupo inteiro e investigar |
| Valores monetários negativos | Preservar (podem representar estornos/ajustes) |
| Campo `total` do JSON | Não inserir como receita; é metadado do servidor |

## 8. Logs e testes

```bash
python -m pytest tests/ -v
```

Os testes verificam a leitura e limpeza monetária, duplicatas, nulos, rejeições, controle de conflitos, inserção, reexecução sem duplicar, atualização e impedimento da criação não autorizada de tabela.

O log `logs/etl_sefin.log` registra horário de execução, arquivo de origem, quantidades tratadas, quantidades carregadas e erros com traceback. Os arquivos de log giram ao atingir 5 MB, mantendo até três cópias anteriores.

## 9. Segurança e limites

- Não comitar `.env`, credenciais, `data/bruto/*.json`, CSVs produzidos ou logs. O novo `.gitignore` da entrega já contém as regras para credenciais, JSONs, saídas e logs. Se houver outro `.gitignore` local, **mescle sem sobrescrever**.
- Não usar dados de receitas como se identificassem contribuintes de IPTU/ISS.
- Conferir com a equipe de banco o SGBD, esquema, permissões, migrações e nomes de tabelas antes de conectar a carga ao banco compartilhado.
- Este fluxo processa arquivos coletados em lotes. Sem um identificador exclusivo da API, a chave lógica precisa ser homologada antes de produção.
- Verificar qualidade dos rejeitados antes de considerar a coleta integralmente carregada. Falhas de validação individual não interrompem a carga dos demais; ausência de qualquer válido interrompe com erro.

## 10. Compatibilidade com o GitHub consultado

- O branch visto no Codespace, `feature_etl_api`, existe no repositório; neste momento seu commit está igual ao de `main`. Não suponha que alterações locais não commitadas estejam no GitHub.
- `requirements.txt` original já declara `pandas`, `requests`, `sqlalchemy` e `psycopg2-binary`. Não o substitua; use `requirements-etl.txt` e `requirements-postgres.txt` para ter uma instalação independente da E2.
- As migrações V1, V2 e V3 são da Sprint 2 e não devem ser sobrescritas. A V4 é aditiva.
- Evite novos commits diretos em `main`; o README solicita revisão por Pull Request.

Arquivos-fonte conferidos: https://github.com/Lucas-George-Oliveira/inteligencia_tributaria/tree/main/src/database/schema e https://github.com/Lucas-George-Oliveira/inteligencia_tributaria/blob/main/requirements.txt.
