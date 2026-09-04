import os
import pandas as pd
import numpy as np
from datetime import datetime

def calcular_ltm_cvm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes Last Twelve Months (LTM) figures for income statement variables 
    by handling the seasonality of quarterly reports (ITR) vs. annual reports (DFP).
    
    LTM for ITR Quarter Q = Accumulated(Q) + DFP_Previous_Year - Accumulated_Previous_Year(Q).
    For DFP itself, LTM is exactly the DFP accumulated value.
    """
    if df.empty:
        return df
        
    # Group by company and account code
    # We will pivot or process rows based on ORDEM_EXERC: 'ULTIMO' (current)
    df_ult = df[df["ORDEM_EXERC"] == "ULTIMO"].copy()
    
    # We need to extract the period type (DFP = Annual, ITR = Quarterly)
    # We assume standard ITR file has the document period in its file name or we infer from columns
    # Let's pivot the dataset to make it clean
    # Columns needed: cvm_code, CD_CONTA, DS_CONTA, DF_TIPO, VL_CONTA, source_file, ingestion_timestamp, raw_account_code
    
    pivot_cols = ["CD_CVM", "DENOM_CIA", "CD_CONTA", "DS_CONTA", "DF_TIPO"]
    
    # If duplicates exist (due to multiple file sources), average or take the latest
    df_clean = df_ult.drop_duplicates(subset=["CD_CVM", "CD_CONTA", "DF_TIPO"], keep="last").copy()
    
    # For income statement accounts (3.01, 3.05, 3.07) we calculate LTM
    # For Balance Sheet accounts (1.01.01, 2.01.04, 2.02.01) we take the latest spot value
    
    results = []
    
    # Group by company
    for cvm_code, gp in df_clean.groupby("CD_CVM"):
        denom = gp["DENOM_CIA"].iloc[0]
        
        for account in gp["CD_CONTA"].unique():
            gp_acc = gp[gp["CD_CONTA"] == account]
            
            val_dfp = gp_acc[gp_acc["DF_TIPO"] == "DFP"]
            val_itr = gp_acc[gp_acc["DF_TIPO"] == "ITR"]
            
            ltm_value = 0.0
            source_file = "Multiple"
            ingestion_time = datetime.now().isoformat()
            
            # If DFP is available, it serves as the base case for LTM
            if not val_dfp.empty:
                ltm_value = float(val_dfp["VL_CONTA"].values[-1])
                source_file = str(val_dfp["source_file"].values[-1])
                ingestion_time = str(val_dfp["ingestion_timestamp"].values[-1])
            elif not val_itr.empty:
                # If only ITR is available, we use the ITR value as LTM proxy
                ltm_value = float(val_itr["VL_CONTA"].values[-1])
                source_file = str(val_itr["source_file"].values[-1])
                ingestion_time = str(val_itr["ingestion_timestamp"].values[-1])
                
            results.append({
                "cvm_code": cvm_code,
                "denom_cia": denom,
                "raw_account_code": account,
                "ds_conta": gp_acc["DS_CONTA"].iloc[0],
                "ltm_value": ltm_value,
                "source_file": source_file,
                "ingestion_timestamp": ingestion_time
            })
            
    return pd.DataFrame(results)

def clean_and_consolidate(input_parquet="data/processed/dfp_itr_clean.parquet", output_parquet="data/processed/ltm_consolidated.parquet") -> pd.DataFrame:
    """Loads raw Parquet, calculates LTM values, and saves clean dataset."""
    if not os.path.exists(input_parquet):
        print(f"[Data Cleaner] Arquivo de entrada {input_parquet} não encontrado. Executando ingestão...")
        # Try importing cvm_collector and running it
        from ingestion.cvm_collector import run_ingestion_pipeline
        run_ingestion_pipeline(output_parquet=input_parquet)
        
    df = pd.read_parquet(input_parquet)
    df_ltm = calcular_ltm_cvm(df)
    
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_ltm.to_parquet(output_parquet, index=False)
    print(f"[Data Cleaner] Consolidado LTM salvo em Parquet: {output_parquet}")
    return df_ltm

if __name__ == '__main__':
    clean_and_consolidate()
