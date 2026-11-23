"""
Testes do RNF01 — Proteção do IPTU Social (Sprint 5, E3).

Prova, com o pipeline completo sobre a carteira sintética, que nenhum
beneficiário do IPTU Social (idosos, aposentados, pensionistas e pessoas com
deficiência de baixa renda) recebe ação preditiva de cobrança.

Rodar: python -m pytest tests/test_iptu_social.py -v
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml.divisao_temporal import dividir_temporal
from src.ml.gerar_historico_sintetico import gerar_historico
from src.ml.preparar_base import preparar_base
from src.ml.protecao_iptu_social import (
    COLUNA_GRUPO,
    GRUPOS_PROTEGIDOS,
    ViolacaoProtecaoIPTUSocial,
    classificar_protecao,
    eh_grupo_protegido,
    excluir_grupos_protegidos,
    garantir_sem_protegidos,
    ids_protegidos,
    normalizar_indicador,
    remover_protegidos_da_saida,
)
from src.ml.scoring_recuperabilidade import gerar_scoring_recuperabilidade

CAMINHO_BRUTO = Path("data/bruto/carteira_contribuintes_sintetica.csv")
CAMINHO_CARTEIRA = Path("data/processado/carteira_teste_escorada.csv")
CAMINHO_MODELO = Path("models/modelo_campeao_recuperabilidade.joblib")

TOTAL_CARTEIRA = 20_000
TOTAL_BENEFICIARIOS = 1_393

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def carteira_bruta() -> pd.DataFrame:
    return pd.read_csv(CAMINHO_BRUTO, sep=";", encoding="utf-8-sig", dtype={"id_contribuinte": str})


@pytest.fixture(scope="module")
def protegidos(carteira_bruta) -> frozenset:
    return ids_protegidos(carteira_bruta)


@pytest.fixture(scope="module")
def saida_pipeline(carteira_bruta) -> pd.DataFrame:
    """
    Pipeline completo, do cadastro bruto ao score:
    preparar_base -> histórico de 12 meses -> split temporal -> scoring.

    Nenhuma lista de protegidos é passada ao scoring: a exclusão tem de vir
    do próprio pipeline. A conferência é feita de forma independente nos testes.
    """
    historico = gerar_historico(carteira_bruta)
    _, _, teste = dividir_temporal(historico, coluna_data="data_referencia_simulada")
    return gerar_scoring_recuperabilidade(teste, caminho_modelo=str(CAMINHO_MODELO))


def _registro(**extras) -> dict:
    """Contribuinte mínimo válido para o modelo."""
    base = {
        "id_contribuinte": "teste",
        "area_construida_m2": 120.0,
        "valor_venal": 250000.0,
        "valor_iptu_anual": 2000.0,
        "distancia_centro_km": 3.5,
        "exercicios_inadimplentes_5a": 2,
        "tempo_inadimplencia_dias": 400,
        "valor_divida_consolidada": 5000.0,
        "qtd_parcelamentos_anteriores": 1,
        "parcelamento_rompido": 0,
        "qtd_notificacoes": 2,
        "tipo_imovel": "residencial",
        "setor_urbano": "Taquaralto",
    }
    base.update(extras)
    return base


# ---------------------------------------------------------------------------
# 1. Pipeline completo sobre a carteira sintética
# ---------------------------------------------------------------------------
def test_carteira_sintetica_tem_1393_beneficiarios(carteira_bruta, protegidos):
    assert len(carteira_bruta) == TOTAL_CARTEIRA
    assert len(protegidos) == TOTAL_BENEFICIARIOS


def test_pipeline_completo_nao_escora_nenhum_beneficiario(saida_pipeline, protegidos):
    """RNF01: 0 beneficiários na saída do modelo."""
    na_saida = set(saida_pipeline["id_contribuinte"].astype(str)) & protegidos
    assert len(na_saida) == 0, f"{len(na_saida)} beneficiário(s) receberam score"


def test_pipeline_nao_exclui_quem_nao_e_protegido(saida_pipeline, carteira_bruta, protegidos):
    """A regra é exata: todos os não beneficiários continuam sendo escorados."""
    nao_protegidos = set(carteira_bruta["id_contribuinte"]) - protegidos
    assert set(saida_pipeline["id_contribuinte"].astype(str)) == nao_protegidos
    assert len(nao_protegidos) == TOTAL_CARTEIRA - TOTAL_BENEFICIARIOS


def test_nenhuma_acao_de_cobranca_para_beneficiarios(saida_pipeline, protegidos):
    """Ranking e ação recomendada saem apenas para não beneficiários."""
    com_acao = saida_pipeline[saida_pipeline["acao_recomendada_sefin"].notna()]
    assert not com_acao["id_contribuinte"].astype(str).isin(protegidos).any()
    garantir_sem_protegidos(saida_pipeline, protegidos)  # não pode levantar erro


def test_saida_nao_carrega_indicador_nem_grupo(saida_pipeline):
    """O indicador (e o código do grupo, que pode revelar deficiência) não chega à saída."""
    for coluna in ("is_iptu_social", "iptu_social", "boolean_is_iptu_social", COLUNA_GRUPO):
        assert coluna not in saida_pipeline.columns


def test_carteira_escorada_versionada_nao_tem_beneficiarios(protegidos):
    """Artefato lido pelo painel (data/processado/carteira_teste_escorada.csv)."""
    carteira = pd.read_csv(CAMINHO_CARTEIRA, sep=";", dtype={"id_contribuinte": str})
    assert not carteira["id_contribuinte"].isin(protegidos).any()


# ---------------------------------------------------------------------------
# 2. Trava na saída: se um beneficiário vazar, o pipeline barra
# ---------------------------------------------------------------------------
def test_trava_detecta_beneficiario_injetado_na_saida(saida_pipeline, protegidos):
    vazado = saida_pipeline.head(1).assign(id_contribuinte=sorted(protegidos)[0])
    contaminada = pd.concat([saida_pipeline.head(50), vazado], ignore_index=True)

    with pytest.raises(ViolacaoProtecaoIPTUSocial):
        garantir_sem_protegidos(contaminada, protegidos)

    limpa, removidos = remover_protegidos_da_saida(contaminada, protegidos)
    assert removidos == 1
    garantir_sem_protegidos(limpa, protegidos)


def test_trava_detecta_saida_com_indicador_verdadeiro():
    saida = pd.DataFrame([_registro(id_contribuinte="x", is_iptu_social=True)])
    with pytest.raises(ViolacaoProtecaoIPTUSocial):
        garantir_sem_protegidos(saida, protegidos=[])


def test_scoring_exclui_beneficiario_se_receber_base_com_indicador(carteira_bruta):
    """Mesmo chamado direto, sem preparar_base, o scoring não escora beneficiário."""
    amostra = pd.concat([
        carteira_bruta[carteira_bruta["iptu_social"] == 1].head(5),
        carteira_bruta[carteira_bruta["iptu_social"] == 0].head(5),
    ])
    resultado = gerar_scoring_recuperabilidade(amostra, caminho_modelo=str(CAMINHO_MODELO))
    assert len(resultado) == 5
    assert set(resultado["id_contribuinte"]) == set(amostra.loc[amostra["iptu_social"] == 0, "id_contribuinte"])


def test_scoring_com_lista_de_protegidos_remove_e_confere(carteira_bruta, protegidos):
    preparada = preparar_base(carteira_bruta)
    vazado = carteira_bruta[carteira_bruta["iptu_social"] == 1].head(3).drop(columns="iptu_social")
    entrada = pd.concat([preparada.head(20), vazado], ignore_index=True)

    resultado = gerar_scoring_recuperabilidade(
        entrada, caminho_modelo=str(CAMINHO_MODELO), ids_protegidos=protegidos)
    assert len(resultado) == 20
    assert not resultado["id_contribuinte"].isin(protegidos).any()


def test_painel_nao_exibe_beneficiario(tmp_path, protegidos):
    """O ranking do painel lê carregar_carteira(); ela retira qualquer beneficiário."""
    pytest.importorskip("streamlit")
    pytest.importorskip("altair")
    pytest.importorskip("pydeck")
    from src.painel.painel_sefin import carregar_carteira

    carteira = pd.read_csv(CAMINHO_CARTEIRA, sep=";", dtype={"id_contribuinte": str})
    ultima = carteira["data_referencia_simulada"].max()
    vazado = carteira[carteira["data_referencia_simulada"] == ultima].head(1).assign(
        id_contribuinte=sorted(protegidos)[0])
    caminho = tmp_path / "carteira.csv"
    pd.concat([carteira, vazado]).to_csv(caminho, sep=";", index=False)

    exibida = carregar_carteira(caminho)
    assert not exibida["id_contribuinte"].isin(protegidos).any()


# ---------------------------------------------------------------------------
# 3. Casos de borda do indicador
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("valor", [True, 1, 1.0, np.int64(1), np.bool_(True), "1", "true", "Sim", " S ", "TRUE"])
def test_indicador_verdadeiro(valor):
    assert normalizar_indicador(valor) is True


@pytest.mark.parametrize("valor", [False, 0, 0.0, np.int64(0), np.bool_(False), "0", "false", "não", "nao", "N"])
def test_indicador_falso(valor):
    assert normalizar_indicador(valor) is False


@pytest.mark.parametrize("valor", [None, np.nan, pd.NA, "", "  ", "talvez", 2, -1, 0.5, "2"])
def test_indicador_nulo_ou_invalido_e_indefinido(valor):
    assert normalizar_indicador(valor) is None


@pytest.mark.parametrize("valor", [None, np.nan, "", "talvez", 2, -1])
def test_indicador_indefinido_e_protegido_por_padrao(valor):
    """Fail-safe: na dúvida, o contribuinte não recebe ação preditiva."""
    df = pd.DataFrame([_registro(is_iptu_social=valor)])
    classificacao = classificar_protecao(df)
    assert classificacao["protegido"].iloc[0]
    assert classificacao["motivo"].iloc[0] == "indicador_indefinido"
    assert preparar_base(df).empty


@pytest.mark.parametrize("valor", [None, np.nan, "talvez", 2])
def test_politica_erro_interrompe_com_indicador_indefinido(valor):
    df = pd.DataFrame([_registro(is_iptu_social=valor)])
    with pytest.raises(ValueError, match="nulos ou inválidos"):
        preparar_base(df, politica_indefinido="erro")


def test_politica_desconhecida_e_rejeitada():
    with pytest.raises(ValueError, match="Política inválida"):
        classificar_protecao(pd.DataFrame([_registro(is_iptu_social=0)]), politica="ignorar")


def test_base_sem_coluna_de_iptu_social_e_rejeitada():
    """Sem o indicador não dá para garantir o RNF01: o pipeline para."""
    with pytest.raises(ValueError, match="IPTU Social"):
        preparar_base(pd.DataFrame([_registro()]))


@pytest.mark.parametrize("coluna", ["is_iptu_social", "iptu_social", "boolean_is_iptu_social"])
def test_aceita_os_nomes_de_coluna_do_projeto(coluna):
    df = pd.DataFrame([_registro(id_contribuinte="a", **{coluna: 1}),
                       _registro(id_contribuinte="b", **{coluna: 0})])
    assert list(eh_grupo_protegido(df)) == [True, False]
    assert list(preparar_base(df)["id_contribuinte"]) == ["b"]


# ---------------------------------------------------------------------------
# 4. Grupos formalizados (LC 285/2013, art. 20, II)
# ---------------------------------------------------------------------------
def test_grupos_formalizados():
    assert set(GRUPOS_PROTEGIDOS) == {"idoso", "aposentado", "pensionista", "pcd"}


@pytest.mark.parametrize("grupo", ["idoso", "aposentado", "pensionista", "pcd", " IDOSO ", "Pcd"])
def test_codigo_de_grupo_protege_mesmo_com_indicador_falso(grupo):
    """Cadastro inconsistente (grupo informado, flag 0): prevalece a proteção."""
    df = pd.DataFrame([_registro(is_iptu_social=0, grupo_iptu_social=grupo)])
    classificacao = classificar_protecao(df)
    assert classificacao["protegido"].iloc[0]
    assert classificacao["motivo"].iloc[0] == f"grupo:{grupo.strip().lower()}"


@pytest.mark.parametrize("grupo", [None, np.nan, "", "nenhum"])
def test_sem_grupo_e_indicador_falso_nao_e_protegido(grupo):
    df = pd.DataFrame([_registro(is_iptu_social=0, grupo_iptu_social=grupo)])
    assert not eh_grupo_protegido(df).iloc[0]


def test_codigo_de_grupo_desconhecido_e_tratado_como_indefinido():
    df = pd.DataFrame([_registro(is_iptu_social=0, grupo_iptu_social="estudante")])
    classificacao = classificar_protecao(df)
    assert classificacao["protegido"].iloc[0]
    assert classificacao["motivo"].iloc[0] == "indicador_indefinido"


def test_eh_grupo_protegido_aceita_registro_unico():
    assert eh_grupo_protegido(_registro(iptu_social=1)) is True
    assert eh_grupo_protegido(_registro(iptu_social=0)) is False
    assert eh_grupo_protegido(_registro(iptu_social=0, grupo_iptu_social="pensionista")) is True


def test_preparar_base_remove_grupo_e_dados_pessoais():
    df = pd.DataFrame([
        _registro(id_contribuinte="a", is_iptu_social=False, grupo_iptu_social="", cpf_cnpj="1", nome="X"),
        _registro(id_contribuinte="b", is_iptu_social=False, grupo_iptu_social="pcd", cpf_cnpj="2", nome="Y"),
    ])
    preparada = preparar_base(df)
    assert list(preparada["id_contribuinte"]) == ["a"]
    for coluna in ("is_iptu_social", COLUNA_GRUPO, "cpf_cnpj", "nome"):
        assert coluna not in preparada.columns


def test_relatorio_da_exclusao_na_carteira_sintetica(carteira_bruta):
    elegivel, relatorio = excluir_grupos_protegidos(carteira_bruta)
    assert relatorio.total_registros == TOTAL_CARTEIRA
    assert relatorio.protegidos == TOTAL_BENEFICIARIOS
    assert relatorio.indefinidos == 0
    assert relatorio.elegiveis == len(elegivel) == TOTAL_CARTEIRA - TOTAL_BENEFICIARIOS
    assert relatorio.por_motivo == {"indicador_iptu_social": TOTAL_BENEFICIARIOS}
