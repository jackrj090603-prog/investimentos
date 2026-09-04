import re
import subprocess

PORTS = [8000, 8001, 8002, 8003, 8004, 8005, 8501]

def liberar_portas():
    print("==================================================")
    print("   LIBERANDO PORTAS DO ECOSSISTEMA CEARÁ FINANCE  ")
    print("==================================================")
    
    pids_to_kill = set()
    try:
        output = subprocess.check_output("netstat -ano", shell=True, text=True, errors="ignore")
        for line in output.splitlines():
            for port in PORTS:
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit() and int(pid) > 0:
                            pids_to_kill.add(pid)
                            print(f"[Porta {port}] Ocupada pelo Processo PID {pid}")
    except Exception as e:
        print(f"Erro ao verificar netstat: {e}")

    for pid in pids_to_kill:
        try:
            print(f"Finalizando processo PID {pid}...")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        except Exception as e:
            print(f"Erro ao matar PID {pid}: {e}")

    print("\nTodas as portas foram liberadas com sucesso!\n")

if __name__ == "__main__":
    liberar_portas()
