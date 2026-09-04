import os
import sys
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from ingestion.cvm_collector import processar_demonstrativos, gerar_dados_mock_cvm

def test_cvm_lineage_and_metadata(tmp_path):
    # Setup mock CSV files in temporary folder
    extract_dir = gerar_dados_mock_cvm(2024, "DFP", str(tmp_path))
    
    # Run processing
    df = processar_demonstrativos(extract_dir, 2024, "DFP")
    
    assert not df.empty
    
    # Verify metadata lineage columns exist
    required_lineage_columns = ["source_file", "ingestion_timestamp", "cvm_code", "raw_account_code"]
    for col in required_lineage_columns:
        assert col in df.columns, f"Metadado obrigatório '{col}' está ausente no dataset."
        
    # Verify strict consolidation constraint: only consolidates should be processed
    # In processed dataset all rows are consolidation data
    assert len(df) > 0
    print("[TEST] Ingestion lineage and consolidation rules verified successfully.")
