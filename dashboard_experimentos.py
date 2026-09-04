import streamlit as st
import pandas as pd
import numpy as np
import os
import itertools
import matplotlib.pyplot as plt
import seaborn as sns
import dados
import backtest
import graficos
import figuras

# Configurar página Streamlit
st.set_page_config(page_title="Aegis Momentum LS — Lab de Experimentos", layout="wide")

# Exibir logotipo do Ceará Finance
col_logo, col_title = st.columns([0.1, 0.9])
with col_logo:
    if os.path.exists("Mira/LOGO_CF.png"):
        st.image("Mira/LOGO_CF.png", width=80)
    elif os.path.exists("../Mira/LOGO_CF.png"):
        st.image("../Mira/LOGO_CF.png", width=80)
with col_title:
    st.title("🛡️ Aegis Momentum Long-Short — Laboratório de Experimentos")
    st.write("Liga de Mercado Financeiro da UFC — Ceará Finance")

# Inicializar cache de dados
@st.cache_resource
def carregar_dados_sistema():
    with st.spinner("Carregando cotações históricas da B3 e dados do CDI... (Aproveitando cache se disponível)"):
        return dados.carregar_dados_completos()

data_dict = carregar_dados_sistema()

# Sidebar: Painel de Controle de Grade de Experimentos
st.sidebar.header("⚙️ Configurações da Otimização (Grid Search)")

# Opções de parametrização
lookbacks_selecionados = st.sidebar.multiselect("Janelas de Lookback (L meses)", [3, 6, 9, 12, 18], default=[6, 12])
ativos_selecionados = st.sidebar.multiselect("Nº de Ativos por Perna (Top N)", [3, 5, 10, 15], default=[5, 10])
estilo_estrategia = st.sidebar.multiselect("Estilo da Operação", ["Long-Short", "Long-Only"], default=["Long-Short", "Long-Only"])
custos_bps_opcao = st.sidebar.multiselect("Custos de Transação (bps)", [0, 5, 10, 20], default=[10])

run_grid_search = st.sidebar.button("🚀 Rodar Grade de Experimentos")

