--
-- PostgreSQL database dump
--

\restrict dcdUazv1bgpNj45amN5oOSuoVcWccNiqlt1fIcMc8fMPACVOkgE52JYYmdbDom7

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tributario; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA tributario;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analista_fiscal; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.analista_fiscal (
    id_analista character varying(36) DEFAULT (gen_random_uuid())::text NOT NULL,
    nome character varying(150) NOT NULL,
    perfil character varying(50) NOT NULL,
    CONSTRAINT chk_perfil CHECK (((perfil)::text = ANY ((ARRAY['ADMINISTRADOR'::character varying, 'AUDITOR'::character varying, 'CONSULTOR'::character varying])::text[])))
);


--
-- Name: TABLE analista_fiscal; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.analista_fiscal IS 'Analistas fiscais com acesso ao sistema de controle de inadimplência.';


--
-- Name: contribuinte; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.contribuinte (
    cpf_cnpj character varying(18) NOT NULL,
    nome character varying(150) NOT NULL,
    is_iptu_social boolean DEFAULT false NOT NULL,
    contato character varying(100),
    CONSTRAINT chk_cpf_cnpj_formato CHECK ((((cpf_cnpj)::text ~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$'::text) OR ((cpf_cnpj)::text ~ '^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$'::text)))
);


--
-- Name: TABLE contribuinte; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.contribuinte IS 'Cadastro de contribuintes (PF e PJ) do município.';


--
-- Name: COLUMN contribuinte.is_iptu_social; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.contribuinte.is_iptu_social IS 'TRUE quando o contribuinte tem isenção/redução social de IPTU.';


--
-- Name: debito_tributario; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.debito_tributario (
    id_debito character varying(36) DEFAULT (gen_random_uuid())::text NOT NULL,
    inscricao_imobiliaria character varying(20),
    cpf_cnpj character varying(18) NOT NULL,
    tipo_tributo character varying(4) NOT NULL,
    valor_debito numeric(15,2) NOT NULL,
    data_vencimento date NOT NULL,
    status_pagamento character varying(20) DEFAULT 'PENDENTE'::character varying NOT NULL,
    CONSTRAINT chk_iptu_requer_imovel CHECK ((((tipo_tributo)::text <> 'IPTU'::text) OR (inscricao_imobiliaria IS NOT NULL))),
    CONSTRAINT chk_status_pagamento CHECK (((status_pagamento)::text = ANY ((ARRAY['PENDENTE'::character varying, 'PAGO'::character varying, 'VENCIDO'::character varying, 'PARCELADO'::character varying, 'CANCELADO'::character varying])::text[]))),
    CONSTRAINT chk_tipo_tributo CHECK (((tipo_tributo)::text = ANY ((ARRAY['IPTU'::character varying, 'ISS'::character varying])::text[]))),
    CONSTRAINT debito_tributario_valor_debito_check CHECK ((valor_debito > (0)::numeric))
);


--
-- Name: TABLE debito_tributario; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.debito_tributario IS 'Débitos tributários lançados por contribuinte (IPTU e ISS).';


--
-- Name: COLUMN debito_tributario.status_pagamento; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.debito_tributario.status_pagamento IS 'PENDENTE | PAGO | VENCIDO | PARCELADO | CANCELADO';


--
-- Name: imovel; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.imovel (
    inscricao_imobiliaria character varying(20) NOT NULL,
    cpf_cnpj_proprietario character varying(18) NOT NULL,
    logradouro character varying(200) NOT NULL,
    bairro character varying(100) NOT NULL,
    area_edificada numeric(10,2) NOT NULL,
    setor_urbano character varying(20) NOT NULL,
    CONSTRAINT imovel_area_edificada_check CHECK ((area_edificada > (0)::numeric))
);


--
-- Name: TABLE imovel; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.imovel IS 'Cadastro imobiliário urbano para fins de lançamento de IPTU.';


--
-- Name: COLUMN imovel.inscricao_imobiliaria; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.imovel.inscricao_imobiliaria IS 'Chave de inscrição cadastral do imóvel no município.';


--
-- Name: COLUMN imovel.setor_urbano; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.imovel.setor_urbano IS 'Código do setor/zona urbana para cálculo da alíquota IPTU.';


--
-- Name: log_auditoria; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.log_auditoria (
    id_log character varying(36) DEFAULT (gen_random_uuid())::text NOT NULL,
    id_analista character varying(36) NOT NULL,
    timestamp_acesso timestamp without time zone DEFAULT now() NOT NULL,
    filtros_aplicados text,
    justificativa_lgpd text NOT NULL
);


--
-- Name: TABLE log_auditoria; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.log_auditoria IS 'Trilha de auditoria de acessos dos analistas fiscais (conformidade LGPD).';


--
-- Name: COLUMN log_auditoria.justificativa_lgpd; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.log_auditoria.justificativa_lgpd IS 'Justificativa obrigatória para acesso a dados pessoais (LGPD Art. 37).';


--
-- Name: modelo_predicao; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.modelo_predicao (
    id_modelo character varying(36) DEFAULT (gen_random_uuid())::text NOT NULL,
    versao character varying(50) NOT NULL,
    acuracia numeric(5,4) NOT NULL,
    data_treinamento date NOT NULL,
    CONSTRAINT modelo_predicao_acuracia_check CHECK (((acuracia >= (0)::numeric) AND (acuracia <= (1)::numeric)))
);


--
-- Name: TABLE modelo_predicao; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.modelo_predicao IS 'Registro de versões dos modelos preditivos de inadimplência.';


--
-- Name: COLUMN modelo_predicao.acuracia; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.modelo_predicao.acuracia IS 'Acurácia do modelo no conjunto de teste (0.0 a 1.0).';


--
-- Name: score_recuperabilidade; Type: TABLE; Schema: tributario; Owner: -
--

CREATE TABLE tributario.score_recuperabilidade (
    id_score character varying(36) DEFAULT (gen_random_uuid())::text NOT NULL,
    id_debito character varying(36) NOT NULL,
    id_modelo character varying(36) NOT NULL,
    score_valor numeric(5,4) NOT NULL,
    nivel_inadimplencia character varying(20) NOT NULL,
    data_calculo date DEFAULT CURRENT_DATE NOT NULL,
    CONSTRAINT chk_nivel_inadimplencia CHECK (((nivel_inadimplencia)::text = ANY ((ARRAY['BAIXO'::character varying, 'MEDIO'::character varying, 'ALTO'::character varying, 'CRITICO'::character varying])::text[]))),
    CONSTRAINT score_recuperabilidade_score_valor_check CHECK (((score_valor >= (0)::numeric) AND (score_valor <= (1)::numeric)))
);


--
-- Name: TABLE score_recuperabilidade; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON TABLE tributario.score_recuperabilidade IS 'Score de recuperabilidade do débito gerado pelos modelos preditivos.';


--
-- Name: COLUMN score_recuperabilidade.score_valor; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.score_recuperabilidade.score_valor IS 'Probabilidade de pagamento (0 = certeza de inadimplência, 1 = certeza de pagamento).';


--
-- Name: COLUMN score_recuperabilidade.nivel_inadimplencia; Type: COMMENT; Schema: tributario; Owner: -
--

COMMENT ON COLUMN tributario.score_recuperabilidade.nivel_inadimplencia IS 'Classificação: BAIXO | MEDIO | ALTO | CRITICO';


--
-- Data for Name: analista_fiscal; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.analista_fiscal (id_analista, nome, perfil) FROM stdin;
analista-001	Roberto Alves Martins	ADMINISTRADOR
analista-002	Silvia Torres Campos	AUDITOR
analista-003	Marcos Vinícius Souza	CONSULTOR
analista-004	Patrícia Neves Lima	AUDITOR
\.


--
-- Data for Name: contribuinte; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.contribuinte (cpf_cnpj, nome, is_iptu_social, contato) FROM stdin;
456.789.123-87	Ana Paula Rodrigues	f	anapaula@gmail.com
321.654.987-12	Carlos Eduardo Mendes	t	(11) 91234-5678
654.321.098-55	Fernanda Lima Costa	f	fernanda.lima@empresa.com
11.222.333/0001-44	Comércio Rápido Ltda	f	fiscal@comerciorapido.com.br
55.666.777/0001-88	Serviços Tech ME	f	contato@servicostech.com.br
99.888.777/0001-11	Construtora Urbana S/A	f	financeiro@construtoraurbana.com
123.456.789-09	Maria da Silva Souza	t	maria.santos@email.com
987.654.321-00	Flavin do Pneu	f	(11) 98765-4321
\.


--
-- Data for Name: debito_tributario; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.debito_tributario (id_debito, inscricao_imobiliaria, cpf_cnpj, tipo_tributo, valor_debito, data_vencimento, status_pagamento) FROM stdin;
deb-001	0001-0001-001	123.456.789-09	IPTU	850.00	2026-02-28	PAGO
deb-002	0001-0001-002	987.654.321-00	IPTU	1200.00	2026-03-31	VENCIDO
deb-003	0001-0001-003	456.789.123-87	IPTU	600.00	2026-06-30	PENDENTE
deb-004	0001-0001-004	321.654.987-12	IPTU	120.00	2026-02-28	PAGO
deb-005	0001-0001-005	654.321.098-55	IPTU	3500.00	2026-03-31	PARCELADO
deb-006	0002-0001-001	11.222.333/0001-44	IPTU	8700.00	2026-01-31	VENCIDO
deb-007	0002-0001-002	99.888.777/0001-11	IPTU	22000.00	2025-12-31	VENCIDO
deb-008	\N	55.666.777/0001-88	ISS	4500.00	2026-04-30	PENDENTE
deb-009	\N	987.654.321-00	ISS	350.00	2026-02-28	VENCIDO
deb-010	\N	11.222.333/0001-44	ISS	1800.00	2026-03-31	PAGO
\.


--
-- Data for Name: imovel; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.imovel (inscricao_imobiliaria, cpf_cnpj_proprietario, logradouro, bairro, area_edificada, setor_urbano) FROM stdin;
0001-0001-001	123.456.789-09	Rua das Flores, 123	Centro	85.50	SU-01
0001-0001-002	987.654.321-00	Av. Brasil, 456, Ap. 32	Jardim América	120.00	SU-02
0001-0001-003	456.789.123-87	Rua Palmeiras, 789	Vila Nova	60.75	SU-01
0001-0001-004	321.654.987-12	Travessa das Acácias, 10	Bela Vista	45.00	SU-03
0001-0001-005	654.321.098-55	Alameda Santos, 2000, Ap. 5	Jardins	200.00	SU-02
0002-0001-001	11.222.333/0001-44	Av. Paulista, 1500, Lj. 3	Bela Vista	350.00	SU-02
0002-0001-002	99.888.777/0001-11	Rua Industrial, 500	Distrito Ind.	800.00	SU-04
\.


--
-- Data for Name: log_auditoria; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.log_auditoria (id_log, id_analista, timestamp_acesso, filtros_aplicados, justificativa_lgpd) FROM stdin;
log-001	analista-002	2026-09-10 08:30:00	{"tipo_tributo":"IPTU","status":"VENCIDO","setor":"SU-02"}	Auditoria trimestral de inadimplência IPTU - Resolução Municipal 42/2026
log-002	analista-002	2026-09-15 14:10:00	{"nivel_inadimplencia":"CRITICO"}	Levantamento para notificação extrajudicial - Processo Adm. 2026/0091
log-003	analista-001	2026-09-20 09:00:00	{"tipo_tributo":"ISS","status":"PENDENTE"}	Revisão administrativa mensal - Competência Setembro/2026
log-004	analista-004	2026-09-23 16:45:00	{"cpf_cnpj":"11.222.333/0001-44"}	Consulta pontual solicitada pelo Departamento Jurídico - Ofício DJ-205/2026
\.


--
-- Data for Name: modelo_predicao; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.modelo_predicao (id_modelo, versao, acuracia, data_treinamento) FROM stdin;
modelo-v1	v1.0-regressao-logistica	0.7823	2025-06-01
modelo-v2	v2.0-random-forest	0.8541	2025-11-15
modelo-v3	v3.0-gradient-boosting	0.8912	2026-03-10
\.


--
-- Data for Name: score_recuperabilidade; Type: TABLE DATA; Schema: tributario; Owner: -
--

COPY tributario.score_recuperabilidade (id_score, id_debito, id_modelo, score_valor, nivel_inadimplencia, data_calculo) FROM stdin;
score-001	deb-001	modelo-v3	0.9800	BAIXO	2026-09-01
score-002	deb-002	modelo-v3	0.1250	CRITICO	2026-09-01
score-003	deb-003	modelo-v3	0.6200	MEDIO	2026-09-01
score-004	deb-004	modelo-v3	0.9500	BAIXO	2026-09-01
score-005	deb-005	modelo-v3	0.4800	MEDIO	2026-09-01
score-006	deb-006	modelo-v3	0.0950	CRITICO	2026-09-01
score-007	deb-007	modelo-v3	0.0320	CRITICO	2026-09-01
score-008	deb-008	modelo-v3	0.3100	ALTO	2026-09-01
score-009	deb-009	modelo-v3	0.2200	ALTO	2026-09-01
score-010	deb-010	modelo-v3	0.9600	BAIXO	2026-09-01
score-011	deb-002	modelo-v2	0.1580	CRITICO	2026-06-01
score-012	deb-007	modelo-v2	0.0610	CRITICO	2026-06-01
\.


--
-- Name: analista_fiscal pk_analista_fiscal; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.analista_fiscal
    ADD CONSTRAINT pk_analista_fiscal PRIMARY KEY (id_analista);


--
-- Name: contribuinte pk_contribuinte; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.contribuinte
    ADD CONSTRAINT pk_contribuinte PRIMARY KEY (cpf_cnpj);


--
-- Name: debito_tributario pk_debito_tributario; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.debito_tributario
    ADD CONSTRAINT pk_debito_tributario PRIMARY KEY (id_debito);


--
-- Name: imovel pk_imovel; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.imovel
    ADD CONSTRAINT pk_imovel PRIMARY KEY (inscricao_imobiliaria);


--
-- Name: log_auditoria pk_log_auditoria; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.log_auditoria
    ADD CONSTRAINT pk_log_auditoria PRIMARY KEY (id_log);


--
-- Name: modelo_predicao pk_modelo_predicao; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.modelo_predicao
    ADD CONSTRAINT pk_modelo_predicao PRIMARY KEY (id_modelo);


--
-- Name: score_recuperabilidade pk_score_recuperabilidade; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.score_recuperabilidade
    ADD CONSTRAINT pk_score_recuperabilidade PRIMARY KEY (id_score);


--
-- Name: modelo_predicao uq_modelo_versao; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.modelo_predicao
    ADD CONSTRAINT uq_modelo_versao UNIQUE (versao);


--
-- Name: score_recuperabilidade uq_score_debito_modelo; Type: CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.score_recuperabilidade
    ADD CONSTRAINT uq_score_debito_modelo UNIQUE (id_debito, id_modelo);


--
-- Name: idx_debito_contribuinte; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_debito_contribuinte ON tributario.debito_tributario USING btree (cpf_cnpj);


--
-- Name: idx_debito_status; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_debito_status ON tributario.debito_tributario USING btree (status_pagamento);


--
-- Name: idx_debito_tipo_vencimento; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_debito_tipo_vencimento ON tributario.debito_tributario USING btree (tipo_tributo, data_vencimento);


--
-- Name: idx_imovel_proprietario; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_imovel_proprietario ON tributario.imovel USING btree (cpf_cnpj_proprietario);


--
-- Name: idx_log_analista; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_log_analista ON tributario.log_auditoria USING btree (id_analista, timestamp_acesso);


--
-- Name: idx_score_nivel; Type: INDEX; Schema: tributario; Owner: -
--

CREATE INDEX idx_score_nivel ON tributario.score_recuperabilidade USING btree (nivel_inadimplencia);


--
-- Name: debito_tributario fk_debito_contribuinte; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.debito_tributario
    ADD CONSTRAINT fk_debito_contribuinte FOREIGN KEY (cpf_cnpj) REFERENCES tributario.contribuinte(cpf_cnpj) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: debito_tributario fk_debito_imovel; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.debito_tributario
    ADD CONSTRAINT fk_debito_imovel FOREIGN KEY (inscricao_imobiliaria) REFERENCES tributario.imovel(inscricao_imobiliaria) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: imovel fk_imovel_contribuinte; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.imovel
    ADD CONSTRAINT fk_imovel_contribuinte FOREIGN KEY (cpf_cnpj_proprietario) REFERENCES tributario.contribuinte(cpf_cnpj) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: log_auditoria fk_log_analista; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.log_auditoria
    ADD CONSTRAINT fk_log_analista FOREIGN KEY (id_analista) REFERENCES tributario.analista_fiscal(id_analista) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: score_recuperabilidade fk_score_debito; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.score_recuperabilidade
    ADD CONSTRAINT fk_score_debito FOREIGN KEY (id_debito) REFERENCES tributario.debito_tributario(id_debito) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: score_recuperabilidade fk_score_modelo; Type: FK CONSTRAINT; Schema: tributario; Owner: -
--

ALTER TABLE ONLY tributario.score_recuperabilidade
    ADD CONSTRAINT fk_score_modelo FOREIGN KEY (id_modelo) REFERENCES tributario.modelo_predicao(id_modelo) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict dcdUazv1bgpNj45amN5oOSuoVcWccNiqlt1fIcMc8fMPACVOkgE52JYYmdbDom7

