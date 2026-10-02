## OBJETIVO GERAL:
Modelagem da estrutura principal do sistema, identificando as entidades e seus relacionamentos.

Organização das informações tributárias em um formato visual e de fácil compreensão.

Definição das regras de negócio entre contribuintes, tributos, fiscalizações, notificações e demais componentes do sistema.

Redução de ambiguidades nos requisitos, facilitando a comunicação entre equipe de negócio e desenvolvimento.

Planejamento da futura implementação do banco de dados com uma estrutura consistente.

Apoio à documentação técnica do projeto.

Facilitação da manutenção e evolução do sistema, permitindo visualizar impactos de alterações.

## CÓDIGO DO DIAGRAMA ENGENHARIA DE RELACIONAMENTO:
    CONTRIBUINTE {
            string cnpj_cpf PK
            string nome 
            boolean_is_iptu_social 
            string contato
    }

    IMOVEL {
        string inscricao_imobiliaria PK
        string cpf_cnpj_proprietario FK
        string logradouro
        string bairro
        float area_edificada
        string setor_urbano
    }

    DEBITO_TRIBUTARIO {
        string id_debito PK
        string inscricao_imobiliaria FK
        string cpf_cnpj FK
        string tipo_tributo "IPTU ou ISS"
        float valor_debito
        date data_vencimento
        string status_pagamento "Ativo, Quitado, Isento"
    }

    MODELO_PREDICAO {
        string id_modelo PK
        string versao
        float acuracia
        date data_treinamento
    }

    SCORE_RECUPERABILIDADE {
        string id_score PK
        string id_debito FK
        string id_modelo FK
        float score_valor
        string nivel_inadimplencia "CRITICO, ALTO, MEDIO, BAIXO"
        date data_calculo
    }

    LOG_AUDITORIA {
        string id_log PK
        string id_analista FK
        datetime timestamp
        string filtros_aplicados
        string justificativa_lgpd
    }

    ANALISTA_FISCAL {
        string id_analista PK
        string nome
        string perfil "Analista Fiscal ou Procurador"
    }

    CONTRIBUINTE ||--o{ IMOVEL : "possui"
    CONTRIBUINTE ||--o{ DEBITO_TRIBUTARIO : "acumula"
    IMOVEL ||--o{ DEBITO_TRIBUTARIO : "gera"
    DEBITO_TRIBUTARIO ||--|| SCORE_RECUPERABILIDADE : "possui_score"
    MODELO_PREDICAO ||--o{ SCORE_RECUPERABILIDADE : "gera"
    ANALISTA_FISCAL ||--o{ LOG_AUDITORIA : "registra_acesso"
<img width="793" height="767" alt="Captura de tela 2026-09-23 183352" src="https://github.com/user-attachments/assets/f9533e66-296f-4e61-965b-896db183b9a3" />
