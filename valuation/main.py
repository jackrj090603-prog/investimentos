import yaml
import os
import pandas as pd
import numpy as np
from src.wacc import calcular_beta, calcular_ke, calcular_wacc, desalavancar_beta, realavancar_beta
from src.dcf import projetar_fluxos, calcular_dcf, gerar_tabela_sensibilidade
from src.monte_carlo import rodar_simulacao, calcular_estatisticas, plotar_histograma

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("=====================================================================")
    print("         CEARÁ FINANCE - MOTOR DE VALUATION v1.0                     ")
    print("=====================================================================\n")
    
    # 1. Carregar Configurações
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config', 'premissas.yaml')
    
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo de premissas não encontrado em {config_path}")
        return
        
    premissas = load_config(config_path)
    
    # Extract metadata
    ticker = premissas['ativo']['ticker']
    indice = premissas['ativo']['indice']
    cotacao_atual = premissas['ativo']['cotacao_atual']
    num_acoes = premissas['ativo']['num_acoes']
    divida_liquida = premissas['ativo']['divida_liquida']
    
    # 2. Módulo 4a: Cálculo do WACC com Regressão do Beta
    print(">>> SPRINT 4.1: Estimando WACC...")
    beta_alavancado = calcular_beta(ticker, index_ticker=indice, period='2y')
    
    rf = premissas['wacc']['taxa_livre_risco']
    erp = premissas['wacc']['premio_risco_mercado']
    kd = premissas['wacc']['custo_divida']
    tax_rate = premissas['wacc']['aliquota_imposto']
    de_ratio = premissas['wacc']['de_ratio']
    
    # Unlever and Relever beta to verify Hamada Formula logic
    beta_u = desalavancar_beta(beta_alavancado, de_ratio, tax_rate)
    beta_l = realavancar_beta(beta_u, de_ratio, tax_rate)
    
    ke = calcular_ke(rf, beta_l, erp)
    wacc_final = calcular_wacc(ke, kd, de_ratio, tax_rate)
    
    print("\n--- Componentes do WACC ---")
    print(f"• Beta de Mercado (Alavancado): {beta_l:.2f}")
    print(f"• Beta Desalavancado (Hamada): {beta_u:.2f}")
    print(f"• Custo do Capital Próprio (Ke): {ke:.2%}")
    print(f"• Custo da Dívida depois do Imposto (Kd * (1 - T)): {kd * (1.0 - tax_rate):.2%}")
    print(f"• Estrutura de Capital (D/E): {de_ratio:.2f}")
    print(f"• Alíquota Efetiva de Imposto (RET): {tax_rate:.1%}")
    print(f"• WACC Estimado Final: {wacc_final:.2%}\n")
    
    # 3. Módulo 4b: Projeção de Fluxos e DCF
    print(">>> SPRINT 4.2: Projetando Fluxos e DCF...")
    fluxos = projetar_fluxos(premissas)
    
    g = premissas['projecao']['perpetuidade_g']
    dcf_res = calcular_dcf(fluxos, wacc_final, g, divida_liquida, num_acoes)
    
    print("\n--- Demonstração Financeira Projetada (FCFF) ---")
    for ano, flow in enumerate(fluxos, start=1):
        print(f"• Ano {ano}: R$ {flow:,.2f}  |  VP: R$ {dcf_res['vp_fluxos'][ano-1]:,.2f}")
    
    print("\n--- Resultados do DCF (Cenário Base) ---")
    print(f"• Enterprise Value (EV): R$ {dcf_res['enterprise_value']:,.2f}")
    print(f"• (-) Dívida Líquida: R$ {divida_liquida:,.2f}")
    print(f"• (=) Equity Value: R$ {dcf_res['equity_value']:,.2f}")
    print(f"• (/) Número de Ações: {num_acoes:,}")
    print(f"• (=) Valor Justo por Ação (Cenário Base): R$ {dcf_res['valor_por_acao']:.2f}")
    print(f"• Cotação Atual: R$ {cotacao_atual:.2f}")
    
    upside = (dcf_res['valor_por_acao'] / cotacao_atual) - 1.0
    print(f"• Upside Potencial: {upside:.1%}\n")
    
    # 4. Tabela de Sensibilidade
    print(">>> Gerando Tabela de Sensibilidade (WACC × g)...")
    wacc_range = [wacc_final - 0.02, wacc_final - 0.01, wacc_final, wacc_final + 0.01, wacc_final + 0.02]
    g_range = [g - 0.01, g - 0.005, g, g + 0.005, g + 0.01]
    
    df_sens = gerar_tabela_sensibilidade(wacc_range, g_range, premissas)
    print("\n--- Tabela de Sensibilidade (Valor por Ação - R$) ---")
    pd.set_option('display.float_format', lambda x: '%.2f' % x)
    print(df_sens)
    print()
    
    # 5. Módulo 5: Simulação de Monte Carlo
    print(">>> MÓDULO 5: Executando Simulação de Monte Carlo (10.000 iterações)...")
    n_sim = premissas['monte_carlo']['num_simulacoes']
    precos_simulados = rodar_simulacao(premissas, beta_l, n_simulacoes=n_sim)
    
    stats = calcular_estatisticas(precos_simulados, cotacao_atual)
    
    print("\n--- Estatísticas do Monte Carlo ---")
    print(f"• Preço Médio Simulado: R$ {stats['media']:.2f}")
    print(f"• Preço Mediano Simulado (P50): R$ {stats['mediana']:.2f}")
    print(f"• Desvio Padrão: R$ {stats['desvio_padrao']:.2f}")
    print(f"• Percentil P10 (Pior Cenário): R$ {stats['p10']:.2f}")
    print(f"• Percentil P90 (Melhor Cenário): R$ {stats['p90']:.2f}")
    print(f"• Probabilidade de Upside (P(Valor Justo > Cotação Atual)): {stats['prob_upside']:.1%}\n")
    
    # Plot histogram
    image_path = os.path.join(base_dir, 'monte_carlo_distribution.png')
    plotar_histograma(precos_simulados, stats, cotacao_atual, image_path)
    
    print("=====================================================================")
    print("         VALUATION EXECUTADO COM SUCESSO!                            ")
    print("=====================================================================")

if __name__ == "__main__":
    main()
