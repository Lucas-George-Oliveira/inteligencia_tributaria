import requests
import pandas as pd
from typing import Dict, Any

CODIGO_IBGE_PALMAS = "1721000"

def obter_indicadores_ibge(codigo_municipio: str = CODIGO_IBGE_PALMAS) -> Dict[str, Any]:
    """
    Obtém indicadores socioeconômicos do município (Palmas-TO) via API de Serviços do IBGE.
    """
    url = f"https://servicodados.ibge.gov.br/api/v1/pesquisas/indicadores/30255/resultados/{codigo_municipio}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        dados = response.json()
        
        # Estrutura inicial de retorno resumida
        resultado = {
            "codigo_ibge": codigo_municipio,
            "municipio": "Palmas",
            "uf": "TO",
            "status": "sucesso",
            "dados_brutos": dados
        }
        return resultado
    except requests.RequestException as e:
        print(f"[ERRO IBGE] Falha ao consultar API do IBGE: {e}")
        return {"status": "erro", "mensagem": str(e)}

def estruturar_dados_socioeconomicos(dados_ibge: Dict[str, Any]) -> pd.DataFrame:
    """
    Converte a resposta da API do IBGE em um DataFrame estruturado
    para ser cruzado com os dados tributários da Prefeitura de Palmas.
    """
    if dados_ibge.get("status") != "sucesso" or not dados_ibge.get("dados_brutos"):
        # Retorna DataFrame com estrutura padrão em caso de fallback
        return pd.DataFrame([{
            "codigo_ibge": CODIGO_IBGE_PALMAS,
            "municipio": "Palmas",
            "pib_per_capita": None,
            "indice_desenvolvimento": None
        }])

    # Parsing simples da resposta do IBGE
    registros = []
    for item in dados_ibge["dados_brutos"]:
        indicador_id = item.get("id")
        respostas = item.get("resumida", [])
        registros.append({
            "codigo_ibge": CODIGO_IBGE_PALMAS,
            "indicador_id": indicador_id,
            "valor": respostas[0].get("valor") if respostas else None
        })

    return pd.DataFrame(registros)

if __name__ == "__main__":
    print("Testando extração do IBGE para Palmas-TO...")
    dados = obter_indicadores_ibge()
    df_ibge = estruturar_dados_socioeconomicos(dados)
    print(df_ibge.head())