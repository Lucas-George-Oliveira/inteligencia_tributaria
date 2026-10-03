--
-- PostgreSQL database dump
--

\restrict fCwfcbcZ4jjnd6JAAXRFZemTYnbmd84gNbsRu9EeZJgbZLTLJGmOHZq18PuFgKO

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

\unrestrict fCwfcbcZ4jjnd6JAAXRFZemTYnbmd84gNbsRu9EeZJgbZLTLJGmOHZq18PuFgKO

