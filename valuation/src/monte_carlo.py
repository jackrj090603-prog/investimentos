import numpy as np
import matplotlib.pyplot as plt
import copy
from src.wacc import calcular_ke, calcular_wacc
from src.dcf import projetar_fluxos, calcular_dcf

def rodar_simulacao(premissas: dict, beta_base: float, n_simulacoes: int = 10000) -> np.ndarray:
    """
    Runs the Monte Carlo simulation loop by drawing parameters from triangular distributions.
    Returns an array of simulated stock prices.
    """
    mc_config = premissas['monte_carlo']
    dists = mc_config['distribuicoes']
    
    divida_liquida = premissas['ativo']['divida_liquida']
    num_acoes = premissas['ativo']['num_acoes']
    erp = premissas['wacc']['premio_risco_mercado']
    de_ratio = premissas['wacc']['de_ratio']
    tax_rate = premissas['wacc']['aliquota_imposto']
    
    precos_simulados = []
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    for _ in range(n_simulacoes):
        # Draw parameters from triangular distributions [min, mode, max]
        vso_draw = np.random.triangular(dists['vso_media'][0], dists['vso_media'][1], dists['vso_media'][2])
        margem_draw = np.random.triangular(dists['margem_ebit'][0], dists['margem_ebit'][1], dists['margem_ebit'][2])
        g_draw = np.random.triangular(dists['perpetuidade_g'][0], dists['perpetuidade_g'][1], dists['perpetuidade_g'][2])
        rf_draw = np.random.triangular(dists['taxa_livre_risco'][0], dists['taxa_livre_risco'][1], dists['taxa_livre_risco'][2])
        kd_draw = np.random.triangular(dists['custo_divida'][0], dists['custo_divida'][1], dists['custo_divida'][2])
        
        # Calculate simulated WACC
        ke_sim = calcular_ke(rf_draw, beta_base, erp)
        wacc_sim = calcular_wacc(ke_sim, kd_draw, de_ratio, tax_rate)
        
        # Clone premissas to avoid mutating original config
        sim_premissas = copy.deepcopy(premissas)
        sim_premissas['projecao']['vso'] = [vso_draw] * 5
        sim_premissas['projecao']['margem_ebit'] = margem_draw
        sim_premissas['wacc']['aliquota_imposto'] = tax_rate
        
        # Project cash flows and calculate DCF valuation
        fluxos_sim = projetar_fluxos(sim_premissas)
        dcf_res = calcular_dcf(fluxos_sim, wacc_sim, g_draw, divida_liquida, num_acoes)
        
        precos_simulados.append(dcf_res['valor_por_acao'])
        
    return np.array(precos_simulados)

def calcular_estatisticas(precos_simulados: np.ndarray, cotacao_atual: float) -> dict:
    """
    Calculates summary statistics and percentiles for the simulated stock prices.
    """
    mean_val = np.mean(precos_simulados)
    median_val = np.median(precos_simulados)
    std_val = np.std(precos_simulados)
    
    p10 = np.percentile(precos_simulados, 10)
    p50 = np.percentile(precos_simulados, 50)
    p90 = np.percentile(precos_simulados, 90)
    
    # Probability that intrinsic value is greater than the current stock price
    prob_upside = np.mean(precos_simulados > cotacao_atual)
    
    return {
        "media": mean_val,
        "mediana": median_val,
        "desvio_padrao": std_val,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "prob_upside": prob_upside
    }

def plotar_histograma(precos_simulados: np.ndarray, stats: dict, cotacao_atual: float, save_path: str):
    """
    Generates and saves a beautiful distribution histogram of the simulated prices.
    """
    plt.figure(figsize=(10, 6))
    
    # Set Ceará Finance theme colors
    primary_color = "#1f77b4"  # Dark Blue
    accent_color = "#ff7f0e"   # Orange
    bg_color = "#f5f5f5"       # Light gray
    
    # Plot histogram
    n, bins, patches = plt.hist(precos_simulados, bins=50, edgecolor='black', alpha=0.75, color=primary_color)
    
    # Add vertical lines for key metrics
    plt.axvline(stats['p10'], color='red', linestyle='--', linewidth=1.5, label=f'P10: R$ {stats["p10"]:.2f}')
    plt.axvline(stats['p50'], color='green', linestyle='-', linewidth=1.5, label=f'P50 (Mediana): R$ {stats["p50"]:.2f}')
    plt.axvline(stats['p90'], color='blue', linestyle='--', linewidth=1.5, label=f'P90: R$ {stats["p90"]:.2f}')
    
    # Current stock price line
    plt.axvline(cotacao_atual, color=accent_color, linestyle='-', linewidth=2.5, label=f'Cotação Atual: R$ {cotacao_atual:.2f}')
    
    # Labels and titles
    plt.title('Simulação de Monte Carlo - Valor Intrínseco DIRR3', fontsize=14, fontweight='bold')
    plt.xlabel('Preço Justo por Ação (R$)', fontsize=12)
    plt.ylabel('Frequência (Simulações)', fontsize=12)
    
    # Formatting grid and layout
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper right', frameon=True, facecolor=bg_color)
    
    # Annotate probability of upside
    plt.text(
        0.05, 0.95,
        f"Prob. Upside: {stats['prob_upside']:.1%}\nMédia: R$ {stats['media']:.2f}\nMediana: R$ {stats['mediana']:.2f}",
        transform=plt.gca().transAxes,
        verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8, edgecolor='gray')
    )
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"Histograma de Monte Carlo salvo em: {save_path}")
