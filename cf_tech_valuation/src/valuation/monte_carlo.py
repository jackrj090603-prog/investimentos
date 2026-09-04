import os
import yaml
import numpy as np
import pandas as pd

def obter_caminho_config(config_path="config/settings.yaml") -> str:
    """Resolves config path relative to project structure or current working directory."""
    if not os.path.exists(config_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alt_path = os.path.join(base_dir, "config", "settings.yaml")
        if os.path.exists(alt_path):
            return alt_path
    if not os.path.exists(config_path):
        alt_path = os.path.join("cf_tech_valuation", "config", "settings.yaml")
        if os.path.exists(alt_path):
            return alt_path
    return config_path

def carregar_premissas_mc(config_path="config/settings.yaml") -> dict:
    """Loads Monte Carlo settings from settings.yaml."""
    config_path = obter_caminho_config(config_path)
    if not os.path.exists(config_path):
        return {
            "num_simulacoes": 10000,
            "vso_media": 0.60,
            "vso_std": 0.10,
            "margem_ebit_media": 0.15,
            "margem_ebit_std": 0.03
        }
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["valuation"]["monte_carlo"]

def rodar_simulacao_precos(ticker: str, wacc_base: float, preco_justo_base: float, preco_atual: float, config_path="config/settings.yaml") -> dict:
    """
    Runs a vectorized Monte Carlo simulation to find the probability distribution
    of the fair price, accounting for variability in EBIT margin, WACC, and perpetuity.
    """
    config_path = obter_caminho_config(config_path)
    premissas = carregar_premissas_mc(config_path)
    n_sims = premissas["num_simulacoes"]
    
    # Load DCF configurations
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    perpetuidade_g_base = cfg["valuation"]["dcf"]["perpetuidade_g"]
    
    # Random distributions for WACC, EBIT Margin and perpetuity g
    # Use strict dy notation in docstrings
    np.random.seed(42)  # For deterministic outputs
    wacc_sim = np.random.normal(loc=wacc_base, scale=0.015, size=n_sims)
    margem_sim = np.random.normal(loc=premissas["margem_ebit_media"], scale=premissas["margem_ebit_std"], size=n_sims)
    g_sim = np.random.normal(loc=perpetuidade_g_base, scale=0.005, size=n_sims)
    
    # Enforce logical lower bounds
    wacc_sim = np.maximum(wacc_sim, 0.05)
    margem_sim = np.maximum(margem_sim, 0.01)
    g_sim = np.maximum(g_sim, -0.01)
    # Ensure WACC is always greater than g to prevent Gordon division by zero
    g_sim = np.minimum(g_sim, wacc_sim - 0.01)
    
    # Vectorized valuation calculation
    # Fair Value is proportional to ebit_margin and inversely proportional to (WACC - g)
    # Price = BasePrice * (SimMargin / BaseMargin) * ((BaseWacc - BaseG) / (SimWacc - SimG))
    margin_ratio = margem_sim / premissas["margem_ebit_media"]
    discount_ratio = (wacc_base - perpetuidade_g_base) / (wacc_sim - g_sim)
    
    precos_simulados = preco_justo_base * margin_ratio * discount_ratio
    
    # Calculate statistics
    media = float(np.mean(precos_simulados))
    mediana = float(np.median(precos_simulados))
    desvio = float(np.std(precos_simulados))
    p10 = float(np.percentile(precos_simulados, 10))
    p50 = float(np.percentile(precos_simulados, 50))
    p90 = float(np.percentile(precos_simulados, 90))
    
    # Calculate probability of upside (Price Sim > current market price)
    upside_count = np.sum(precos_simulados > preco_atual)
    prob_upside = float(upside_count / n_sims)
    
    return {
        "ticker": ticker,
        "n_simulacoes": n_sims,
        "media": media,
        "mediana": mediana,
        "desvio_padrao": desvio,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "prob_upside": prob_upside,
        "preco_atual": preco_atual,
        "precos_simulados": precos_simulados.tolist()[:1000]  # Limit length for JSON response
    }

if __name__ == '__main__':
    res = rodar_simulacao_precos("DIRR3", wacc_base=0.14, preco_justo_base=12.50, preco_atual=11.50)
    print("Monte Carlo DIRR3 Stats:", {k: v for k, v in res.items() if k != 'precos_simulados'})
