# 1. Requisitos para a realização do projeto
- O que se segue são os requisitos do projeto, que foram idealizados (em maioria) na terceira atividade de Engenharia de Software - 2026/2;
- Além disso, acompanha os requisitos as suas respectivas categorias e prioridades enumeradas;
- O objetivo é, em suma, realizar o projeto e contemplar todos os requisitos;
- Todos os Pull Requests desse projeto estarão relacionados com algum requisito de alguma forma.

## 1.1. Especificação de Requisitos Funcionais (RF)

| ID | Nome do Requisito | Descrição / História de Usuário (COMO... QUERO... PARA...) | Critérios de Aceite (Validação) | Valor (1 a 5) |
| :--- | :--- | :--- | :--- | :---: |
| **RF01** | Visualização e Priorização de Devedores | Como analista fiscal da Sefin, quero visualizar o mapa da cidade com o nível de inadimplência e a lista de devedores priorizados, para organizar e direcionar as ações de cobrança administrativa do município. | 1. Exibir mapa interativo da malha urbana de Palmas com marcadores de inadimplência.<br>2. Apresentar ranking ordenado por nível de risco e score de recuperabilidade. | **5** |
| **RF02** | Relatórios Explicativos da Indicação | Como procurador municipal, quero ver relatórios que explicam os motivos de o sistema indicar aquele devedor, para fundamentar a cobrança e dar explicações se o cidadão solicitar. | 1. Exibir a justificativa/fatores de impacto da nota de risco (explicabilidade/SHAP).<br>2. Incluir código hash SHA-256 para auditoria de integridade do relatório. | **5** |
| **RF03** | Filtragem Avançada de Dívidas | Como analista fiscal da Sefin, quero filtrar as dívidas por tipo de imposto (IPTU ou ISS), valor e região/bairro, para montar campanhas de arrecadação direcionadas. | 1. Permitir filtro simultâneo por tributo (IPTU/ISS), faixa de valor e setor censitário.<br>2. Atualizar a lista e o mapa em tempo real conforme os filtros aplicados. | **4** |
| **RF04** | Consulta e Explicação do Risco pelo Cidadão | Como cidadão, quero consultar meus débitos e solicitar a explicação da minha nota de risco no portal, para entender a situação do meu imóvel e exercer meus direitos (Art. 20 da LGPD). | 1. Permitir consulta por CPF/CNPJ ou Inscrição Imobiliária.<br>2. Exibir explicação da nota de risco em linguagem simples e acessível em até 2 segundos. | **3** |
| **RF05** | Simulação e Renegociação de Dívidas | Como cidadão, quero simular o parcelamento e renegociar minhas dívidas diretamente pelo portal, para quitar meus débitos sem precisar ir presencialmente à prefeitura. | 1. Exibir opções de parcelamento conforme legislação municipal.<br>2. Gerar simulação de parcelas e desconto de juros/multa. | **2** |
| **RF06** | Exportação de Dados da Cobrança | Como analista fiscal ou procurador, quero exportar a lista de devedores e relatórios para análise externa ou ajuizamento. | 1. Permitir download em formato CSV de planilha estruturada.<br>2. Permitir exportação em formato PDF formatado para impressão/processo. | **4** |
| **RF07** | Registro Automático de Logs de Auditoria | O sistema deve gravar um registro automático com data, hora e usuário para cada consulta ou previsão realizada. | 1. Salvar no `LogAuditoria` o ID do usuário, ação, parâmetros e timestamp.<br>2. Armazenar os logs por um período mínimo de 5 anos. | **5** |
| **RF08** | Coleta de Dados via API REST | O sistema deve consumir a API REST da Prefeitura de Palmas para obter dados atualizados de arrecadação e dívida ativa. | 1. Tratar autenticação, paginação e erros de comunicação do servidor municipal.<br>2. Persistir os registros coletados no banco de dados local. | **4** |
| **RF09** | Controle de Acesso e Autenticação | O sistema deve restringir a visualização de dados pessoais e fiscais apenas a funcionários autorizados e autenticados. | 1. Exigir login e senha válidos para acesso ao painel interno da Sefin/Procuradoria.<br>2. Bloquear acesso direto a endpoints sensíveis sem token de sessão ativo. | **5** |
| **RF10** | Integração com Geoportal / GIS | O sistema deve integrar com o serviço de cadastro imobiliário para obter a malha urbana espacializada de Palmas. | 1. Buscar coordenadas e limites de bairros/quadras via serviço GIS.<br>2. Renderizar polígonos e marcadores no componente de mapa interativo. | **4** |

---
## 1.2. Requisitos Não Funcionais (RNF)

| ID | Categoria | Descrição da Restrição (com número e condição) | Métrica / Forma de Teste |
| :--- | :--- | :--- | :--- |
| *RNF01* | Proteção de Grupos Vulneráveis | O sistema deve aplicar um filtro automático que garanta 100% de exclusão dos beneficiários do IPTU Social das listas de cobrança preditiva. | Teste unitário de filtro na base de dados garantindo 0 registros do IPTU Social na saída do modelo. |
| *RNF02* | Desempenho / Usabilidade | A consulta de débitos realizada pelo cidadão deve exibir o resultado na tela em no máximo 2 segundos após informar o CPF ou a Inscrição do Imóvel. | Medição do tempo de resposta HTTP/renderização em testes automatizados (tempo < 2.0s). |
| *RNF03* | Explicabilidade / LGPD | O sistema deve gerar a resposta com a explicação da nota de risco do cidadão (Art. 20 da LGPD) em linguagem simples e em no máximo 2 segundos. | Verificação do tempo de geração do trecho explicativo (SHAP/LIME) no limite estipulado. |
| *RNF04* | Privacidade e Segurança | Dados pessoais do cidadão (como CPF e nome) devem ser armazenados com criptografia ou com os números parcialmente ocultos no banco de dados. | Inspeção visual no banco de dados e na interface para validar o mascaramento de CPF (***.123.456-**). |
| *RNF05* | Tecnologia e Reprodutibilidade | O projeto deve ser desenvolvido em Python 3.10+ com dependências isoladas em requirements.txt. | Instalação limpa do ambiente executando o comando pip install -r requirements.txt. |

---
## 1.3. Matriz de Priorização MoSCOW

* **Must Have (no máximo 2):**
  * **RF01** — Visualização no Mapa e Lista Priorizada de Devedores (A entrega central do projeto de inteligência fiscal).
  * **RF02** — Relatórios Explicativos da Indicação da Cobrança (Essencial para a legalidade e transparência das ações da Procuradoria).

* **Should Have (Alta prioridade):**
  * **RF03** — Filtragem por Imposto (IPTU/ISS), Valor e Região (Otimiza o trabalho do analista).
  * **RF06** — Exportação de dados em CSV e PDF.
  * **RF07** — Registro Automático de Logs de Auditoria (LGPD).
  * **RF08** — Coleta de dados via API REST da Prefeitura.
  * **RF09** — Autenticação e Controle de Acesso.
  * **RF10** — Integração com serviço GIS/Geoportal.

* **Could Have (Desejável):**
  * **RF04** — Consulta e solicitação de explicação do risco pelo cidadão no portal (Será liberado após a validação do uso interno pela Sefin).

* **Won't Have (Fora do escopo do MVP por enquanto):**
  * **RF05** — Simulação de parcelamento e renegociação direta de dívidas pelo cidadão (Exige integração complexa com sistemas bancários/arrecadação).