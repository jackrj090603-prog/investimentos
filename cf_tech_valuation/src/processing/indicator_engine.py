import os
import pandas as pd
import numpy as np

def calcular_indicadores_financeiros(input_parquet="data/processed/ltm_consolidated.parquet", output_parquet="data/processed/kpis_calculados.parquet") -> pd.DataFrame:
    """
    Computes key financial performance indicators (KPIs) from LTM values.
    
    KPIs calculated:
    - EBIT Margin
    - Net Margin
    - Total Debt
    - Net Debt
    - Net Debt / EBIT (leverage ratio)
    """
    if not os.path.exists(input_parquet):
        print(f"[Indicator Engine] Arquivo {input_parquet} não encontrado. Iniciando limpeza...")
        from processing.data_cleaner import clean_and_consolidate
        df_ltm = clean_and_consolidate(output_parquet=input_parquet)
    else:
        df_ltm = pd.read_parquet(input_parquet)
        
    if df_ltm.empty:
        print("[Indicator Engine] Dataset consolidado vazio.")
        return pd.DataFrame()
        
    # Pivot accounts to columns: cvm_code, denom_cia, source_file, ingestion_timestamp
    # CD_CONTA values: 3.01, 3.05, 3.07, 1.01.01, 2.01.04, 2.02.01
    
    rows = []
    for cvm_code, gp in df_ltm.groupby("cvm_code"):
        denom = gp["denom_cia"].iloc[0]
        
        # Get specific account values
        def get_val(code):
            val_row = gp[gp["raw_account_code"] == code]
            return float(val_row["ltm_value"].values[0]) if not val_row.empty else 0.0
            
        receita = get_val("3.01")
        ebit = get_val("3.05")
        lucro = get_val("3.07")
        caixa = get_val("1.01.01")
        div_cp = get_val("2.01.04")
        div_lp = get_val("2.02.01")
        
        # Calculations
        margem_ebit = ebit / receita if receita > 0 else 0.0
        margem_liquida = lucro / receita if receita > 0 else 0.0
        divida_total = div_cp + div_lp
        divida_liquida = divida_total - caixa
        alavancagem = divida_liquida / ebit if ebit > 0 else 0.0
        
        # Lineage metadata
        source_file = gp["source_file"].iloc[0] if "source_file" in gp.columns else "Cleaned"
        ing_time = gp["ingestion_timestamp"].iloc[0] if "ingestion_timestamp" in gp.columns else "Cleaned"
        
        rows.append({
            "cvm_code": cvm_code,
            "denom_cia": denom,
            "receita_ltm": receita,
            "ebit_ltm": ebit,
            "lucro_ltm": lucro,
            "caixa": caixa,
            "divida_cp": div_cp,
            "divida_lp": div_lp,
            "divida_total": divida_total,
            "divida_liquida": divida_liquida,
            "margem_ebit": margem_ebit,
            "margem_liquida": margem_liquida,
            "alavancagem_ebit": alavancagem,
            "source_file": source_file,
            "ingestion_timestamp": ing_time
        })
        
    result_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    result_df.to_parquet(output_parquet, index=False)
    print(f"[Indicator Engine] KPIs calculados com sucesso: {output_parquet}")
    return result_df

if __name__ == '__main__':
    calcular_indicadores_financeiros()
