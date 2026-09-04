import os
import json
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# Caminhos padrão
CDI_BACKUP_PATH = "data/cdi_diario_backup.csv"
IBOV_BACKUP_PATH = "data/ibov_composicao_mensal_backup.csv"
PRECOS_CACHE_PATH = "data/precos_cache.csv"

def carregar_cdi(data_inicio="01/01/2016", data_fim="31/12/2026"):
    """
    Busca o CDI diário da API do Banco Central (Série 12).
    Caso falhe (erro de rede ou HTTP 406/500), carrega do backup local.
    """
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={data_inicio}&dataFinal={data_fim}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        print("[Dados] Consultando API do Banco Central para o CDI...")
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)
            # Converter data string para datetime
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
            # Converter valor string para float (SGS retorna taxa percentual diária, ex: 0.0528)
            df["valor"] = df["valor"].astype(str).str.replace(",", ".").astype(float)
            # Converter de percentual para decimal (ex: 0.0528% -> 0.000528)
            df["valor"] = df["valor"] / 100.0
            
            df = df.sort_values("data").reset_index(drop=True)
            return df
        else:
            print(f"[Dados] API do BC retornou HTTP {res.status_code}. Usando backup local do CDI...")
    except Exception as e:
        print(f"[Dados] Erro ao consultar API do BC: {e}. Usando backup local do CDI...")
        
    # Carregar Backup
    if os.path.exists(CDI_BACKUP_PATH):
        df = pd.read_csv(CDI_BACKUP_PATH)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = df["valor"].astype(float)
        return df.sort_values("data").reset_index(drop=True)
    else:
        raise FileNotFoundError("API do Banco Central offline e arquivo de backup do CDI não encontrado!")

def carregar_composicao_ibov():
    """ Carrega o histórico de composição mensal do Ibovespa para evitar viés de sobrevivência. """
    if os.path.exists(IBOV_BACKUP_PATH):
        df = pd.read_csv(IBOV_BACKUP_PATH)
        df["data"] = pd.to_datetime(df["data"])
        return df.sort_values("data").reset_index(drop=True)
    else:
        raise FileNotFoundError("Base de composição do Ibovespa mensal não encontrada!")

def baixar_precos_ativos(tickers, start_date="2016-01-01", end_date="2026-12-31"):
    """
    Baixa as cotações históricas diárias (fechamento ajustado) dos ativos via yfinance.
    Utiliza um cache local em CSV para acelerar execuções futuras.
    """
    # Se o cache existe, carregar dele
    if os.path.exists(PRECOS_CACHE_PATH):
        print("[Dados] Carregando cotações históricas do cache local...")
        df_cache = pd.read_csv(PRECOS_CACHE_PATH, index_col=0, parse_dates=True)
        # Verificar se todos os tickers necessários estão no cache
        missing = [t for t in tickers if f"{t}.SA" not in df_cache.columns]
        if not missing:
            return df_cache
        else:
            print(f"[Dados] Cache incompleto. Baixando tickers faltantes via yfinance: {missing}...")
            
    # Baixar cotações via yfinance
    print(f"[Dados] Baixando cotações para {len(tickers)} ativos via Yahoo Finance...")
    tickers_sa = [f"{t}.SA" for t in tickers]
    
    try:
        # Baixar dados em lote
        data = yf.download(tickers_sa, start=start_date, end=end_date, group_by="column", progress=False)
        # Extrair apenas fechamento ajustado (Adj Close)
        if "Adj Close" in data.columns:
            precos = data["Adj Close"]
        elif "Close" in data.columns:
            precos = data["Close"]
        else:
            precos = data
            
        # Salvar no cache
        precos.to_csv(PRECOS_CACHE_PATH)
        print("[Dados] Cotações salvas no cache com sucesso.")
        return precos
    except Exception as e:
        print(f"[Dados] Erro ao baixar dados do Yahoo Finance: {e}")
        # Se houver erro, mas tivermos o cache antigo parcial, retorna o cache
        if os.path.exists(PRECOS_CACHE_PATH):
            return pd.read_csv(PRECOS_CACHE_PATH, index_col=0, parse_dates=True)
        raise e

def carregar_dados_completos(start_date="2016-01-01", end_date="2026-12-31"):
    """ Orquestrador principal de carga de dados. """
    # 1. Carregar composição mensal do Ibovespa
    comp = carregar_composicao_ibov()
    
    # 2. Levantar todos os tickers únicos históricos
    todos_tickers = set()
    for t_str in comp["tickers"]:
        for t in t_str.split():
            todos_tickers.add(t)
    todos_tickers = list(todos_tickers)
    
    # 3. Baixar/Carregar preços dos ativos
    precos = baixar_precos_ativos(todos_tickers, start_date, end_date)
    
    # 4. Carregar CDI
    # Converter datas para formato brasileiro (DD/MM/AAAA) para a API do BCB
    start_dt = pd.to_datetime(start_date).strftime("%d/%m/%Y")
    end_dt = pd.to_datetime(end_date).strftime("%d/%m/%Y")
    cdi = carregar_cdi(start_dt, end_dt)
    
    return {
        "precos": precos,
        "cdi": cdi,
        "composicao": comp
    }

if __name__ == "__main__":
    # Teste de execução rápida
    dados = carregar_dados_completos("2016-01-01", "2016-06-30")
    print("Preços carregados:", dados["precos"].shape)
    print("Linhas de CDI:", len(dados["cdi"]))
    print("Meses de Composição:", len(dados["composicao"]))
