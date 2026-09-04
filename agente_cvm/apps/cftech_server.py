import os
import sys
import json
import yaml
import subprocess
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

PORT = 8005

RUNNING_PROCESS = None
LAST_LOGS = []

def obter_caminho_config():
    paths = [
        os.path.join(PROJECT_DIR, "cf_tech_valuation", "config", "settings.yaml"),
        os.path.join(PROJECT_DIR, "config", "settings.yaml"),
        os.path.join(BASE_DIR, "..", "cf_tech_valuation", "config", "settings.yaml")
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]

def obter_caminho_parquet():
    paths = [
        os.path.join(PROJECT_DIR, "data", "processed", "kpis_calculados.parquet"),
        os.path.join(PROJECT_DIR, "cf_tech_valuation", "data", "processed", "kpis_calculados.parquet")
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]

class CFTechHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.render_cftech_ui().encode("utf-8"))
            
        elif parsed.path == "/LOGO_CF.png":
            self.serve_logo()
            
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "app": "cftech"}')
            
        elif parsed.path == "/api/cf_tech/config":
            config_path = obter_caminho_config()
            if not os.path.exists(config_path):
                data = {
                    "wacc": {"risk_free_rate": 0.105, "market_risk_premium": 0.055, "tax_rate": 0.34},
                    "dcf": {"projection_years": 5, "perpetual_growth_rate": 0.045},
                    "monte_carlo": {"iterations": 10000}
                }
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            
        elif parsed.path == "/api/cf_tech/kpis":
            kpis = self.carregar_kpis_parquet()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(kpis).encode("utf-8"))
            
        elif parsed.path == "/api/cf_tech/status":
            global RUNNING_PROCESS, LAST_LOGS
            is_running = RUNNING_PROCESS is not None and RUNNING_PROCESS.poll() is None
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"running": is_running, "logs": LAST_LOGS[-40:]}).encode("utf-8"))
            
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        if parsed.path == "/api/cf_tech/config":
            try:
                new_cfg = json.loads(body)
                config_path = obter_caminho_config()
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(new_cfg, f, default_flow_style=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "settings.yaml atualizado com sucesso!"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                
        elif parsed.path == "/api/cf_tech/run":
            global RUNNING_PROCESS, LAST_LOGS
            try:
                payload = json.loads(body)
                stage = payload.get("stage", "all")
                ticker = payload.get("ticker", "DIRR3")
                
                main_script = os.path.join(PROJECT_DIR, "cf_tech_valuation", "main.py")
                cmd = [sys.executable, main_script, "--stage", stage, "--ticker", ticker]
                
                LAST_LOGS = [f"[Sistema] Iniciando pipeline: stage={stage}, ticker={ticker}...\n"]
                RUNNING_PROCESS = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                import threading
                def read_proc():
                    global LAST_LOGS
                    for line in RUNNING_PROCESS.stdout:
                        LAST_LOGS.append(line)
                        if len(LAST_LOGS) > 300:
                            LAST_LOGS = LAST_LOGS[-200:]
                threading.Thread(target=read_proc, daemon=True).start()
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "started", "ticker": ticker, "stage": stage}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                
        else:
            self.send_response(404)
            self.end_headers()

    def carregar_kpis_parquet(self):
        p_path = obter_caminho_parquet()
        if not os.path.exists(p_path):
            return []
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(p_path)
            return table.to_pylist()
        except:
            return []

    def serve_logo(self):
        paths_to_try = [
            os.path.join(PROJECT_DIR, "Mira", "LOGO_CF.png"),
            os.path.join(PROJECT_DIR, "LOGO_CF.png"),
            os.path.join(AGENTE_DIR, "LOGO_CF.png")
        ]
        for p in paths_to_try:
            if os.path.exists(p):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(p, "rb") as f:
                    self.wfile.write(f.read())
                return
        self.send_response(404)
        self.end_headers()

    def render_cftech_ui(self):
        html = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CF Tech Pipelines — Ceará Finance</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-dark: #07080c;
            --bg-card: #0d0f17;
            --border-color: rgba(255, 255, 255, 0.08);
            --accent: #ec4899;
            --text-main: #ffffff;
            --text-muted: #8e9bb0;
            --font-mono: 'JetBrains Mono', monospace;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 20px 25px;
            min-height: 100vh;
        }
        .container {
            max-width: 1300px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 18px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 25px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .brand img {
            height: 46px;
            object-fit: contain;
        }
        .brand-title h1 {
            font-size: 20px;
            font-weight: 800;
        }
        .brand-title p {
            font-size: 12px;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 700;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .btn-action {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            color: #ffffff;
            padding: 8px 14px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-action:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .grid-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 22px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }
        .card-header h2 {
            font-size: 17px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .form-group {
            margin-bottom: 14px;
        }
        .form-group label {
            display: block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 6px;
            font-weight: 600;
        }
        .form-group input, .form-group select {
            width: 100%;
            background: #121520;
            border: 1px solid var(--border-color);
            padding: 10px 12px;
            border-radius: 8px;
            color: #ffffff;
            font-size: 13px;
            font-family: var(--font-mono);
            outline: none;
        }
        .form-group input:focus, .form-group select:focus {
            border-color: var(--accent);
        }
        .btn-run {
            background: linear-gradient(135deg, #ec4899 0%, #be185d 100%);
            border: none;
            color: #ffffff;
            font-weight: 700;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-size: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            transition: opacity 0.2s;
        }
        .btn-run:hover {
            opacity: 0.9;
        }
        .console-box {
            background: #050608;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            font-family: var(--font-mono);
            font-size: 12px;
            height: 280px;
            overflow-y: auto;
            color: #38bdf8;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .table-wrap {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th {
            background: #121520;
            padding: 12px 14px;
            font-weight: 700;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            text-align: right;
            font-family: var(--font-mono);
        }
        th:first-child {
            text-align: left;
            font-family: 'Outfit', sans-serif;
        }
        td {
            padding: 10px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            text-align: right;
            font-family: var(--font-mono);
        }
        td:first-child {
            text-align: left;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            color: #38bdf8;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <img src="/LOGO_CF.png" alt="Ceará Finance" onerror="this.style.display='none'">
                <div class="brand-title">
                    <h1>CF Tech Pipelines</h1>
                    <p>WACC, DCF, Monte Carlo & Parquet Database</p>
                </div>
            </div>
            <div class="header-actions">
                <a href="http://localhost:8000" class="btn-action"><i class="fas fa-arrow-left"></i> Hub Central</a>
                <button onclick="salvarConfig()" class="btn-action" style="color:#46e0a0;"><i class="fas fa-floppy-disk"></i> Salvar Premissas</button>
            </div>
        </header>

        <div class="grid-layout">
            <div class="card">
                <div class="card-header">
                    <h2><i class="fas fa-sliders" style="color:var(--accent);"></i> Premissas de Valuation (settings.yaml)</h2>
                    <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">Rastreabilidade Total</span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div class="form-group">
                        <label>Risk-Free Rate (Rf)</label>
                        <input type="number" id="cfg-rf" step="0.005">
                    </div>
                    <div class="form-group">
                        <label>Market Risk Premium (MRP)</label>
                        <input type="number" id="cfg-mrp" step="0.005">
                    </div>
                    <div class="form-group">
                        <label>Alíquota IR / CSLL</label>
                        <input type="number" id="cfg-tax" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Crescimento Perpétuo (g)</label>
                        <input type="number" id="cfg-g" step="0.005">
                    </div>
                    <div class="form-group">
                        <label>Anos Projeção DCF</label>
                        <input type="number" id="cfg-years" step="1">
                    </div>
                    <div class="form-group">
                        <label>Iterações Monte Carlo</label>
                        <input type="number" id="cfg-iter" step="1000">
                    </div>
                </div>

                <div style="border-top:1px solid var(--border-color); padding-top:16px; margin-top:10px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                        <div class="form-group">
                            <label>Ativo Alvo</label>
                            <select id="run-ticker">
                                <option value="DIRR3">DIRR3 (Direcional)</option>
                                <option value="PETR4">PETR4 (Petrobras)</option>
                                <option value="VALE3">VALE3 (Vale)</option>
                                <option value="WEGE3">WEGE3 (WEG)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Estágio Pipeline</label>
                            <select id="run-stage">
                                <option value="all">Pipeline Completo (All)</option>
                                <option value="wacc">Apenas WACC</option>
                                <option value="dcf">Apenas DCF</option>
                                <option value="monte_carlo">Apenas Monte Carlo</option>
                                <option value="research">Apenas Auditoria IA</option>
                            </select>
                        </div>
                    </div>
                    <button class="btn-run" onclick="executarPipeline()" id="btn-exec">
                        <i class="fas fa-play"></i> Rodar Pipeline Assíncrono
                    </button>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2><i class="fas fa-terminal" style="color:#38bdf8;"></i> Console de Execução & Logs</h2>
                    <span id="badge-status" style="font-size:11px; color:#46e0a0; font-weight:700;"><i class="fas fa-circle-check"></i> Pronto</span>
                </div>
                <div id="console-output" class="console-box">Aguardando comando de execução...</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2><i class="fas fa-database" style="color:#a472ff;"></i> Indicadores Financeiros Calculados (data/processed/kpis_calculados.parquet)</h2>
                <button onclick="carregarKPIs()" class="btn-action" style="padding:4px 10px; font-size:11px;"><i class="fas fa-rotate"></i> Atualizar Tabela</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Data Base</th>
                            <th>Margem Bruta</th>
                            <th>Margem EBITDA</th>
                            <th>Margem Líquida</th>
                            <th>ROE</th>
                            <th>ROIC</th>
                            <th>Dívida Líq / EBITDA</th>
                        </tr>
                    </thead>
                    <tbody id="tbody-kpis">
                        <tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> Lendo banco Parquet...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentConfig = {};
        let pollingTimer = null;

        async function carregarConfig() {
            try {
                const res = await fetch('/api/cf_tech/config');
                currentConfig = await res.json();
                document.getElementById('cfg-rf').value = currentConfig.wacc?.risk_free_rate || 0.105;
                document.getElementById('cfg-mrp').value = currentConfig.wacc?.market_risk_premium || 0.055;
                document.getElementById('cfg-tax').value = currentConfig.wacc?.tax_rate || 0.34;
                document.getElementById('cfg-g').value = currentConfig.dcf?.perpetual_growth_rate || 0.045;
                document.getElementById('cfg-years').value = currentConfig.dcf?.projection_years || 5;
                document.getElementById('cfg-iter').value = currentConfig.monte_carlo?.iterations || 10000;
            } catch (err) {
                console.error(err);
            }
        }

        async function salvarConfig() {
            const updated = {
                ...currentConfig,
                wacc: {
                    ...currentConfig.wacc,
                    risk_free_rate: parseFloat(document.getElementById('cfg-rf').value),
                    market_risk_premium: parseFloat(document.getElementById('cfg-mrp').value),
                    tax_rate: parseFloat(document.getElementById('cfg-tax').value)
                },
                dcf: {
                    ...currentConfig.dcf,
                    perpetual_growth_rate: parseFloat(document.getElementById('cfg-g').value),
                    projection_years: parseInt(document.getElementById('cfg-years').value)
                },
                monte_carlo: {
                    ...currentConfig.monte_carlo,
                    iterations: parseInt(document.getElementById('cfg-iter').value)
                }
            };

            const res = await fetch('/api/cf_tech/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updated)
            });
            const data = await res.json();
            alert(data.message || 'Configurações salvas!');
        }

        async function executarPipeline() {
            const ticker = document.getElementById('run-ticker').value;
            const stage = document.getElementById('run-stage').value;
            const btn = document.getElementById('btn-exec');
            
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executando Pipeline...';
            document.getElementById('badge-status').innerHTML = '<span style="color:#f59e0b;"><i class="fas fa-spinner fa-spin"></i> Processando...</span>';

            await fetch('/api/cf_tech/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, stage })
            });

            if (pollingTimer) clearInterval(pollingTimer);
            pollingTimer = setInterval(verificarStatus, 1500);
        }

        async function verificarStatus() {
            try {
                const res = await fetch('/api/cf_tech/status');
                const data = await res.json();
                
                const consoleBox = document.getElementById('console-output');
                consoleBox.innerText = (data.logs || []).join('');
                consoleBox.scrollTop = consoleBox.scrollHeight;

                if (!data.running) {
                    clearInterval(pollingTimer);
                    document.getElementById('btn-exec').disabled = false;
                    document.getElementById('btn-exec').innerHTML = '<i class="fas fa-play"></i> Rodar Pipeline Assíncrono';
                    document.getElementById('badge-status').innerHTML = '<span style="color:#46e0a0;"><i class="fas fa-circle-check"></i> Concluído com Sucesso</span>';
                    carregarKPIs();
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function carregarKPIs() {
            try {
                const res = await fetch('/api/cf_tech/kpis');
                const kpis = await res.json();
                const tbody = document.getElementById('tbody-kpis');
                if (!kpis || kpis.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">Nenhum KPI pré-calculado no banco parquet. Execute um pipeline acima.</td></tr>';
                    return;
                }

                let html = '';
                for (const row of kpis) {
                    html += `
                    <tr>
                        <td>${row.ticker || '-'}</td>
                        <td>${row.data_base || '-'}</td>
                        <td>${row.margem_bruta != null ? (row.margem_bruta * 100).toFixed(1) + '%' : '-'}</td>
                        <td>${row.margem_ebitda != null ? (row.margem_ebitda * 100).toFixed(1) + '%' : '-'}</td>
                        <td>${row.margem_liquida != null ? (row.margem_liquida * 100).toFixed(1) + '%' : '-'}</td>
                        <td>${row.roe != null ? (row.roe * 100).toFixed(1) + '%' : '-'}</td>
                        <td>${row.roic != null ? (row.roic * 100).toFixed(1) + '%' : '-'}</td>
                        <td>${row.divida_liquida_ebitda != null ? row.divida_liquida_ebitda.toFixed(2) + 'x' : '-'}</td>
                    </tr>
                    `;
                }
                tbody.innerHTML = html;
            } catch (err) {
                console.error(err);
            }
        }

        window.addEventListener('DOMContentLoaded', () => {
            carregarConfig();
            carregarKPIs();
        });
    </script>
</body>
</html>
"""
        return html

def iniciar_servidor(port=PORT):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, CFTechHandler)
    print(f"[CF Tech Server] Pipelines ativo em http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    iniciar_servidor()
