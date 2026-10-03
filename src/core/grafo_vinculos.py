class GrafoSefin:
    def __init__(self):
        # O grafo será um dicionário de dicionários para guardar a Lista de Adjacência.
        # Ex: { 'CPF_123': ['Imovel_A', 'Imovel_B'] }
        self.grafo = {}
        # Dicionário auxiliar para guardar o TIPO de cada nó (Contribuinte, Imovel, Processo)
        self.tipos_nos = {}

    def adicionar_no(self, id_no, tipo):
        """Adiciona um nó ao grafo, se não existir."""
        if id_no not in self.grafo:
            self.grafo[id_no] = []
            self.tipos_nos[id_no] = tipo

    def adicionar_vinculo(self, id_origem, id_destino):
        """Cria uma aresta não-direcionada entre dois nós."""
        # Garante que os nós existam no grafo antes de vincular
        if id_origem in self.grafo and id_destino in self.grafo:
            # Como a relação vai e volta (CPF dono do Imovel, Imovel pertence ao CPF)
            self.grafo[id_origem].append(id_destino)
            self.grafo[id_destino].append(id_origem)

    def buscar_rede_contribuinte(self, id_contribuinte):
        """
        Usa Busca em Largura (BFS) para encontrar TODOS os imóveis e processos
        ligados direta ou indiretamente a um CPF/CNPJ.
        """
        if id_contribuinte not in self.grafo:
            return "Contribuinte não encontrado."

        visitados = set()
        fila = [id_contribuinte]
        rede = {'Imovel': [], 'Processo': []}

        while fila:
            no_atual = fila.pop(0)
            if no_atual not in visitados:
                visitados.add(no_atual)
                
                # Classifica o nó encontrado para o relatório
                tipo = self.tipos_nos[no_atual]
                if tipo in rede:
                    rede[tipo].append(no_atual)
                
                # Adiciona os vizinhos na fila para explorar
                for vizinho in self.grafo[no_atual]:
                    if vizinho not in visitados:
                        fila.append(vizinho)
                        
        return rede


if __name__ == "__main__":
    # ==========================================
    # CASOS DE TESTE UTILITÁRIOS (Amostra Simulada)
    # ==========================================
    print("Iniciando testes da estrutura de Grafos...\n")
    
    sefin = GrafoSefin()

    # 1. Inserindo a amostra simulada
    sefin.adicionar_no("CPF_111222333", "Contribuinte")
    sefin.adicionar_no("Inscricao_001", "Imovel")
    sefin.adicionar_no("Inscricao_002", "Imovel")
    sefin.adicionar_no("Proc_999/2025", "Processo")
    sefin.adicionar_no("Proc_888/2026", "Processo")

    # 2. Criando os vínculos (Arestas)
    sefin.adicionar_vinculo("CPF_111222333", "Inscricao_001") # CPF é dono do Imovel 1
    sefin.adicionar_vinculo("CPF_111222333", "Inscricao_002") # CPF também é dono do Imovel 2
    sefin.adicionar_vinculo("Inscricao_001", "Proc_999/2025") # Imovel 1 tem o processo 999
    sefin.adicionar_vinculo("Inscricao_002", "Proc_888/2026") # Imovel 2 tem o processo 888

    # 3. Testando a busca da "teia" do devedor
    print("Buscando rede do Contribuinte CPF_111222333:")
    resultado = sefin.buscar_rede_contribuinte("CPF_111222333")
    print(resultado)
    
    # Validação visual do teste
    esperado = {'Imovel': ['Inscricao_001', 'Inscricao_002'], 'Processo': ['Proc_999/2025', 'Proc_888/2026']}
    if resultado == esperado:
        print("\n✅ Teste passou com sucesso! A estrutura mapeou as múltiplas inscrições.")
    else:
        print("\n❌ Falha no teste.")