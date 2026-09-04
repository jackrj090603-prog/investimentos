import os
import yaml
import pandas as pd
import numpy as np

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

def carregar_premissas_dcf(config_path="config/settings.yaml") -> dict:
    """Loads DCF and perpetuity growth assumptions from settings.yaml."""
    config_path = obter_caminho_config(config_path)
    if not os.path.exists(config_path):
        return {
            "anos_projecao": 5,
            "perpetuidade_g": 0.025
        }
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["valuation"]["dcf"]

def projetar_fluxos_fcff(receita_inicial: float, margem_ebit: float, tax_rate: float, anos: int, crescimento_receita: float = 0.05) -> list:
    """
    Projects Free Cash Flow to Firm (FCFF) for N years.
    
    Differential changes in variables are represented as dy steps.
    """
    fluxos = []
    receita = receita_inicial
    
    # Premissas de reinvestimento (capex, nwc)
    capex_percent = 0.02
    nwc_percent = 0.08
    
    for dy_year in range(1, anos + 1):
        # dy_year represents the step differential in the time horizon
        receita *= (1.0 + crescimento_receita)
        ebit = receita * margem_ebit
        ebit_after_tax = ebit * (1.0 - tax_rate)
        
        # FCFF = EBIT*(1-T) + Depr - Capex - Delta_NWC
        # We proxy Depr/Capex/NWC for simplicity
        reinvestimento = receita * (capex_percent + nwc_percent)
        fcff = ebit_after_tax - reinvestimento
        fluxos.append(fcff)
        
    return fluxos

def calcular_dcf_fair_value(ticker: str, wacc: float, kpis_path="data/processed/kpis_calculados.parquet", config_path="config/settings.yaml") -> dict:
    """
    Executes the DCF model for the company, mapping debt and equity 
    dynamically from processed Parquet files and global configurations.
    """
    dcf_premissas = carregar_premissas_dcf(config_path)
    anos = dcf_premissas["anos_projecao"]
    perpetuidade_g = dcf_premissas["perpetuidade_g"]  # dy growth rate
    
    # Load settings.yaml to check tax rate
    config_path = obter_caminho_config(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    tax_rate = cfg["valuation"]["wacc"]["aliquota_imposto"]
    
    # Load KPIs dataset
    if not os.path.exists(kpis_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alt_kpi = os.path.join(base_dir, "data", "processed", "kpis_calculados.parquet")
        if os.path.exists(alt_kpi):
            kpis_path = alt_kpi
            
    if not os.path.exists(kpis_path):
        print(f"[DCF Model] KPIs file {kpis_path} not found. Running Indicators engine...")
        from processing.indicator_engine import calcular_indicadores_financeiros
        df_kpi = calcular_indicadores_financeiros()
    else:
        df_kpi = pd.read_parquet(kpis_path)
        
    # Find company information
    # Look for matching denom_cia containing ticker or exact match
    company_row = df_kpi[df_kpi["denom_cia"].str.contains(ticker[:4], case=False, na=False)]
    
    if company_row.empty:
        # Fallback values if ticker not in CVM database yet
        print(f"[DCF Model] Empresa {ticker} não encontrada no banco CVM. Usando fallbacks operacionais.")
        receita_inicial = 2000000000.0
        margem_ebit = 0.15
        divida_liquida = 300000000.0
        denom = ticker
    else:
        receita_inicial = float(company_row["receita_ltm"].values[0])
        margem_ebit = float(company_row["margem_ebit"].values[0])
        divida_liquida = float(company_row["divida_liquida"].values[0])
        denom = str(company_row["denom_cia"].values[0])
        
    # Project 5 years
    fluxos = projetar_fluxos_fcff(receita_inicial, margem_ebit, tax_rate, anos)
    
    # Discount future cash flows
    vp_fluxos = []
    for dy_idx, f in enumerate(fluxos):
        vp = f / ((1.0 + wacc) ** (dy_idx + 1))
        vp_fluxos.append(vp)
        
    soma_vp = sum(vp_fluxos)
    
    # Terminal Value (Gordon Growth)
    # TV_5 = FCFF_5 * (1 + g) / (WACC - g)
    fluxo_terminal = fluxos[-1] * (1.0 + perpetuidade_g)
    valor_terminal = fluxo_terminal / (wacc - perpetuidade_g)
    vp_valor_terminal = valor_terminal / ((1.0 + wacc) ** anos)
    
    enterprise_value = soma_vp + vp_valor_terminal
    equity_value = enterprise_value - divida_liquida
    
    # Fetch number of shares or use placeholder (e.g. 100M shares)
    num_acoes = 200000000.0  # 200 million shares default
    if "DIRR3" in ticker:
        num_acoes = 173000000.0
    elif "PETR4" in ticker:
        num_acoes = 13000000000.0
    elif "VALE3" in ticker:
        num_acoes = 4500000000.0
        
    preco_justo = equity_value / num_acoes
    
    return {
        "ticker": ticker,
        "denom_cia": denom,
        "receita_inicial": receita_inicial,
        "margem_ebit": margem_ebit,
        "wacc": wacc,
        "enterprise_value": enterprise_value,
        "divida_liquida": divida_liquida,
        "equity_value": equity_value,
        "num_acoes": num_acoes,
        "preco_justo": preco_justo,
        "fluxos_projetados": fluxos,
        "vp_fluxos": vp_fluxos,
        "valor_terminal": valor_terminal,
        "vp_valor_terminal": vp_valor_terminal
    }

if __name__ == '__main__':
    res = calcular_dcf_fair_value("DIRR3", wacc=0.14)
    print("DCF DIRR3:", res)
