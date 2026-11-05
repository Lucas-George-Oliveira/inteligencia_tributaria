from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.core.engenharia_atributos import engenharia_atributos
from src.core.grafo_vinculos import construir_grafo_vinculos, identificar_grupos_risco
from src.api.coleta_ibge import obter_indicadores_ibge, estruturar_dados_socioeconomicos
from src.database.database import get_db, init_db, DebitoModel, GrupoRiscoModel

# Inicializa as tabelas no banco de dados ao subir a API
init_db()

app = FastAPI(
    title="API de Inteligência Tributária - Palmas/TO",
    version="1.0.0",
    description="Interface REST para análise de risco tributário, dados do IBGE, grafos e persistência em banco."
)

class DebitoItem(BaseModel):
    cpf_cnpj: Optional[str] = None
    cpf_cnpj_hash: Optional[str] = None
    valor_debito: float
    data_vencimento: str
    tipo_tributo: str
    bairro: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "online", "sistema": "Inteligência Tributária - Prefeitura de Palmas"}

@app.post("/api/v1/analise-risco")
def analisar_risco(debitos: List[DebitoItem], db: Session = Depends(get_db)):
    """Aplica engenharia de atributos e persiste os débitos analisados no banco de dados."""
    if not debitos:
        raise HTTPException(status_code=400, detail="A lista de débitos não pode estar vazia.")
    
    itens = [d.model_dump() if hasattr(d, "model_dump") else d.dict() for d in debitos]
    df_input = pd.DataFrame(itens)
    
    df_processado = engenharia_atributos(df_input)
    
    for col in df_processado.columns:
        if str(df_processado[col].dtype) == "category":
            df_processado[col] = df_processado[col].astype(str)
            
    registros = df_processado.to_dict(orient="records")
    
    # Persistência dos registros no banco de dados
    for reg in registros:
        debito_db = DebitoModel(
            cpf_cnpj_hash=reg.get("cpf_cnpj_hash") or reg.get("cpf_cnpj", "ANONIMO"),
            valor_debito=float(reg.get("valor_debito", 0.0)),
            data_vencimento=str(reg.get("data_vencimento")),
            tipo_tributo=str(reg.get("tipo_tributo")),
            bairro=reg.get("bairro"),
            faixa_valor_debito=reg.get("faixa_valor_debito"),
            dias_atraso=reg.get("dias_atraso")
        )
        db.add(debito_db)
    db.commit()

    return registros

@app.post("/api/v1/grafos/grupos-risco")
def analisar_grupos_risco(debitos: List[DebitoItem], db: Session = Depends(get_db)):
    """Mapeia vínculos e persiste os grupos de risco identificados no banco de dados."""
    if not debitos:
        raise HTTPException(status_code=400, detail="A lista de débitos não pode estar vazia.")
    
    itens = [d.model_dump() if hasattr(d, "model_dump") else d.dict() for d in debitos]
    df_input = pd.DataFrame(itens)
    G = construir_grafo_vinculos(df_input)
    grupos = identificar_grupos_risco(G)
    
    # Persistência dos grupos no banco de dados
    for g in grupos:
        grupo_db = GrupoRiscoModel(
            grupo_id_origem=g["grupo_id"],
            tamanho_grupo=g["tamanho_grupo"],
            total_debito=g["total_debito"],
            membros_json=json.dumps(g["membros"])
        )
        db.add(grupo_db)
    db.commit()

    return {"total_grupos": len(grupos), "grupos": grupos}

@app.get("/api/v1/ibge/palmas")
def consultar_ibge_palmas():
    dados_brutos = obter_indicadores_ibge()
    df_ibge = estruturar_dados_socioeconomicos(dados_brutos)
    return df_ibge.to_dict(orient="records")