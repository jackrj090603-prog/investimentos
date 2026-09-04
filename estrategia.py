import pandas as pd
import numpy as np

def calcular_momentum_sinal(precos_diarios, data_rebal, ativos_elegiveis, L_meses=12, lag_meses=1):
    """
    Calcula o sinal de momentum para uma data de rebalanceamento específica.
    Usa o retorno acumulado dos ativos elegíveis na janela de [L_meses] terminando há [lag_meses] atrás.
    """
    # Converter para cotações mensais (fim de mês) para facilitar o lookback
    # Filtramos até a data do rebalanceamento
    precos_ate_rebal = precos_diarios.loc[:data_rebal]
    if len(precos_ate_rebal) < 20:
        return pd.Series(dtype=float)
        
    # Resample para mensal
    precos_mensais = precos_ate_rebal.resample("ME").last()
    
    if len(precos_mensais) < (L_meses + lag_meses + 1):
        # Histórico insuficiente
        return pd.Series(dtype=float)
        
    # Data de fim da janela de sinal: t - lag_meses
    data_fim_sinal = precos_mensais.index[-(lag_meses + 1)]
    # Data de início da janela de sinal: t - lag_meses - L_meses
    data_ini_sinal = precos_mensais.index[-(lag_meses + 1 + L_meses)]
    
    sinais = {}
    for ticker in ativos_elegiveis:
        col = f"{ticker}.SA"
        if col in precos_mensais.columns:
            p_fim = precos_mensais.loc[data_fim_sinal, col]
            p_ini = precos_mensais.loc[data_ini_sinal, col]
            
            # Garantir que o ativo tem preços válidos e não é nulo
            if pd.notna(p_fim) and pd.notna(p_ini) and p_ini > 0:
                retorno_janela = (p_fim / p_ini) - 1.0
                sinais[ticker] = retorno_janela
                
    return pd.Series(sinais)

def selecionar_portfolio(sinais, top_n=10):
    """
    Seleciona as pernas Long (Top N de melhor retorno) e Short (Bottom N de pior retorno).
    """
    if sinais.empty:
        return [], []
        
    # Ordenar do maior para o menor sinal
    sinais_ordenados = sinais.sort_values(ascending=False)
    
    # Selecionar Long e Short
    n_ativos = min(top_n, len(sinais_ordenados) // 2)
    if n_ativos < 1:
        # Se houver muito poucos ativos, pega pelo menos 1 ou metade dos ativos
        n_ativos = max(1, len(sinais_ordenados) // 2)
        
    longs = list(sinais_ordenados.head(n_ativos).index)
    shorts = list(sinais_ordenados.tail(n_ativos).index)
    
    return longs, shorts
