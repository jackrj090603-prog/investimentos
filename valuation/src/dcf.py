import pandas as pd
import numpy as np

def projetar_fluxos(premissas: dict) -> list:
    """
    Projects Free Cash Flow to the Firm (FCFF) for the next 5 years using the corporate drivers:
    VGV Lançado -> VSO -> Vendas -> POC -> Receita -> Margem EBIT -> NOPAT -> FCFF.
    """
    proj_config = premissas['projecao']
    wacc_config = premissas['wacc']
    
    vgv_lancado = proj_config['vgv_lancado']
    vso = proj_config['vso']
    poc = proj_config['poc']
    margem_ebit = proj_config['margem_ebit']
    tax_rate = wacc_config['aliquota_imposto']
    
    depreciacao_percent = proj_config['depreciacao_percent']
    capex_percent = proj_config['capex_percent']
    nwc_percent = proj_config['nwc_percent']
    
    # 1. Calcular Vendas Líquidas
    # Vendas = VGV Lançado * VSO
    vendas = [vgv_lancado[i] * vso[i] for i in range(5)]
    
    # Helper to get sales for previous years (Steady state proxy for historical sales to avoid year 1-2 depression)
    def get_venda(idx):
        if idx < 0:
            return vendas[0]  # Proxy for historical sales before Year 1
        return vendas[idx]
        
    # 2. Calcular Receita Reconhecida via POC
    # Receita_t = Vendas_t * POC_1 + Vendas_t-1 * POC_2 + Vendas_t-2 * POC_3
    receitas = []
    for i in range(5):
        receita_reconhecida = (
            get_venda(i) * poc['ano_1'] +
            get_venda(i - 1) * poc['ano_2'] +
            get_venda(i - 2) * poc['ano_3']
        )
        receitas.append(receita_reconhecida)
        
    # 3. Projetar EBIT e NOPAT
    ebit = [rec * margem_ebit for rec in receitas]
    nopat = [eb * (1.0 - tax_rate) for eb in ebit]
    
    # 4. Projetar D&A, CAPEX, e NWC
    depreciacao = [rec * depreciacao_percent for rec in receitas]
    capex = [rec * capex_percent for rec in receitas]
    nwc = [rec * nwc_percent for rec in receitas]
    
    # Variação de NWC (NWC_t - NWC_t-1)
    delta_nwc = []
    for i in range(5):
        if i == 0:
            # Steady state: assumes no NWC cash outflow from Year 0 to Year 1
            delta_nwc.append(0.0)
        else:
            delta_nwc.append(nwc[i] - nwc[i-1])
            
    # 5. Calcular o FCFF (Free Cash Flow to Firm)
    # FCFF = NOPAT + D&A - CAPEX - Delta NWC
    fcff = []
    for i in range(5):
        flow = nopat[i] + depreciacao[i] - capex[i] - delta_nwc[i]
        fcff.append(flow)
        
    return fcff

def calcular_dcf(fluxos: list, wacc: float, g: float, divida_liquida: float, num_acoes: int) -> dict:
    """
    Performs DCF valuation of the projected cash flows.
    """
    if wacc <= g:
        # Prevent division by zero or negative terminal value in Gordon Growth
        g = wacc - 0.01
        
    # Calculate present value (VP) of cash flows for years 1..5
    vp_fluxos = []
    for t, flow in enumerate(fluxos, start=1):
        vp = flow / ((1.0 + wacc) ** t)
        vp_fluxos.append(vp)
        
    # Gordon Growth Model for Terminal Value (TV) at Year 5
    fcff_terminal = fluxos[-1] * (1.0 + g)
    terminal_value = fcff_terminal / (wacc - g)
    
    # Discount Terminal Value to Year 0
    vp_terminal = terminal_value / ((1.0 + wacc) ** len(fluxos))
    
    # Enterprise Value (EV)
    enterprise_value = sum(vp_fluxos) + vp_terminal
    
    # Equity Value = EV - Net Debt
    equity_value = enterprise_value - divida_liquida
    
    # Fair Value per share
    valor_por_acao = equity_value / num_acoes
    
    return {
        "valor_por_acao": valor_por_acao,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "vp_fluxos": vp_fluxos,
        "vp_terminal": vp_terminal,
        "terminal_value": terminal_value
    }

def gerar_tabela_sensibilidade(wacc_range: list, g_range: list, premissas: dict) -> pd.DataFrame:
    """
    Generates a 2D sensitivity table of WACC vs. g and the resulting Fair Value per share.
    """
    fluxos = projetar_fluxos(premissas)
    divida_liquida = premissas['ativo']['divida_liquida']
    num_acoes = premissas['ativo']['num_acoes']
    
    grid = {}
    for g in g_range:
        col_name = f"g = {g:.1%}"
        grid[col_name] = []
        for wacc in wacc_range:
            dcf_res = calcular_dcf(fluxos, wacc, g, divida_liquida, num_acoes)
            grid[col_name].append(dcf_res['valor_por_acao'])
            
    row_names = [f"WACC = {wacc:.1%}" for wacc in wacc_range]
    df_sens = pd.DataFrame(grid, index=row_names)
    return df_sens
