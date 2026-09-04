import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import dados
import backtest
import graficos

def exportar_figuras_publicacao(df_result, metrics, historico_posicoes, folder="figuras"):
    """
    Gera e salva os 5 gráficos em qualidade de publicação (300 DPI, mesmo padrão de cores e eixos em português).
    Inclui a figura contendo a tabela de métricas consolidadas formatada de forma profissional.
    """
    os.makedirs(folder, exist_ok=True)
    
    # Configuração comum de fonte e tamanho para 300 DPI
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["axes.titlesize"] = 13
    
    # (a) Curva de capital acumulada vs CDI
    plt.figure(figsize=(10, 6))
    plt.plot(df_result.index, df_result["capital_estrategia"], label="Estratégia Aegis Momentum LS", color="#111116", linewidth=2.2)
    plt.plot(df_result.index, df_result["capital_cdi"], label="CDI (Benchmark)", color="#86868b", linestyle="--", linewidth=1.8)
    plt.title("Curva de Capital Acumulada vs CDI (B3)", fontweight="bold", pad=12)
    plt.xlabel("Período")
    plt.ylabel("Multiplicador do Capital")
    plt.legend(frameon=True, facecolor="#f9f9fb", edgecolor="#000000")
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "figura_a_curva_capital.png"), dpi=300)
    plt.close()
    
    # (b) Alpha acumulado (excesso vs CDI)
    plt.figure(figsize=(10, 6))
    alpha_acum = df_result["capital_estrategia"] - df_result["capital_cdi"]
    plt.fill_between(df_result.index, alpha_acum, 0, where=(alpha_acum >= 0), color="#e2f0d9", interpolate=True)
    plt.fill_between(df_result.index, alpha_acum, 0, where=(alpha_acum < 0), color="#fce4d6", interpolate=True)
    plt.plot(df_result.index, alpha_acum, color="#2b2b2b", linewidth=2.0)
    plt.axhline(0, color="#111116", linestyle=":", linewidth=1.2)
    plt.title("Evolução do Alpha Acumulado (Excesso de Retorno vs CDI)", fontweight="bold", pad=12)
    plt.xlabel("Período")
    plt.ylabel("Retorno Excedente Acumulado")
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "figura_b_alpha_acumulado.png"), dpi=300)
    plt.close()
    
    # (c) Drawdown pico a vale ao longo do tempo
    plt.figure(figsize=(10, 6))
    capital = df_result["capital_estrategia"]
    max_peak = capital.cummax()
    drawdowns = (capital - max_peak) / max_peak * 100.0
    plt.fill_between(df_result.index, drawdowns, 0, color="#ffc7ce", alpha=0.5)
    plt.plot(df_result.index, drawdowns, color="#9c0006", linewidth=1.5)
    plt.title("Histórico de Drawdowns Pico a Vale (%)", fontweight="bold", pad=12)
    plt.xlabel("Período")
    plt.ylabel("Rebaixamento (%)")
    plt.ylim(top=0)
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "figura_c_drawdown.png"), dpi=300)
    plt.close()
    
    # (d) Mapa de calor de retornos mensais
    plt.figure(figsize=(12, 7))
    ret_mensal = df_result["ret_diario_estratega"].resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0) * 100.0
    df_pivot = pd.DataFrame({
        "Ano": ret_mensal.index.year,
        "Mês": ret_mensal.index.month,
        "Retorno": ret_mensal.values
    })
    meses_nomes = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                   7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    df_pivot["Mês"] = df_pivot["Mês"].map(meses_nomes)
    
    try:
        pivot_table = df_pivot.pivot(index="Ano", columns="Mês", values="Retorno")
        ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        ordem_existente = [m for m in ordem_meses if m in pivot_table.columns]
        pivot_table = pivot_table[ordem_existente]
        
        sns.heatmap(pivot_table, annot=True, fmt=".1f", cmap="RdYlGn", center=0, cbar=True,
                    linewidths=0.5, annot_kws={"size": 10, "weight": "bold"})
        plt.title("Matriz de Retornos Mensais da Estratégia (%)", fontweight="bold", pad=12)
        plt.xlabel("Mês")
        plt.ylabel("Ano")
    except Exception as e:
        plt.text(0.5, 0.5, f"Erro ao gerar Heatmap:\n{e}", ha="center", va="center")
        
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "figura_d_heatmap.png"), dpi=300)
    plt.close()
    
    # (e) Tabela de métricas consolidadas formatada de forma profissional
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axis("off")
    
    # Determinar a interpretação estatística do p-valor
    significancia = "Não Significativo"
    if metrics["p_value"] < 0.01:
        significancia = "Altamente Significativo (99% conf.)"
    elif metrics["p_value"] < 0.05:
        significancia = "Significativo (95% conf.)"
    elif metrics["p_value"] < 0.10:
        significancia = "Marginalmente Significativo (90% conf.)"
        
    table_data = [
        ["Retorno Acumulado Estratégia", f"{metrics['ret_acum_estrategia']:.2f}%"],
        ["Retorno Acumulado CDI", f"{metrics['ret_acum_cdi']:.2f}%"],
        ["Retorno Anualizado Estratégia", f"{metrics['ret_anual_estrategia']:.2f}%"],
        ["Retorno Anualizado CDI", f"{metrics['ret_anual_cdi']:.2f}%"],
        ["Volatilidade Anualizada", f"{metrics['vol_anualizada']:.2f}%"],
        ["Índice Sharpe (vs CDI)", f"{metrics['sharpe']:.2f}"],
        ["Drawdown Máximo", f"{metrics['max_drawdown']:.2f}%"],
        ["% de Meses Positivos", f"{metrics['pct_meses_positivos']:.1f}%"],
        ["Alpha Anualizado (vs CDI)", f"{metrics['alpha_anualizado']:.2f}%"],
        ["Estatística T do Alpha", f"{metrics['t_stat']:.3f}"],
        ["P-Valor do Alpha", f"{metrics['p_value']:.4f} ({significancia})"]
    ]
    
    tab = ax.table(cellText=table_data, colLabels=["Métrica de Desempenho", "Valor"], loc="center", cellLoc="left")
    tab.auto_set_font_size(False)
    tab.set_font_size(10)
    tab.scale(1.2, 1.5)
    
    # Formatação visual da tabela
    for (r_idx, c_idx), cell in tab.get_celld().items():
        cell.set_linewidth(1.2)
        if r_idx == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#111116") # Preto institucional Ceará Finance
        else:
            cell.set_facecolor("#ffffff" if r_idx % 2 == 0 else "#f9f9fb")
            if c_idx == 1:
                cell.set_text_props(weight="bold")
                
    plt.title("Tabela de Métricas Consolidadas do Backtest", fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "figura_e_tabela_metricas.png"), dpi=300)
    plt.close()
    
    print(f"[Figuras] 5 Figuras de alta qualidade exportadas com sucesso na pasta: '{folder}/'")

if __name__ == "__main__":
    d_dict = dados.carregar_dados_completos("2018-01-01", "2024-12-31")
    df_r, met, pos = backtest.rodar_backtest(d_dict, L_meses=12, top_n=10)
    exportar_figuras_publicacao(df_r, met, pos)
