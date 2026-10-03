
import heapq


class GestorDividas:
    def __init__(self):
        # Fila de prioridade: score maior sai primeiro
        self.fila_cobranca = []

        # Tabela hash: inscrição -> dados da dívida
        self.dividas = {}

    def adicionar_contribuinte(self, nome, inscricao, score):
        contribuinte = {
            "nome": nome,
            "inscricao": inscricao,
            "score": score
        }

        # O heapq é uma min-heap.
        # Usamos -score para priorizar o maior score.
        heapq.heappush(
            self.fila_cobranca,
            (-score, inscricao, contribuinte)
        )

        # Armazena a dívida usando a inscrição como chave
        self.dividas[inscricao] = contribuinte

    def proximo_da_fila(self):
        if not self.fila_cobranca:
            return None

        _, inscricao, contribuinte = heapq.heappop(
            self.fila_cobranca
        )

        return contribuinte

    def buscar_por_inscricao(self, inscricao):
        return self.dividas.get(inscricao)


if __name__ == "__main__":
    sistema = GestorDividas()

    # Cadastro de cinco contribuintes fictícios
    sistema.adicionar_contribuinte("Ana Silva", "INS001", 45)
    sistema.adicionar_contribuinte("Bruno Costa", "INS002", 99)
    sistema.adicionar_contribuinte("Carla Souza", "INS003", 20)
    sistema.adicionar_contribuinte("Diego Lima", "INS004", 80)
    sistema.adicionar_contribuinte("Eva Santos", "INS005", 60)

    print("=== FILA DE COBRANÇA ===")

    proximo = sistema.proximo_da_fila()
    print("Primeiro da fila:", proximo)

    print("\n=== BUSCA POR INSCRIÇÃO ===")

    resultado = sistema.buscar_por_inscricao("INS003")

    if resultado:
        print("Dívida encontrada:", resultado)
    else:
        print("Inscrição não encontrada.")