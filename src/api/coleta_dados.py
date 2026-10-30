import os
import json
import time
from datetime import datetime
import requests

BASE_URL = "https://acessoainformacao.palmas.to.gov.br"

NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Respeito às regras de conduta do manual
DELAY_ENTRE_REQUISICOES = 1.5
MAX_RETRIES_429 = 3

def buscar_dados_paginados(limite_paginas=3):
    todos_os_dados = []
    quantidade_por_pagina = 1000  # A API permite puxar lotes de 1000
    
    sessao = requests.Session()
    
    # 1. Visita prévia obrigatória para recolher cookies de sessão (Armadilha do manual)
    print("Obtendo cookies de sessão...")
    try:
        sessao.get(
            f"{BASE_URL}/cidadao/transparencia/sgreceitas",
            headers={"User-Agent": NAVEGADOR},
            timeout=60
        )
    except Exception as e:
        print(f"❌ Falha ao obter cookies iniciais: {e}")
        return todos_os_dados
    
    # 2. Cabeçalhos obrigatórios para simular o frontend no POST
    headers_api = {
        "User-Agent": NAVEGADOR,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE_URL}/cidadao/transparencia/sgreceitas",
        "Origin": BASE_URL,
    }

    for pagina_atual in range(1, limite_paginas + 1):
        # A paginação desta API não é por página, mas por Offset (deslocamento)
        offset = (pagina_atual - 1) * quantidade_por_pagina
        
        # Payload no formato exato exigido pelo sistema NUCLEOGOV
        consulta = {
            "k1": {
                "order": {},
                "limit": f"{offset}, {quantidade_por_pagina}",
                "acao": "sgreceitas/listar"
            }
        }
        
        payload = {
            "multi_request": "true",
            "params": json.dumps(consulta)
        }
        
        sucesso = False
        tentativa_429 = 0

        while not sucesso and tentativa_429 < MAX_RETRIES_429:
            try:
                time.sleep(DELAY_ENTRE_REQUISICOES)
                
                resposta = sessao.post(
                    f"{BASE_URL}/api",
                    data=payload,
                    headers=headers_api,
                    timeout=60
                )
                
                if resposta.status_code == 429:
                    tentativa_429 += 1
                    tempo = 5 * tentativa_429
                    print(f"⚠️ Rate Limit excedido. Aguardando {tempo}s...")
                    time.sleep(tempo)
                    continue

                if resposta.status_code == 200:
                    try:
                        json_resp = resposta.json()
                        # Extração da estrutura {"k1": {"total": N, "dados": [...]}}
                        pacote = json_resp.get("k1", {})
                        registros = pacote.get("dados", [])
                        total_esperado = pacote.get("total", 0)
                    except requests.exceptions.JSONDecodeError:
                        print(f"❌ Erro de JSON. Conteúdo retornado:\n{resposta.text[:200]}")
                        return todos_os_dados
                        
                    if not registros:
                        print("Nenhum dado retornado na resposta. Encerrando paginação.")
                        return todos_os_dados
                        
                    todos_os_dados.extend(registros)
                    print(f"✅ Página {pagina_atual} processada. (+{len(registros)} registros de um total de {total_esperado} disponíveis no servidor)")
                    sucesso = True
                else:
                    print(f"❌ Falha na requisição. Status Code: {resposta.status_code}")
                    return todos_os_dados
                    
            except Exception as e:
                print(f"❌ Erro inesperado na página {pagina_atual}: {e}")
                return todos_os_dados

    return todos_os_dados

def salvar_dados_brutos(dados):
    """Garante a pasta data/bruto e salva o JSON com data e hora."""
    if not dados:
        print("Nenhum dado para salvar.")
        return

    pasta_destino = os.path.join("data", "bruto")
    os.makedirs(pasta_destino, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"coleta_api_{timestamp}.json"
    caminho_completo = os.path.join(pasta_destino, nome_arquivo)

    with open(caminho_completo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    print(f"\n📁 Arquivo salvo em: {caminho_completo}")
    print(f"📊 Total de registros consolidados nesta execução: {len(dados)}")

if __name__ == "__main__":
    print("🚀 Iniciando coleta automatizada NUCLEOGOV...")
    dados_coletados = buscar_dados_paginados(limite_paginas=3)
    salvar_dados_brutos(dados_coletados)