# Função para avaliar vieses e salvar experimentos.md
def gerar_resumo_executivo_md(df_exp, filepath="experimentos.md"):
    if df_exp.empty:
        return
        
    top_sharpe = df_exp.sort_values("sharpe", ascending=False).iloc[0]
    worst_sharpe = df_exp.sort_values("sharpe", ascending=True).iloc[0]
    
    # Detecção de vieses automática
    alertas = []
    if (df_exp["custo_bps"] == 0).any():
        alertas.append("- **⚠️ Alerta de Custos Irrealistas:** Existem experimentos com custo de transação = 0 bps. Lembre-se de que os custos de corretagem e slippage deterioram o momentum na B3.")
    if (df_exp["top_n"] <= 3).any():
        alertas.append("- **⚠️ Alerta de Concentração:** Algumas carteiras operam com 3 ou menos ativos por perna. Isso eleva significativamente o risco não-sistemático (idiossincrático).")
    if len(df_exp) > 50:
        alertas.append("- **⚠️ Risco de Overfitting (Data Snooping):** Muitas configurações testadas na mesma base histórica aumentam a probabilidade de achar uma estratégia vencedora por puro azar estatístico.")
        
    alertas_str = "\n".join(alertas) if alertas else "- **✅ Sem alertas graves detectados.** As premissas estão condizentes com o rigor operacional."
    
    md_content = f"""# Resumo Executivo dos Experimentos Quantitativos
*Gerado automaticamente pelo laboratório Aegis Momentum LS*

### 🏆 Melhor Configuração (Sharpe Máximo)
- **Lookback:** {top_sharpe['lookback']} meses
- **Nº Ativos:** {top_sharpe['top_n']} por perna
- **Operação:** {top_sharpe['estilo']}
- **Sharpe Ratio:** {top_sharpe['sharpe']:.2f}
- **Retorno Anualizado:** {top_sharpe['ret_anual']:.2f}% (vs CDI de {top_sharpe['ret_cdi_anual']:.2f}%)
- **Alpha Anualizado:** {top_sharpe['alpha_anual']:.2f}%
- **Max Drawdown:** {top_sharpe['max_dd']:.2f}%
- **Custo Operacional:** {top_sharpe['custo_bps']} bps

### 📉 Pior Configuração (Sharpe Mínimo)
- **Lookback:** {worst_sharpe['lookback']} meses | **Ativos:** {worst_sharpe['top_n']} | **Estilo:** {worst_sharpe['estilo']} | **Sharpe:** {worst_sharpe['sharpe']:.2f}

### 🕵️ Análise Automática de Vieses e Riscos
{alertas_str}

### 🔬 Racional Metodológico
A estratégia de momentum baseia-se no prêmio de prorrogação de tendência (Jegadeesh & Titman, 1993). Na B3, o custo de transação de rebalanceamento mensal (slippage + emolumentos) e o custo de aluguel de ações (BTC) na perna vendida (simulado em 2% a.a.) são fatores determinantes para a viabilidade real do Alpha.
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

# Lógica do Grid Search
csv_path = "experimentos.csv"

if run_grid_search:
    if not lookbacks_selecionados or not ativos_selecionados or not estilo_estrategia or not custos_bps_opcao:
        st.error("Selecione pelo menos uma opção em cada parâmetro na barra lateral!")
    else:
        # Calcular produto cartesiano
        grid = list(itertools.product(lookbacks_selecionados, ativos_selecionados, estilo_estrategia, custos_bps_opcao))
        st.write(f"Iniciando varredura de **{len(grid)}** combinações paramétricas...")
        
        progress_bar = st.progress(0)
        resultados = []
        
        for idx, (L, N, estilo, custos) in enumerate(grid):
            long_only = (estilo == "Long-Only")
            # Rodar backtest
            _, metrics, _ = backtest.rodar_backtest(
                data_dict, L_meses=L, top_n=N, long_only=long_only, custo_bps=custos
            )
            
            resultados.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "lookback": L,
                "top_n": N,
                "estilo": estilo,
                "custo_bps": custos,
                "ret_acum": metrics["ret_acum_estrategia"],
                "ret_cdi_acum": metrics["ret_acum_cdi"],
                "ret_anual": metrics["ret_anual_estrategia"],
                "ret_cdi_anual": metrics["ret_anual_cdi"],
                "vol_anual": metrics["vol_anualizada"],
                "sharpe": metrics["sharpe"],
                "max_dd": metrics["max_drawdown"],
                "pct_meses_pos": metrics["pct_meses_positivos"],
                "alpha_anual": metrics["alpha_anualizado"],
                "t_stat": metrics["t_stat"],
                "p_value": metrics["p_value"]
            })
            
            progress_bar.progress((idx + 1) / len(grid))
            
        df_novos = pd.DataFrame(resultados)
        
        # Concatenar com histórico se existir
        if os.path.exists(csv_path):
            df_antigo = pd.read_csv(csv_path)
            df_final = pd.concat([df_antigo, df_novos], ignore_index=True).drop_duplicates(
                subset=["lookback", "top_n", "estilo", "custo_bps"], keep="last"
            )
        else:
            df_final = df_novos
            
        df_final.to_csv(csv_path, index=False)
        gerar_resumo_executivo_md(df_final)
        st.success("Varredura concluída com sucesso! Histórico de experimentos atualizado.")

# Carregar histórico de experimentos
if os.path.exists(csv_path):
    df_exp = pd.read_csv(csv_path)
    
    st.header("📊 Painel Geral de Performance dos Experimentos")
    
    col1, col2 = st.columns([0.65, 0.35])
    
    with col1:
        st.subheader("Grade de Resultados Salvos")
        # Mostrar tabela formatada
        st.dataframe(df_exp.style.format({
            "ret_acum": "{:.1f}%", "ret_anual": "{:.1f}%", "vol_anual": "{:.1f}%", 
            "sharpe": "{:.2f}", "max_dd": "{:.1f}%", "alpha_anual": "{:.1f}%", "p_value": "{:.4f}"
        }))
        
    with col2:
        st.subheader("🎯 Resumo do Melhor Modelo")
        if os.path.exists("experimentos.md"):
            with open("experimentos.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
                
    st.markdown("---")
    st.header("📈 Análises Visuais do Comportamento Paramétrico")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Fronteira Eficiente (Sharpe vs Max Drawdown)")
        # Gráfico interativo ou scatter plot com Matplotlib
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.scatterplot(data=df_exp, x="max_dd", y="sharpe", hue="estilo", size="lookback", sizes=(30, 200), ax=ax, palette="dark")
        ax.set_xlabel("Máximo Drawdown (%)")
        ax.set_ylabel("Índice Sharpe")
        ax.set_title("Otimização Multi-Objetivo (Minimizar Risco vs Maximizar Sharpe)")
        st.pyplot(fig)
        plt.close()
        
    with col_g2:
        st.subheader("Matriz de Sensibilidade do Sharpe Ratio (Heatmap)")
        # Heatmap para estratégia Long-Short com custo de 10 bps
        df_ls_10 = df_exp[(df_exp["estilo"] == "Long-Short") & (df_exp["custo_bps"] == 10)]
        if not df_ls_10.empty:
            try:
                pivot_exp = df_ls_10.pivot(index="lookback", columns="top_n", values="sharpe")
                fig, ax = plt.subplots(figsize=(8, 5))
                sns.heatmap(pivot_exp, annot=True, fmt=".2f", cmap="viridis", ax=ax)
                ax.set_xlabel("Número de Ativos (Perna)")
                ax.set_ylabel("Lookback (Meses)")
                st.pyplot(fig)
                plt.close()
            except Exception as e:
                st.write("Não foi possível pivotar os dados para gerar o Heatmap. Execute mais lookbacks e ativos na barra lateral.")
        else:
            st.info("Execute experimentos no estilo 'Long-Short' com custo de 10 bps na barra lateral para ver o heatmap de sensibilidade.")
            
    st.markdown("---")
    st.header("🔍 Detalhamento e Diagnóstico de uma Configuração Específica")
    
    # Seleção de uma configuração específica no histórico
    df_exp["label"] = df_exp.apply(lambda r: f"L={r['lookback']}m | N={r['top_n']} | {r['estilo']} | Cost={r['custo_bps']}bps", axis=1)
    label_selecionada = st.selectbox("Escolha uma configuração para ver a carteira e gerar os relatórios:", df_exp["label"])
    
    if label_selecionada:
        row_sel = df_exp[df_exp["label"] == label_selecionada].iloc[0]
        st.write(f"**Análise detalhada de:** {label_selecionada}")
        
        # Executar o backtest completo dessa config para extrair dados diários e posições
        long_only = (row_sel["estilo"] == "Long-Only")
        df_r, met, pos = backtest.rodar_backtest(
            data_dict, L_meses=row_sel["lookback"], top_n=row_sel["top_n"], 
            long_only=long_only, custo_bps=row_sel["custo_bps"]
        )
        
        col_det1, col_det2 = st.columns([0.4, 0.6])
        
        with col_det1:
            st.subheader("Último Rebalanceamento da Carteira")
            if pos:
                ultima = pos[-1]
                st.write(f"**Data:** {ultima['data'].strftime('%d/%m/%Y')}")
                st.write("**🛡️ Perna Long (Comprados):**")
                st.write(", ".join(ultima["longs"]))
                
                if not long_only:
                    st.write("**⚔️ Perna Short (Vendidos):**")
                    st.write(", ".join(ultima["shorts"]))
            else:
                st.info("Sem posições históricas encontradas.")
                
            # Exibir métricas de t-test
            st.write("### Rigor Estatístico")
            st.metric("Estatística T do Alpha", f"{met['t_stat']:.3f}")
            sig_texto = "Sim" if met["p_value"] < 0.05 else "Não"
            st.metric("Alpha Estatisticamente Significante? (p < 5%)", sig_texto)
            st.metric("P-Valor do Teste-T", f"{met['p_value']:.4f}")
            
        with col_det2:
            st.subheader("Curva de Capital da Configuração Selecionada")
            # Plotar a curva de capital
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.plot(df_r.index, df_r["capital_estrategia"], label="Estratégia Selecionada", color="#a472ff", linewidth=2)
            ax.plot(df_r.index, df_r["capital_cdi"], label="CDI", color="#7d80a8", linestyle="--", linewidth=1.5)
            ax.set_ylabel("Multiplicador de Capital")
            ax.legend()
            st.pyplot(fig)
            plt.close()
            
            # Botão para exportar os gráficos em 300 DPI e PDF
            if st.button("💾 Exportar Figuras de Publicação (DPI 300)"):
                figuras.exportar_figuras_publicacao(df_r, met, pos)
                st.success("Os 5 arquivos de imagem (.png) com alta resolução foram salvos na pasta 'figuras/' do seu computador!")

else:
    st.info("Nenhum experimento histórico encontrado. Configure os parâmetros na barra lateral e clique em 'Rodar Grade de Experimentos' para iniciar.")
