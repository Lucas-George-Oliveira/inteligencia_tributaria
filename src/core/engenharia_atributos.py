import pandas as pd
import numpy as np

def engenharia_atributos(df: pd.DataFrame, data_referencia: str = None) -> pd.DataFrame:
    """
    Transforma a base de débitos tributários criando atributos 
    para análise de risco e modelos preditivos.
    """
    # 1. Cria cópia para não alterar o DataFrame original
    df_result = df.copy()

    # 2. Validação de colunas obrigatórias
    colunas_obrigatorias = ["valor_debito", "data_vencimento", "tipo_tributo"]
    for coluna in colunas_obrigatorias:
        if coluna not in df_result.columns:
            raise ValueError(f"A coluna obrigatória '{coluna}' está ausente no DataFrame.")

    # 3. Conversão de datas
    df_result["data_vencimento"] = pd.to_datetime(df_result["data_vencimento"])
    
    if data_referencia:
        ref_date = pd.to_datetime(data_referencia)
    else:
        ref_date = pd.Timestamp.now()

    # 4. Cálculo de dias, meses de atraso e indicador booleano de atraso
    dias = (ref_date - df_result["data_vencimento"]).dt.days
    df_result["dias_atraso"] = dias.apply(lambda x: max(x, 0))
    df_result["meses_atraso"] = (df_result["dias_atraso"] / 30).astype(int)
    df_result["indicador_atraso"] = (df_result["dias_atraso"] > 0).astype(int)

    # 5. Categorização da faixa de dívida
    def categorizar_faixa(valor):
        if valor <= 1000:
            return "BAIXA"
        elif valor <= 5000:
            return "MEDIA"
        elif valor <= 10000:
            return "ALTA"
        else:
            return "MUITO_ALTA"

    df_result["faixa_divida"] = df_result["valor_debito"].apply(categorizar_faixa)

    # Faixas de valor da dívida
    limites = [-np.inf, 1000, 5000, 20000, np.inf]
    rotulos = ["Baixo", "Médio", "Alto", "Grande Devedor"]
    df_result["faixa_valor_debito"] = pd.cut(df_result["valor_debito"], bins=limites, labels=rotulos)

    # 6. Indicadores de Sazonalidade (mês, trimestre e fim de ano)
    df_result["mes_vencimento"] = df_result["data_vencimento"].dt.month
    df_result["trimestre_vencimento"] = df_result["data_vencimento"].dt.quarter
    df_result["vencimento_fim_ano"] = df_result["mes_vencimento"].isin([11, 12]).astype(int)

    # 7. Transformação cíclica da sazonalidade mensal (seno e cosseno)
    df_result["mes_seno"] = np.sin(2 * np.pi * df_result["mes_vencimento"] / 12)
    df_result["mes_cosseno"] = np.cos(2 * np.pi * df_result["mes_vencimento"] / 12)

    # 8. Escala Logarítmica
    df_result["log_valor_debito"] = np.log1p(df_result["valor_debito"])

    return df_result