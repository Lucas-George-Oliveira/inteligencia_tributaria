import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Configuração da URL da base de dados (SQLite para ambiente local/testes, configurável para PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inteligencia_tributaria.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DebitoModel(Base):
    """Tabela de registro dos débitos tributários processados."""
    __tablename__ = "debitos_tributarios"

    id = Column(Integer, primary_key=True, index=True)
    cpf_cnpj_hash = Column(String(64), index=True, nullable=False)
    valor_debito = Column(Float, nullable=False)
    data_vencimento = Column(String(10), nullable=False)
    tipo_tributo = Column(String(50), nullable=False)
    bairro = Column(String(100), nullable=True)
    faixa_valor_debito = Column(String(30), nullable=True)
    dias_atraso = Column(Integer, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

class GrupoRiscoModel(Base):
    """Tabela de registro dos grupos econômicos de risco identificados via Grafos."""
    __tablename__ = "grupos_risco"

    id = Column(Integer, primary_key=True, index=True)
    grupo_id_origem = Column(Integer, nullable=False)
    tamanho_grupo = Column(Integer, nullable=False)
    total_debito = Column(Float, nullable=False)
    membros_json = Column(Text, nullable=False)  # Lista de hashes dos membros em formato JSON
    criado_em = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Inicializa e cria as tabelas no banco de dados."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Injetor de sessão do banco de dados para a API."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()