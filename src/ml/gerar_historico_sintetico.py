
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml.preparar_base import preparar_base


# Carrega e prepara a carteira original
bruto = pd.read_csv(
    "data/bruto/carteira_contribuintes_sintetica.csv",
    sep=";"
)

estado = preparar_base(bruto)

# Remove resultados futuros da carteira original.
# Vamos simular novos resultados periodo a periodo.
estado = estado.drop(
    columns=[
        "inadimplente_proximo_exercicio",
        "divida_recuperada_12m"
    ],
    errors="ignore"
).reset_index(drop=True)

rng = np.random.default_rng(42)

# Doze periodos mensais simulados
periodos = pd.date_range(
    "2024-01-01",
    periods=12,
    freq="MS"
)

historico = []

for numero, data in enumerate(periodos):

    # Fotografia dos dados conhecidos neste periodo
    observacao = estado.copy()

    # Probabilidade simulada de inadimplencia
    logit = (
        -1.7
        + 0.25 * estado["exercicios_inadimplentes_5a"]
        + 0.40 * estado["parcelamento_rompido"]
        + 0.14 * np.log1p(
            estado["valor_divida_consolidada"] / 1000
        )
        + 0.20 * (estado["tipo_imovel"] == "terreno")
        + 0.12 * np.sin(2 * np.pi * numero / 12)
    )

    probabilidade = 1 / (1 + np.exp(-logit))

    resultado = rng.binomial(
        1, probabilidade.to_numpy()
    )

    observacao["data_referencia_simulada"] = data

    # O resultado so fica disponivel no mes seguinte
    observacao["data_disponibilidade_alvo"] = (
        data + pd.offsets.MonthBegin(1)
    )

    observacao["inadimplente_proximo_periodo"] = resultado

    historico.append(observacao)

    # Atualiza o estado APOS simular o resultado.
    # Assim, o futuro nao altera os atributos do passado.
    estado["tempo_inadimplencia_dias"] = np.where(
        resultado == 1,
        estado["tempo_inadimplencia_dias"] + 30,
        np.maximum(
            estado["tempo_inadimplencia_dias"] - 30, 0
        )
    )

    saldo = estado["valor_divida_consolidada"].to_numpy()
    iptu = estado["valor_iptu_anual"].to_numpy()

    estado["valor_divida_consolidada"] = np.maximum(
        0,
        saldo + resultado * iptu / 12
        - (1 - resultado) * iptu / 24
    ).round(2)

    novas_notificacoes = (
        (resultado == 1)
        & (rng.random(len(estado)) < 0.20)
    ).astype(int)

    estado["qtd_notificacoes"] += novas_notificacoes


# Reune os periodos em uma base longitudinal
base_temporal = pd.concat(
    historico, ignore_index=True
)

saida = Path(
    "data/tratado/historico_temporal_sintetico.csv"
)

saida.parent.mkdir(parents=True, exist_ok=True)

base_temporal.to_csv(saida, index=False)

print("Historico sintetico gerado com sucesso!")
print("Registros:", len(base_temporal))
print(
    "Periodos:",
    base_temporal["data_referencia_simulada"].nunique()
)
print("Arquivo:", saida)
