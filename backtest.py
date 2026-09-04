import os
import pandas as pd
import numpy as np
from datetime import datetime
import dados
import estrategia

def rodar_backtest(data_dict, L_meses=12, top_n=10, long_only=False, custo_bps=10.0, btc_ano=0.02):
    """
    Executa o backtest cronológico mensal de momentum.
    
    Parâmetros:
    - data_dict: Dicionário contendo precos (df), cdi (df), e composicao (df).
    - L_meses: Janela do sinal de momentum.
    - top_n: Número de ativos em cada perna.
    - long_only: Se True, opera apenas perna comprada.
    - custo_bps: Custo de transação em bps (1 bps = 0.01% = 0.0001).
    - btc_ano: Taxa anual de aluguel para a perna short (ex: 0.02 = 2% a.a.).
    """
    precos = data_dict["precos"]
    cdi_df = data_dict["cdi"]
    composicao = data_dict["composicao"]
    
    # Alinhar datas e indexar por data
    cdi_df["data"] = pd.to_datetime(cdi_df["data"])
    cdi_df = cdi_df.set_index("data")
    
    # Criar DataFrame diário para acompanhar os retornos do portfólio
    datas_diarias = precos.index
    df_portfolio = pd.DataFrame(index=datas_diarias)
    df_portfolio["ret_diario_estratega"] = 0.0
    df_portfolio["ret_diario_cdi"] = 0.0
    
    # Sincronizar retornos diários do CDI
    df_portfolio = df_portfolio.join(cdi_df["valor"], how="left").rename(columns={"valor": "ret_diario_cdi"})
    df_portfolio["ret_diario_cdi"] = df_portfolio["ret_diario_cdi"].fillna(0.0)
    
    # Gerar datas de rebalanceamento mensais (fim de mês)
    # Filtramos as datas da composição
    datas_rebal = sorted(composicao["data"])
    
    # Estruturas para guardar histórico de posições e turnover
    historico_posicoes = []
    
    # Posições anteriores para cálculo de turnover
    longs_anteriores = []
    shorts_anteriores = []
    
    custo_transacao_decimal = custo_bps / 10000.0
    btc_diario = (1.0 + btc_ano) ** (1.0 / 252.0) - 1.0
    
    print(f"[Backtest] Iniciando loop cronológico de rebalanceamento ({len(datas_rebal)} meses)...")
    
    # Loop mês a mês
    for idx, dt in enumerate(datas_rebal):
        # A data do rebalanceamento é dt
        dt = pd.to_datetime(dt)
        if dt not in datas_diarias:
            # Achar a data mais próxima no índice de preços
            dt_idx = datas_diarias.get_indexer([dt], method="nearest")[0]
            dt_real = datas_diarias[dt_idx]
        else:
            dt_real = dt
            
        # Determinar os ativos elegíveis para o mês a partir do Ibovespa
        linha_comp = composicao[composicao["data"] == dt.strftime("%Y-%m-%d")]
        if linha_comp.empty:
            continue
        ativos_elegiveis = linha_comp.iloc[0]["tickers"].split()
        
        # Calcular os sinais de momentum
        sinais = estrategia.calcular_momentum_sinal(precos, dt_real, ativos_elegiveis, L_meses=L_meses)
        if sinais.empty:
            continue
            
        # Selecionar carteiras
        longs, shorts = estrategia.selecionar_portfolio(sinais, top_n=top_n)
        if not longs:
            continue
            
        # Período de vigência do portfólio rebalanceado: desta data até a próxima data de rebalanceamento
        if idx < len(datas_rebal) - 1:
            proxima_dt = pd.to_datetime(datas_rebal[idx + 1])
            proxima_dt_idx = datas_diarias.get_indexer([proxima_dt], method="nearest")[0]
            data_fim_vigencia = datas_diarias[proxima_dt_idx]
        else:
            data_fim_vigencia = datas_diarias[-1]
            
        # Filtrar o intervalo de dias úteis desse mês
        intervalo_dias = datas_diarias[(datas_diarias >= dt_real) & (datas_diarias < data_fim_vigencia)]
        if len(intervalo_dias) == 0:
            continue
            
        # Calcular turnover e custo de transação
        # Longs adicionados/removidos
        longs_comprados = set(longs) - set(longs_anteriores)
        longs_vendidos = set(longs_anteriores) - set(longs)
        
        # Shorts adicionados/removidos
        shorts_vendidos = set(shorts) - set(shorts_anteriores)
        shorts_comprados = set(shorts_anteriores) - set(shorts)
        
        # Turnover simplificado = proporção de novos ativos comprados ou vendidos nas carteiras
        n_longs = len(longs)
        n_shorts = len(shorts)
        
        turnover_long = (len(longs_comprados) + len(longs_vendidos)) / (2.0 * n_longs) if n_longs > 0 else 0
        turnover_short = (len(shorts_vendidos) + len(shorts_comprados)) / (2.0 * n_shorts) if n_shorts > 0 and not long_only else 0
        
        # Custo de transação total do mês (aplicado no dia do rebalanceamento)
        total_turnover = turnover_long + turnover_short
        custo_rebal = total_turnover * custo_transacao_decimal
        
        # Guardar para o próximo mês
        longs_anteriores = list(longs)
        shorts_anteriores = list(shorts)
        
        # Salvar histórico para relatórios
        historico_posicoes.append({
            "data": dt_real,
            "longs": longs,
            "shorts": shorts,
            "sinais": sinais
        })
        
        # Calcular retornos diários no intervalo de vigência
        for d in intervalo_dias:
            # Retorno diário da perna Long
            ret_longs_d = []
            for t in longs:
                col = f"{t}.SA"
                if col in precos.columns:
                    val = precos[col].pct_change().loc[d]
                    if pd.notna(val) and not np.isinf(val):
                        ret_longs_d.append(val)
            ret_long = np.mean(ret_longs_d) if ret_longs_d else 0.0
            
            # Retorno diário da perna Short
            ret_short = 0.0
            if not long_only:
                ret_shorts_d = []
                for t in shorts:
                    col = f"{t}.SA"
                    if col in precos.columns:
                        val = precos[col].pct_change().loc[d]
                        if pd.notna(val) and not np.isinf(val):
                            ret_shorts_d.append(val)
                ret_short = np.mean(ret_shorts_d) if ret_shorts_d else 0.0
                
            # Retorno do portfólio
            if long_only:
                ret_d = ret_long
            else:
                # LS: CDI (caixa colateral) + Long - Short - Aluguel BTC
                ret_d = df_portfolio.loc[d, "ret_diario_cdi"] + (ret_long - ret_short) - btc_diario
                
            # Se for o dia do rebalanceamento, desconta o custo de transação
            if d == dt_real:
                ret_d -= custo_rebal
                
            df_portfolio.loc[d, "ret_diario_estratega"] = ret_d
            
    # Eliminar datas sem trade (antes do primeiro rebalanceamento)
    primeiro_rebal = pd.to_datetime(datas_rebal[0])
    df_result = df_portfolio.loc[primeiro_rebal:].copy()
    
    # Calcular retornos acumulados (curvas de capital)
    df_result["capital_estrategia"] = (1.0 + df_result["ret_diario_estratega"]).cumprod()
    df_result["capital_cdi"] = (1.0 + df_result["ret_diario_cdi"]).cumprod()
    
    # Métricas consolidadas
    n_dias = len(df_result)
    anos = n_dias / 252.0
    
    ret_acum_est = df_result["capital_estrategia"].iloc[-1] - 1.0
    ret_acum_cdi = df_result["capital_cdi"].iloc[-1] - 1.0
    
    ret_anual_est = (ret_acum_est + 1.0) ** (1.0 / anos) - 1.0
    ret_anual_cdi = (ret_acum_cdi + 1.0) ** (1.0 / anos) - 1.0
    
    # Volatilidade anualizada
    vol_anual_est = df_result["ret_diario_estratega"].std() * np.sqrt(252.0)
    
    # Sharpe Ratio (taxa livre de risco = CDI)
    excesso_ret_diario = df_result["ret_diario_estratega"] - df_result["ret_diario_cdi"]
    sharpe = (excesso_ret_diario.mean() / excesso_ret_diario.std() * np.sqrt(252.0)) if excesso_ret_diario.std() > 0 else 0.0
    
    # Drawdown Máximo
    capital = df_result["capital_estrategia"]
    max_peak = capital.cummax()
    drawdowns = (capital - max_peak) / max_peak
    max_dd = drawdowns.min()
    
    # % de Meses Positivos
    ret_mensal = df_result["ret_diario_estratega"].resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0)
    pct_meses_pos = (ret_mensal > 0).mean() * 100.0
    
    # Rigor estatístico: Teste-t do Alpha vs CDI (mensal)
    ret_mensal_cdi = df_result["ret_diario_cdi"].resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0)
    excesso_mensal = ret_mensal - ret_mensal_cdi
    
    t_stat = 0.0
    p_value = 1.0
    try:
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(excesso_mensal, 0.0)
    except ImportError:
        # Cálculo manual do teste-t caso o scipy não esteja disponível
        n_meses = len(excesso_mensal)
        if n_meses > 1:
            mean_exc = excesso_mensal.mean()
            std_exc = excesso_mensal.std(ddof=1)
            t_stat = mean_exc / (std_exc / np.sqrt(n_meses)) if std_exc > 0 else 0.0
            # P-value aproximado usando aproximação normal bicaudal
            from scipy.stats import norm
            p_value = 2.0 * (1.0 - norm.cdf(abs(t_stat)))
            
    alpha_mensal_medio = excesso_mensal.mean()
    alpha_anualizado = (1.0 + alpha_mensal_medio) ** 12 - 1.0
    
    metrics = {
        "ret_acum_estrategia": ret_acum_est * 100.0,
        "ret_acum_cdi": ret_acum_cdi * 100.0,
        "ret_anual_estrategia": ret_anual_est * 100.0,
        "ret_anual_cdi": ret_anual_cdi * 100.0,
        "vol_anualizada": vol_anual_est * 100.0,
        "sharpe": sharpe,
        "max_drawdown": max_dd * 100.0,
        "pct_meses_positivos": pct_meses_pos,
        "t_stat": t_stat,
        "p_value": p_value,
        "alpha_anualizado": alpha_anualizado * 100.0,
        "excesso_mensal_serie": excesso_mensal
    }
    
    return df_result, metrics, historico_posicoes

if __name__ == "__main__":
    # Teste rápido
    d_dict = dados.carregar_dados_completos("2020-01-01", "2021-12-31")
    df_r, met, pos = rodar_backtest(d_dict, L_meses=12, top_n=5, long_only=False)
    print("Métricas do Backtest:")
    for k, v in met.items():
        if k != "excesso_mensal_serie":
            print(f"  {k}: {v:.4f}")
