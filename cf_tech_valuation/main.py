import os
import sys
import argparse
import json

# Ensure internal modules import correctly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.ingestion.cvm_collector import run_ingestion_pipeline
from src.processing.data_cleaner import clean_and_consolidate
from src.processing.indicator_engine import calcular_indicadores_financeiros
from src.valuation.wacc_calculator import calcular_wacc_completo
from src.valuation.dcf_model import calcular_dcf_fair_value
from src.valuation.monte_carlo import rodar_simulacao_precos
from src.ai_agent.research_assistant import run_research_assistant

def main():
    parser = argparse.ArgumentParser(description="CF TECH - Valuation & Equity Research Pipeline")
    parser.add_argument("--stage", type=str, required=True, 
                        choices=["ingest", "clean", "kpi", "wacc", "dcf", "mc", "risk", "all"],
                        help="Estágio da pipeline para rodar.")
    parser.add_argument("--ticker", type=str, default="DIRR3", 
                        help="Ticker do ativo B3 para valuation (Ex: DIRR3, PETR4).")
    parser.add_argument("--preco-atual", type=float, default=11.50, 
                        help="Preço atual de mercado para calcular upside em simulações.")
                        
    args = parser.parse_args()
    
    ticker = args.ticker.upper().strip()
    stage = args.stage
    preco_atual = args.preco_atual
    
    print("=" * 60)
    print(f"         CF TECH AUTOMATION - RUNNING STAGE: {stage.upper()}")
    print("=" * 60)
    
    if stage == "ingest" or stage == "all":
        print("[Pipeline] Iniciando Ingestão CVM...")
        run_ingestion_pipeline(years=[2023, 2024])
        
    if stage == "clean" or stage == "all":
        print("[Pipeline] Iniciando Limpeza e Consolidação LTM...")
        clean_and_consolidate()
        
    if stage == "kpi" or stage == "all":
        print("[Pipeline] Calculando KPIs Financeiros...")
        calcular_indicadores_financeiros()
        
    wacc_res = None
    if stage == "wacc" or stage == "all":
        print(f"[Pipeline] Calculando WACC para {ticker}...")
        wacc_res = calcular_wacc_completo(ticker)
        print(json.dumps({k: v for k, v in wacc_res.items() if k != "premissas_utilizadas"}, indent=2))
        
    dcf_res = None
    if stage == "dcf" or stage == "all":
        print(f"[Pipeline] Rodando DCF para {ticker}...")
        # Get WACC value
        if wacc_res is None:
            wacc_res = calcular_wacc_completo(ticker)
        wacc_val = wacc_res["wacc_nominal"]
        
        dcf_res = calcular_dcf_fair_value(ticker, wacc_val)
        # Format list outputs for printing
        print_res = {k: v for k, v in dcf_res.items() if k not in ["fluxos_projetados", "vp_fluxos"]}
        print(json.dumps(print_res, indent=2))
        
    if stage == "mc" or stage == "all":
        print(f"[Pipeline] Rodando Simulação Monte Carlo para {ticker}...")
        if wacc_res is None:
            wacc_res = calcular_wacc_completo(ticker)
        if dcf_res is None:
            dcf_res = calcular_dcf_fair_value(ticker, wacc_res["wacc_nominal"])
            
        mc_res = rodar_simulacao_precos(ticker, wacc_res["wacc_nominal"], dcf_res["preco_justo"], preco_atual)
        print_res = {k: v for k, v in mc_res.items() if k != "precos_simulados"}
        print(json.dumps(print_res, indent=2))
        
    if stage == "risk" or stage == "all":
        print("[Pipeline] Gerando Alertas de Risco via Research Assistant...")
        report = run_research_assistant()
        print(report)
        
    print("[Pipeline] Execução concluída com sucesso!")

if __name__ == '__main__':
    main()
