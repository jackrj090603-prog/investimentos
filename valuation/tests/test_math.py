import pytest
import numpy as np
from src.wacc import desalavancar_beta, realavancar_beta, calcular_ke, calcular_wacc
from src.dcf import calcular_dcf, projetar_fluxos
from src.monte_carlo import calcular_estatisticas

# 1. Test un-leveraging beta (Hamada)
def test_desalavancar_beta():
    beta_l = 1.2
    de_ratio = 0.5
    tax_rate = 0.34
    expected_beta_u = 1.2 / (1.0 + (1.0 - 0.34) * 0.5)  # 1.2 / 1.33 = 0.90225
    assert desalavancar_beta(beta_l, de_ratio, tax_rate) == pytest.approx(expected_beta_u, rel=1e-5)

# 2. Test re-leveraging beta (Hamada un/relever cycle)
def test_realavancar_beta():
    beta_l = 1.2
    de_ratio = 0.25
    tax_rate = 0.04
    beta_u = desalavancar_beta(beta_l, de_ratio, tax_rate)
    beta_l_calc = realavancar_beta(beta_u, de_ratio, tax_rate)
    assert beta_l_calc == pytest.approx(beta_l, rel=1e-5)

# 3. Test CAPM (Ke) cost of equity
def test_calcular_ke():
    rf = 0.12
    beta = 1.1
    erp = 0.06
    # Ke = 0.12 + 1.1 * 0.06 = 0.186
    assert calcular_ke(rf, beta, erp) == pytest.approx(0.186, rel=1e-5)

# 4. Test WACC formula weights and calculation
def test_calcular_wacc():
    ke = 0.18
    kd = 0.12
    de_ratio = 0.25  # E = 0.8, D = 0.2
    tax_rate = 0.34  # Kd after tax = 0.12 * 0.66 = 0.0792
    # weight_equity = 1 / 1.25 = 0.8
    # weight_debt = 0.25 / 1.25 = 0.2
    # WACC = 0.18 * 0.8 + 0.0792 * 0.2 = 0.144 + 0.01584 = 0.15984
    assert calcular_wacc(ke, kd, de_ratio, tax_rate) == pytest.approx(0.15984, rel=1e-5)

# 5. Test DCF Present Value discounting
def test_calcular_dcf_valor_presente():
    fluxos = [100.0, 110.0, 120.0]
    wacc = 0.10
    g = 0.02
    divida_liquida = 0.0
    num_acoes = 1
    
    # VP of flows: 100/1.1 + 110/1.21 + 120/1.331
    expected_vp_flows = [
        100.0 / (1.1 ** 1),
        110.0 / (1.1 ** 2),
        120.0 / (1.1 ** 3)
    ]
    
    res = calcular_dcf(fluxos, wacc, g, divida_liquida, num_acoes)
    assert res['vp_fluxos'][0] == pytest.approx(expected_vp_flows[0], rel=1e-5)
    assert res['vp_fluxos'][1] == pytest.approx(expected_vp_flows[1], rel=1e-5)
    assert res['vp_fluxos'][2] == pytest.approx(expected_vp_flows[2], rel=1e-5)

# 6. Test Gordon perpetuity growth model for Terminal Value
def test_calcular_dcf_terminal_value():
    fluxos = [100.0, 110.0]
    wacc = 0.10
    g = 0.05
    divida_liquida = 0.0
    num_acoes = 1
    
    # TV at Year 2 = 110 * 1.05 / (0.10 - 0.05) = 115.5 / 0.05 = 2310
    # VP of TV = 2310 / 1.1**2 = 1909.0909
    res = calcular_dcf(fluxos, wacc, g, divida_liquida, num_acoes)
    assert res['terminal_value'] == pytest.approx(2310.0, rel=1e-5)
    assert res['vp_terminal'] == pytest.approx(1909.090909, rel=1e-5)

# 7. Test Enterprise Value to share price conversion
def test_calcular_dcf_valor_por_acao():
    fluxos = [100.0, 110.0]
    wacc = 0.10
    g = 0.05
    divida_liquida = 500.0
    num_acoes = 10
    
    res = calcular_dcf(fluxos, wacc, g, divida_liquida, num_acoes)
    # VP of flows = 100/1.1 + 110/1.21 = 90.90909 + 90.90909 = 181.81818
    # VP of TV = 1909.0909
    # EV = 181.81818 + 1909.0909 = 2090.90909
    # Equity = 2090.90909 - 500 = 1590.90909
    # Price per share = 159.0909
    assert res['enterprise_value'] == pytest.approx(2090.90909, rel=1e-5)
    assert res['equity_value'] == pytest.approx(1590.90909, rel=1e-5)
    assert res['valor_por_acao'] == pytest.approx(159.090909, rel=1e-5)

# 8. Test that flow projection length is exactly 5 years
def test_projetar_fluxos_shape():
    premissas_teste = {
        "wacc": {
            "aliquota_imposto": 0.04
        },
        "projecao": {
            "anos": 5,
            "depreciacao_percent": 0.02,
            "capex_percent": 0.015,
            "nwc_percent": 0.10,
            "vgv_lancado": [4e9, 4.3e9, 4.6e9, 4.9e9, 5.2e9],
            "vso": [0.60, 0.62, 0.63, 0.64, 0.65],
            "poc": {
                "ano_1": 0.20,
                "ano_2": 0.50,
                "ano_3": 0.30
            },
            "margem_ebit": 0.15
        }
    }
    fluxos = projetar_fluxos(premissas_teste)
    assert len(fluxos) == 5

# 9. Test Monte Carlo statistics calculation
def test_calcular_estatisticas_monte_carlo():
    precos = np.array([10.0, 12.0, 14.0, 16.0, 18.0, 20.0])
    cotacao = 15.0
    # Mean: 15.0, Median: 15.0
    # Values > 15: 16, 18, 20 (3 out of 6 -> 50%)
    stats = calcular_estatisticas(precos, cotacao)
    assert stats['media'] == 15.0
    assert stats['mediana'] == 15.0
    assert stats['prob_upside'] == 0.5
