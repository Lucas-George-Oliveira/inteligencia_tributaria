import networkx as nx
import pandas as pd
from typing import List, Dict, Any

def construir_grafo_vinculos(df_debitores: pd.DataFrame) -> nx.Graph:
    """
    Constrói um grafo não-direcionado conectando contribuintes (CPFs/CNPJs) 
    por meio de conexões comuns (endereços, sócios ou ligações diretas).
    """
    G = nx.Graph()

    for _, row in df_debitores.iterrows():
        devedor = row.get("cpf_cnpj_hash") or row.get("contribuinte_id")
        tipo_tributo = row.get("tipo_tributo", "Desconhecido")
        valor = row.get("valor_debito", 0.0)

        if not devedor:
            continue

        # Adiciona o nó do devedor com os seus atributos
        if not G.has_node(devedor):
            G.add_node(devedor, tipo="devedor", total_debito=0.0, num_debitos=0)

        G.nodes[devedor]["total_debito"] += valor
        G.nodes[devedor]["num_debitos"] += 1

        # Vínculo por endereço/bairro (se disponível)
        if "bairro" in row and pd.notna(row["bairro"]):
            bairro_node = f"BAIRRO_{row['bairro']}"
            G.add_node(bairro_node, tipo="bairro")
            G.add_edge(devedor, bairro_node, relacao="localizacao")

    return G

def identificar_grupos_risco(G: nx.Graph) -> List[Dict[str, Any]]:
    """
    Identifica componentes ligados (comunidades) no grafo para encontrar
    grupos de devedores interconectados.
    """
    comunidades = []
    for idx, componente in enumerate(nx.connected_components(G)):
        subgrafo = G.subgraph(componente)
        devedores = [n for n, attr in subgrafo.nodes(data=True) if attr.get("tipo") == "devedor"]
        total_debito_grupo = sum(G.nodes[n].get("total_debito", 0.0) for n in devedores)

        if len(devedores) > 1:  # Foca em grupos com conexões compartilhadas
            comunidades.append({
                "grupo_id": idx + 1,
                "tamanho_grupo": len(devedores),
                "total_debito": total_debito_grupo,
                "membros": devedores
            })

    return comunidades