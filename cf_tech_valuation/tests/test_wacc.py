import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from valuation.wacc_calculator import desalavancar_beta_hamada, realavancar_beta_hamada, carregar_premissas_wacc

def test_beta_hamada_cycle():
    # Setup test variables using dy differential derivatives concepts
    beta_l = 1.35
    de_ratio = 0.15
    tax_rate = 0.34
    
    # 1. Unlever Beta
    beta_u = desalavancar_beta_hamada(beta_l, de_ratio, tax_rate)
    
    # 2. Relever Beta
    beta_relevered = realavancar_beta_hamada(beta_u, de_ratio, tax_rate)
    
    # Verify cycle returns the initial value (numerical precision allowance)
    assert abs(beta_relevered - beta_l) < 1e-7
    print("[TEST] Hamada Beta unlever/relever cycle is mathematically verified.")
    
def test_premissas_wacc_configuration():
    premissas = carregar_premissas_wacc("config/settings.yaml")
    assert "taxa_livre_risco" in premissas
    assert "premio_risco_mercado" in premissas
    assert "aliquota_imposto" in premissas
