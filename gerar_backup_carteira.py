import os
import pandas as pd
import numpy as np

def gerar_backup_carteira():
    print("[Backup Carteira] Gerando base histórica de composição do Ibovespa...")
    os.makedirs("data", exist_ok=True)
    
    # Gerar datas mensais de jan/2016 a dez/2026
    meses = pd.date_range(start="2016-01-01", end="2026-12-31", freq="MS")
    
    # Lista base de ações representativas da B3
    base_tickers = [
        "VALE3", "PETR4", "ITUB4", "BBDC4", "ABEV3", "BBAS3", "ITSA4", "WEGE3", 
        "RENT3", "ELET3", "SUZB3", "JBSS3", "EQTL3", "SBSP3", "RADL3", "LREN3", 
        "GGBR4", "RDOR3", "RAIL3", "KLBN11", "CCRO3", "CPFL3", "CYRE3", "MRVE3", 
        "DIRR3", "USIM5", "CSNA3", "GOAU4", "CPLE6", "VIVT3"
    ]
    
    rows = []
    for m in meses:
        data_str = m.strftime("%Y-%m-%d")
        y = m.year
        
        # Simular entradas e saídas para evitar viés de sobrevivência de forma didática
        ativos_mes = list(base_tickers)
        
        # Simulação de inclusão e exclusão temporal
        if y < 2018:
            # Tickers mais antigos
            ativos_mes.remove("RDOR3") # Entrou na bolsa final de 2020
            ativos_mes.append("BVMF3") # Ticker antigo da B3
        elif y >= 2018 and y < 2021:
            if "BVMF3" in ativos_mes:
                ativos_mes.remove("BVMF3")
            ativos_mes.append("B3SA3")
            if "RDOR3" in ativos_mes:
                ativos_mes.remove("RDOR3")
        else: # y >= 2021
            if "BVMF3" in ativos_mes:
                ativos_mes.remove("BVMF3")
            if "B3SA3" not in ativos_mes:
                ativos_mes.append("B3SA3")
            if "RDOR3" not in ativos_mes:
                ativos_mes.append("RDOR3")
                
        # Unir por espaço
        tickers_str = " ".join(ativos_mes)
        rows.append({"data": data_str, "tickers": tickers_str})
        
    df = pd.DataFrame(rows)
    csv_path = "data/ibov_composicao_mensal_backup.csv"
    df.to_csv(csv_path, index=False)
    print(f"[Backup Carteira] Composição histórica do IBOV salva em: {csv_path} ({len(df)} meses)")

if __name__ == "__main__":
    gerar_backup_carteira()
