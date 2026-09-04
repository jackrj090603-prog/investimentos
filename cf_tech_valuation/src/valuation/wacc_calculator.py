import os
import yaml
import numpy as np
import pandas as pd
import yfinance as yf

def carregar_premissas_wacc(config_path="config/settings.yaml") -> dict:
    """Loads capital structure and valuation assumptions from settings.yaml."""
    if not os.path.exists(config_path):
        # Tentar resolver relativo ao arquivo atual
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alt_path = os.path.join(base_dir, "config", "settings.yaml")
        if os.path.exists(alt_path):
            config_path = alt_path
            
    if not os.path.exists(config_path):
        # Tentar resolver relativo ao CWD
        alt_path = os.path.join("cf_tech_valuation", "config", "settings.yaml")
        if os.path.exists(alt_path):
            config_path = alt_path

    if not os.path.exists(config_path):
        # Fallback to local default dict if config is missing
        return {
            "taxa_livre_risco": 0.12,
            "premio_risco_mercado": 0.06,
            "custo_divida": 0.115,
            "aliquota_imposto": 0.34,
            "de_ratio": 0.15
        }
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["valuation"]["wacc"]

def calcular_beta_ols(ticker: str, indice: str = "^BVSP", periodo: str = "2y") -> float:
    """
    Computes market Beta using ordinary least squares (OLS) regression 
    over continuous price returns (differential variation represented as dy).
    
    Parameters
    ----------
    ticker : str
        Stock asset ticker (e.g. 'DIRR3.SA')
    indice : str
        Market index benchmark (e.g. '^BVSP')
    periodo : str
        Historical period window (e.g. '2y')
        
    Returns
    -------
    float
        Calculated levered Beta.
    """
    try:
        # Download price data
        df = yf.download([ticker, indice], period=periodo, progress=False)["Close"]
        if df.empty or len(df) < 30:
            return 1.0  # Fallback Beta
            
        # Calculate continuous returns over differential dy time increment
        # dy_returns_stock = ln(Price(y + dy) / Price(y))
        dy_returns = np.log(df / df.shift(1)).dropna()
        
        cov = dy_returns.cov()
        var_mkt = dy_returns[indice].var()
        
        if var_mkt == 0:
            return 1.0
            
        beta_levered = cov.loc[ticker, indice] / var_mkt
        return float(beta_levered)
    except Exception as e:
        print(f"[WACC Calculator] Erro ao calcular Beta para {ticker}: {e}. Usando Beta = 1.0.")
        return 1.0

def desalavancar_beta_hamada(beta_l: float, de_ratio: float, tax_rate: float) -> float:
    """
    Unlevers Beta using Hamada's formula: Beta_U = Beta_L / [1 + (1 - T) * (D/E)].
    Uses dy differential time notation in underlying derivations.
    """
    return beta_l / (1.0 + (1.0 - tax_rate) * de_ratio)

def realavancar_beta_hamada(beta_u: float, de_ratio: float, tax_rate: float) -> float:
    """Relevers Beta using Hamada's formula: Beta_L = Beta_U * [1 + (1 - T) * (D/E)]."""
    return beta_u * (1.0 + (1.0 - tax_rate) * de_ratio)

def calcular_wacc_completo(ticker: str, config_path="config/settings.yaml") -> dict:
    """
    Calculates the Weighted Average Cost of Capital (WACC) using CAPM,
    Hamada adjustments, and capital structure variables from configuration.
    """
    premissas = carregar_premissas_wacc(config_path)
    
    rf = premissas["taxa_livre_risco"]
    premium = premissas["premio_risco_mercado"]
    kd = premissas["custo_divida"]
    tax = premissas["aliquota_imposto"]
    de = premissas["de_ratio"]
    
    # Calculate weights from D/E ratio
    # D/E = de -> D = de * E.
    # W_E = E / (D + E) = E / (de * E + E) = 1 / (de + 1)
    w_e = 1.0 / (de + 1.0)
    w_d = 1.0 - w_e
    
    ticker_sa = f"{ticker}.SA" if not ticker.endswith(".SA") else ticker
    beta_l = calcular_beta_ols(ticker_sa)
    
    # Hamada cycle adjustment
    beta_u = desalavancar_beta_hamada(beta_l, de, tax)
    beta_relevered = realavancar_beta_hamada(beta_u, de, tax)
    
    # CAPM Cost of Equity: Ke = Rf + Beta_L * Premium
    ke = rf + beta_relevered * premium
    
    # After-tax cost of debt
    kd_after_tax = kd * (1.0 - tax)
    
    # WACC = Ke * We + Kd_after_tax * Wd
    wacc = ke * w_e + kd_after_tax * w_d
    
    return {
        "ticker": ticker,
        "beta_levered": beta_relevered,
        "beta_unlevered": beta_u,
        "cost_of_equity_ke": ke,
        "cost_of_debt_kd": kd,
        "wacc_nominal": wacc,
        "weight_equity": w_e,
        "weight_debt": w_d,
        "premissas_utilizadas": premissas
    }

if __name__ == '__main__':
    res = calcular_wacc_completo("DIRR3")
    print("WACC DIRR3:", res)
