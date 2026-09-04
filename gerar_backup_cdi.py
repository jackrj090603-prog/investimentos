import os
import pandas as pd
import numpy as np

def gerar_backup_cdi():
    print("[Backup CDI] Gerando base histórica de CDI...")
    os.makedirs("data", exist_ok=True)
    
    # Gerar datas diárias de 2016 a 2026 (dias úteis)
    dates = pd.date_range(start="2016-01-01", end="2026-12-31", freq="B")
    
    # Criar uma taxa Selic/CDI diária simulada realística com base nas taxas históricas brasileiras
    # 2016: ~14%, 2018: ~6.5%, 2020: ~2.0%, 2022: ~13.75%, 2024: ~10.5%, 2026: ~10.0%
    cdi_diario = []
    for d in dates:
        y = d.year
        if y == 2016:
            taxa_anual = 0.14
        elif y == 2017:
            taxa_anual = 0.10
        elif y == 2018:
            taxa_anual = 0.065
        elif y == 2019:
            taxa_anual = 0.06
        elif y == 2020:
            taxa_anual = 0.0275
        elif y == 2021:
            taxa_anual = 0.045
        elif y == 2022:
            taxa_anual = 0.125
        elif y == 2023:
            taxa_anual = 0.13
        elif y == 2024:
            taxa_anual = 0.1075
        elif y == 2025:
            taxa_anual = 0.105
        else:
            taxa_anual = 0.10
            
        # Converter taxa anual para diária base 252: (1 + taxa_anual) ^ (1/252) - 1
        taxa_diaria = (1.0 + taxa_anual) ** (1.0 / 252.0) - 1.0
        cdi_diario.append(taxa_diaria)
        
    df = pd.DataFrame({
        "data": dates.strftime("%d/%m/%Y"),
        "valor": cdi_diario
    })
    
    csv_path = "data/cdi_diario_backup.csv"
    df.to_csv(csv_path, index=False)
    print(f"[Backup CDI] Base de CDI salva em: {csv_path} ({len(df)} registros)")

if __name__ == "__main__":
    gerar_backup_cdi()
