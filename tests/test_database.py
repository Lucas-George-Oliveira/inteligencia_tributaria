import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.database import Base, DebitoModel, GrupoRiscoModel

# Banco de dados SQLite em memória para testes isolados
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_inserir_debito(db_session):
    debito = DebitoModel(
        cpf_cnpj_hash="hash_teste_123",
        valor_debito=12000.50,
        data_vencimento="2023-05-10",
        tipo_tributo="IPTU",
        bairro="Centro",
        faixa_valor_debito="Alto",
        dias_atraso=180
    )
    db_session.add(debito)
    db_session.commit()

    resultado = db_session.query(DebitoModel).filter_by(cpf_cnpj_hash="hash_teste_123").first()
    assert resultado is not None
    assert resultado.valor_debito == 12000.50
    assert resultado.faixa_valor_debito == "Alto"

def test_inserir_grupo_risco(db_session):
    grupo = GrupoRiscoModel(
        grupo_id_origem=1,
        tamanho_grupo=2,
        total_debito=25000.0,
        membros_json='["hash_1", "hash_2"]'
    )
    db_session.add(grupo)
    db_session.commit()

    resultado = db_session.query(GrupoRiscoModel).filter_by(grupo_id_origem=1).first()
    assert resultado is not None
    assert resultado.tamanho_grupo == 2