import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Estilo global dos gráficos
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["figure.figsize"] = (10, 6)

def salvar_graficos(df_result, metrics, historico_posicoes, folder="plots"):
    """
    Gera e salva os 5 gráficos da rodada padrão de volta ao tempo.
    """
    os.makedirs(folder, exist_ok=True)
    
    # 1. CURVA DE CAPITAL
    plt.figure()
    plt.plot(df_result.index, df_result["capital_estrategia"], label="Estratégia Momentum", color="#1a1a1a", linewidth=2.0)
    plt.plot(df_result.index, df_result["capital_cdi"], label="CDI (Benchmark)", color="#7a7a7a", linestyle="--", linewidth=1.5)
    plt.title("Evolução da Curva de Capital (Retorno Acumulado)", fontsize=14, fontweight="bold")
    plt.xlabel("Data")
    plt.ylabel("Multiplicador de Capital")
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "curva_capital.png"), dpi=150)
    plt.close()
    
    # 2. ALPHA ACUMULADO
    plt.figure()
    alpha_acum = df_result["capital_estrategia"] - df_result["capital_cdi"]
    plt.fill_between(df_result.index, alpha_acum, 0, where=(alpha_acum >= 0), color="rgba(70, 224, 160, 0.2)", interpolate=True)
    plt.fill_between(df_result.index, alpha_acum, 0, where=(alpha_acum < 0), color="rgba(255, 107, 107, 0.2)", interpolate=True)
    plt.plot(df_result.index, alpha_acum, color="#2b2b2b", linewidth=1.8, label="Alpha Acumulado (Estratégia - CDI)")
    plt.title("Evolução do Alpha Acumulado vs CDI", fontsize=14, fontweight="bold")
    plt.xlabel("Data")
    plt.ylabel("Retorno Excedente (Decimal)")
    plt.axhline(0, color="black", linestyle=":", linewidth=1)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "alpha_acumulado.png"), dpi=150)
    plt.close()
    
    # 3. DRAWDOWN
    plt.figure()
    capital = df_result["capital_estrategia"]
    max_peak = capital.cummax()
    drawdowns = (capital - max_peak) / max_peak * 100.0
    plt.fill_between(df_result.index, drawdowns, 0, color="#ff6b6b", alpha=0.3)
    plt.plot(df_result.index, drawdowns, color="#c62828", linewidth=1.2)
    plt.title("Evolução do Drawdown Pico a Vale (%)", fontsize=14, fontweight="bold")
    plt.xlabel("Data")
    plt.ylabel("Drawdown (%)")
    plt.ylim(top=0)
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "drawdown.png"), dpi=150)
    plt.close()
    
    # 4. MAPA DE CALOR MENSAL
    plt.figure(figsize=(11, 7))
    # Calcular retornos mensais da estratégia
    ret_mensal = df_result["ret_diario_estratega"].resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0) * 100.0
    
    # Transformar em DataFrame pivotado (Ano x Mês)
    df_pivot = pd.DataFrame({
        "Ano": ret_mensal.index.year,
        "Mês": ret_mensal.index.month,
        "Retorno": ret_mensal.values
    })
    
    # Mapear números dos meses para nomes abreviados em português
    meses_nomes = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                   7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    df_pivot["Mês"] = df_pivot["Mês"].map(meses_nomes)
    
    # Pivotar
    try:
        pivot_table = df_pivot.pivot(index="Ano", columns="Mês", values="Retorno")
        # Reordenar colunas
        ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        ordem_existente = [m for m in ordem_meses if m in pivot_table.columns]
        pivot_table = pivot_table[ordem_existente]
        
        sns.heatmap(pivot_table, annot=True, fmt=".1f", cmap="RdYlGn", center=0, cbar=True,
                    linewidths=0.5, annot_kws={"size": 10})
        plt.title("Mapa de Calor dos Retornos Mensais (%)", fontsize=14, fontweight="bold")
        plt.xlabel("Mês")
        plt.ylabel("Ano")
    except Exception as e:
        plt.text(0.5, 0.5, f"Erro ao gerar Heatmap:\n{e}", ha="center", va="center")
        
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "mapa_calor_mensal.png"), dpi=150)
    plt.close()
    
    # 5. CARTEIRA ATUAL
    plt.figure()
    if historico_posicoes:
        ultima_carteira = historico_posicoes[-1]
        longs = ultima_carteira["longs"]
        shorts = ultima_carteira["shorts"]
        sinais = ultima_carteira["sinais"]
        
        # Filtrar os sinais dos ativos selecionados
        ativos = longs + shorts
        valores_sinais = sinais.loc[ativos].sort_values(ascending=False) * 100.0
        
        # Colorir comprado de verde e vendido de vermelho/laranja
        cores = ["#2e7d32" if t in longs else "#c62828" for t in valores_sinais.index]
        
        valores_sinais.plot(kind="bar", color=cores, edgecolor="black")
        plt.axhline(0, color="black", linewidth=1)
        plt.title(f"Sinal de Momentum (%) - Rebalanceamento {ultima_carteira['data'].strftime('%m/%Y')}", fontsize=13, fontweight="bold")
        plt.ylabel("Sinal de Retorno Janela (%)")
        plt.xlabel("Ativos (Verde = Long, Vermelho = Short)")
        plt.xticks(rotation=45, ha="right")
    else:
        plt.text(0.5, 0.5, "Nenhum histórico de posições disponível", ha="center", va="center")
        
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "carteira_atual.png"), dpi=150)
    plt.close()
    
    print(f"[Gráficos] 5 Gráficos padrão salvos com sucesso na pasta: '{folder}/'")

if __name__ == "__main__":
    # Teste rápido
    import dados
    import backtest
    d_dict = dados.carregar_dados_completos("2020-01-01", "2021-12-31")
    df_r, met, pos = backtest.rodar_backtest(d_dict, L_meses=12, top_n=5)
    salvar_graficos(df_r, met, pos)
