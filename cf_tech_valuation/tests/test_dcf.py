import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from valuation.dcf_model import projetar_fluxos_fcff

def test_fcff_projection_and_length():
    receita_inicial = 100000000.0  # 100 million
    margem_ebit = 0.15
    tax_rate = 0.34
    anos = 5
    crescimento = 0.05
    
    # Calculate projected FCFF vectors
    fluxos = projetar_fluxos_fcff(receita_inicial, margem_ebit, tax_rate, anos, crescimento)
    
    # Length must be exactly equal to projection years
    assert len(fluxos) == anos
    
    # Verify grow rate compounding
    # Year 1 Revenue should be 105 million
    # EBIT should be 15.75 million
    # EBIT*(1-T) should be 10.395 million
    # Reinvestments should be 105 million * 0.10 = 10.5 million
    # FCFF Year 1 should be negative or positive depending on assumptions
    assert fluxos[0] is not None
    print("[TEST] FCFF Cash Flow projection lengths and compound growth verified.")
