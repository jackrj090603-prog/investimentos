import os
import sys
import pandas as pd

# Ensure path imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../agente_cvm")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../agente_cvm")))
sys.path.append(os.path.abspath("agente_cvm"))
sys.path.append(os.path.abspath("../agente_cvm"))

from google import genai
from google.genai import types
from config import GEMINI_API_KEY

def detectar_anomalias(kpis_df: pd.DataFrame) -> list:
    """Detects corporate financial anomalies in the KPIs database."""
    anomalias = []
    if kpis_df.empty:
        return anomalias
        
    for _, row in kpis_df.iterrows():
        ticker = row.get("denom_cia", "Desconhecido")
        
        # Check 1: Margin drops
        margin = row.get("margem_ebit", 0.0)
        if margin < 0:
            anomalias.append(f"{ticker}: Margem EBIT LTM negativa ({margin*100.0:.1f}%).")
            
        # Check 2: Leverage ratio too high
        leverage = row.get("alavancagem_ebit", 0.0)
        if leverage > 4.0:
            anomalias.append(f"{ticker}: Alavancagem financeira elevada (Dívida Líquida/EBIT = {leverage:.2f}x, limite de alerta = 4.0x).")
            
        # Check 3: Negative cash position
        cash = row.get("caixa", 0.0)
        if cash < 0:
            anomalias.append(f"{ticker}: Posição de caixa negativa detectada.")
            
    return anomalias

def gerar_relatorio_anomalias_ia(anomalias: list, kpis_df: pd.DataFrame) -> str:
    """Uses Gemini 2.0 to draft a summary anomaly alert report in Markdown."""
    if not GEMINI_API_KEY:
        print("[Research Assistant] GEMINI_API_KEY não configurada. Usando fallback offline.")
        return "### Alertas de Anomalias Financeiras (Fallback)\n\n" + "\n".join([f"- {a}" for a in anomalias])
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    anomalias_str = "\n".join([f"- {a}" for a in anomalias]) if anomalias else "Nenhuma anomalia crítica de balanço identificada."
    
    prompt = f"""
Você é um Analista de Riscos e Pesquisa de Investimentos Sênior na Ceará Finance.
Sua missão é redigir um boletim interno em Markdown resumindo os alertas de anomalias financeiras e a saúde corporativa das empresas analisadas na CVM.

Alertas de Anomalias Detectadas pelo Sistema:
{anomalias_str}

Resumo dos Indicadores:
{kpis_df[['denom_cia', 'receita_ltm', 'ebit_ltm', 'divida_liquida', 'margem_ebit', 'alavancagem_ebit']].to_markdown(index=False)}

Escreva um relatório estruturado em Markdown:
1. **Status Geral da Carteira** (Resumo de riscos e problemas detectados).
2. **Análise Detalhada dos Alertas** (Explicação de cada anomalia em termos de crédito e insolvência).
3. **Recomendações e Próximos Passos** (Ações sugeridas para o comitê de investimentos).
"""
    try:
        config = types.GenerateContentConfig(
            system_instruction="Você é o diretor de controle de riscos e auditoria da Ceará Finance.",
            temperature=0.3
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"[Research Assistant] Erro no Gemini: {e}")
        return "### Alertas de Anomalias Financeiras\n\n" + anomalias_str

def run_research_assistant(kpis_path="data/processed/kpis_calculados.parquet") -> str:
    """Runs the research assistant anomaly scanner."""
    if not os.path.exists(kpis_path):
        return "Dataset de KPIs não encontrado."
    df = pd.read_parquet(kpis_path)
    anomalias = detectar_anomalias(df)
    report = gerar_relatorio_anomalias_ia(anomalias, df)
    return report

if __name__ == '__main__':
    # Test assistant
    res = run_research_assistant()
    print(res)
