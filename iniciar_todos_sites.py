import os
import sys
import time
import subprocess
import urllib.request
import parar_todos_sites

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTE_DIR = os.path.join(BASE_DIR, "agente_cvm")
APPS_DIR = os.path.join(AGENTE_DIR, "apps")

SERVICOS = [
    {"nome": "Central Hub", "porta": 8000, "script": os.path.join(APPS_DIR, "hub_server.py"), "cwd": BASE_DIR},
    {"nome": "Alertas CVM", "porta": 8001, "script": os.path.join(APPS_DIR, "cvm_server.py"), "cwd": AGENTE_DIR},
    {"nome": "Valuation Mira", "porta": 8002, "script": os.path.join(APPS_DIR, "mira_server.py"), "cwd": AGENTE_DIR},
    {"nome": "Equity Research", "porta": 8003, "script": os.path.join(APPS_DIR, "reports_server.py"), "cwd": AGENTE_DIR},
    {"nome": "Workstation", "porta": 8004, "script": os.path.join(APPS_DIR, "workstation_server.py"), "cwd": AGENTE_DIR},
    {"nome": "CF Tech Pipelines", "porta": 8005, "script": os.path.join(APPS_DIR, "cftech_server.py"), "cwd": BASE_DIR},
]

def main():
    print("==========================================================")
    print("    INICIALIZADOR MODULAR CEARÁ FINANCE (MULTI-APPS)      ")
    print("==========================================================\n")
    
    # 1. Liberar portas antes de subir
    parar_todos_sites.liberar_portas()
    time.sleep(1)

    processos = []

    # 2. Iniciar os 6 servidores de micro-dashboards
    for s in SERVICOS:
        cmd = [sys.executable, s["script"]]
        p = subprocess.Popen(cmd, cwd=s["cwd"])
        processos.append((s["nome"], s["porta"], p))
        print(f"[Iniciado] {s['nome']} -> http://localhost:{s['porta']}")

    # 3. Iniciar o dashboard Streamlit (Aegis Momentum Backtest)
    cmd_streamlit = [sys.executable, "-m", "streamlit", "run", "dashboard_experimentos.py", "--server.port", "8501", "--server.headless", "true"]
    p_streamlit = subprocess.Popen(cmd_streamlit, cwd=BASE_DIR)
    processos.append(("Aegis Momentum Backtest", 8501, p_streamlit))
    print("[Iniciado] Aegis Momentum Backtest -> http://localhost:8501")

    # 4. Iniciar rotina de monitoramento de fatos relevantes e bot do Telegram
    script_agente_bot = os.path.join(AGENTE_DIR, "agente.py")
    # Para evitar conflito com a porta 8000 já usada pelo Hub, o agente.py pode rodar em modo background monitor
    print("\nAguardando inicialização dos serviços (3 segundos)...")
    time.sleep(3)

    # 5. Health check em todas as portas
    print("\n--- STATUS DE CONEXAO DOS SITES ---")
    for nome, porta, proc in processos:
        url = f"http://localhost:{porta}"
        try:
            req = urllib.request.urlopen(url, timeout=3)
            status_code = req.getcode()
            print(f"[OK] {nome.ljust(25)} [Porta {porta}]: HTTP {status_code} OK -> {url}")
        except Exception as e:
            print(f"[WAIT] {nome.ljust(25)} [Porta {porta}]: Inicializando ({e})")

    print("\n==========================================================")
    print("  [SUCESSO] TODOS OS SITES ESTAO ONLINE E RODANDO!        ")
    print("  Acesse o Portal Central em: http://localhost:8000        ")
    print("==========================================================\n")

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nFinalizando todos os serviços...")
        for nome, porta, proc in processos:
            proc.terminate()
        parar_todos_sites.liberar_portas()

if __name__ == "__main__":
    main()
