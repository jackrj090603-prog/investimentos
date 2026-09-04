import time
import signal
import sys
import threading
from config import HEARTBEAT_INTERVAL, MONITOR_INTERVAL
import storage
import monitor
import chat
import dashboard

# Sinalizador global para controle de encerramento das threads
running = True

def heartbeat_loop():
    """Imprime mensagens periódicas indicando o status operacional do Agente."""
    global running
    print("[Agente] Thread de Heartbeat iniciada.")
    while running:
        print("[Heartbeat] Agente operacional. Conexões CVM e Telegram verificadas.")
        # Dorme em pequenos blocos de 1s para responder rapidamente ao sinalizador de saída
        for _ in range(HEARTBEAT_INTERVAL):
            if not running:
                break
            time.sleep(1)

def monitor_loop():
    """Varre periodicamente a CVM em busca de novos documentos."""
    global running
    print("[Agente] Thread do Monitor CVM iniciada.")
    
    # Executa a busca inicial imediatamente na inicialização
    try:
        monitor.executar_monitoramento()
    except Exception as e:
        print(f"[Monitor] Falha no ciclo inicial de busca: {e}")
        
    while running:
        # Aguarda o intervalo dormindo de 1s em 1s
        for _ in range(MONITOR_INTERVAL):
            if not running:
                break
            time.sleep(1)
            
        if running:
            try:
                monitor.executar_monitoramento()
            except Exception as e:
                print(f"[Monitor] Erro na varredura periódica: {e}")

def chat_loop():
    """Escuta novas mensagens no bot do Telegram e responde continuamente."""
    global running
    print("[Agente] Thread do Assistente de Conversa iniciada.")
    while running:
        try:
            chat.responder_updates()
        except Exception as e:
            print(f"[Chat] Erro ao processar atualizações de chat: {e}")
            
        # Curta pausa de 2 segundos entre as leituras de mensagens
        time.sleep(2)

def handle_exit(signum, frame):
    """Manipulador de saída para encerrar as threads suavemente com Ctrl+C."""
    global running
    print("\n[Agente] Encerrando o serviço. Aguardando finalização das threads...")
    running = False
    sys.exit(0)

def main():
    global running
    print("=====================================================================")
    print("      CEARÁ FINANCE - AGENTE DE MONITORAMENTO CVM v1.0               ")
    print("=====================================================================\n")
    
    # Registrar sinal de saída Ctrl+C
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # 1. Inicializar banco de dados SQLite
    print("[Agente] Inicializando banco de dados local...")
    storage.init_db()
    
    # 2. Iniciar Dashboard HTTP na porta 8000
    print("[Agente] Iniciando Dashboard local...")
    dashboard.rodar_dashboard_async(port=8000)
    
    # 3. Criar e iniciar as threads
    t_heartbeat = threading.Thread(target=heartbeat_loop, daemon=True)
    t_monitor = threading.Thread(target=monitor_loop, daemon=True)
    t_chat = threading.Thread(target=chat_loop, daemon=True)
    
    t_heartbeat.start()
    t_monitor.start()
    t_chat.start()
    
    # Manter a thread principal ativa
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_exit(None, None)

if __name__ == "__main__":
    main()
