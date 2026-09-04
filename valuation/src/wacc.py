import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings

def calcular_beta(ticker: str, index_ticker: str, period: str = '2y') -> float:
    """
    Downloads ~2 years of daily data for the stock and market index,
    aligns them, and estimates the Beta coefficient using linear regression (OLS).
    """
    try:
        print(f"Baixando dados históricos para cálculo do Beta: {ticker} e {index_ticker}...")
        # Download both tickers in a single call to be faster and more reliable
        df = yf.download([ticker, index_ticker], period=period, progress=False)
        
        if df.empty:
            raise ValueError("O Yahoo Finance retornou um DataFrame vazio (sem conexão ou tickers inválidos).")
            
        # Select adjusted close or close
        price_col = 'Adj Close' if 'Adj Close' in df.columns.levels[0] else 'Close'
        df_prices = df[price_col]
        
        # Verify both tickers are in columns and have data
        if ticker not in df_prices.columns or index_ticker not in df_prices.columns:
            raise ValueError(f"Não foi possível encontrar dados para {ticker} ou {index_ticker} nas colunas.")
            
        # Drop NaNs to align dates
        df_aligned = df_prices[[ticker, index_ticker]].dropna()
        if df_aligned.empty:
            raise ValueError("Nenhum dado alinhado disponível entre o ativo e o índice.")
            
        # Calculate daily returns
        df_returns = df_aligned.pct_change().dropna()
        if len(df_returns) < 10:
            raise ValueError("Dados históricos insuficientes para calcular regressão.")
            
        # OLS regression: R_stock = alpha + beta * R_index
        y = df_returns[ticker]
        X = sm.add_constant(df_returns[index_ticker])
        model = sm.OLS(y, X).fit()
        
        beta = model.params[index_ticker]
        print(f"Beta calculado com sucesso via OLS: {beta:.4f}")
        return float(beta)
        
    except Exception as e:
        warnings.warn(f"Erro ao calcular Beta de mercado para {ticker}: {e}. Retornando fallback Beta = 1.0")
        return 1.0

def desalavancar_beta(beta_alavancado: float, de_ratio: float, tax_rate: float) -> float:
    """
    Unlevers the Beta using Hamada's formula: Beta_U = Beta_L / [1 + (1 - T) * (D/E)]
    """
    return beta_alavancado / (1.0 + (1.0 - tax_rate) * de_ratio)

def realavancar_beta(beta_desalavancado: float, de_ratio: float, tax_rate: float) -> float:
    """
    Relevers the Beta using Hamada's formula: Beta_L = Beta_U * [1 + (1 - T) * (D/E)]
    """
    return beta_desalavancado * (1.0 + (1.0 - tax_rate) * de_ratio)

def calcular_ke(rf: float, beta: float, erp: float) -> float:
    """
    Calculates cost of equity (Ke) using CAPM: Ke = Rf + Beta * ERP
    """
    return rf + beta * erp

def calcular_wacc(ke: float, kd: float, de_ratio: float, tax_rate: float) -> float:
    """
    Calculates Weighted Average Cost of Capital (WACC):
    WACC = Ke * (E / (D+E)) + Kd * (1 - T) * (D / (D+E))
    where:
      E / (D+E) = 1 / (1 + D/E)
      D / (D+E) = (D/E) / (1 + D/E)
    """
    weight_equity = 1.0 / (1.0 + de_ratio)
    weight_debt = de_ratio / (1.0 + de_ratio)
    
    kd_after_tax = kd * (1.0 - tax_rate)
    
    wacc = ke * weight_equity + kd_after_tax * weight_debt
    return wacc
