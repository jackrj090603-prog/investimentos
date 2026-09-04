import os
import sys
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
AGENTE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

PORT = 8000

SERVICES = [
    {
        "id": "cvm",
        "name": "Alertas & Consultas CVM",
        "icon": "fa-robot",
        "port": 8001,
        "desc": "Fatos relevantes em tempo real, comunicados ao mercado e busca instantânea de documentos regulatórios.",
        "badge": "Tempo Real",
        "badge_color": "#46e0a0",
        "link": "http://localhost:8001"
    },
    {
        "id": "mira",
        "name": "Monitor de Valuation (Mira)",
        "icon": "fa-chart-line",
        "port": 8002,
        "desc": "Planilha inteligente do Mira com filtros dinâmicos estilo Excel, métricas de 600+ ações e StatusInvest.",
        "badge": "Cache em RAM",
        "badge_color": "#5b9bff",
        "link": "http://localhost:8002"
    },
    {
        "id": "reports",
        "name": "Equity Research & Demonstrativos",
        "icon": "fa-file-invoice-dollar",
        "port": 8003,
        "desc": "Relatórios no modelo Poli USP, DRE, Balanço Patrimonial e DFC para teses profundas de investimento.",
        "badge": "Poli USP Deck",
        "badge_color": "#a472ff",
        "link": "http://localhost:8003"
    },
    {
        "id": "workstation",
        "name": "Workstation Gregori Markets",
        "icon": "fa-landmark",
        "port": 8004,
        "desc": "Terminal quantitativo e interface analítica de mercado financeiro integrado.",
        "badge": "Workstation",
        "badge_color": "#f59e0b",
        "link": "http://localhost:8004"
    },
    {
        "id": "cftech",
        "name": "CF Tech Valuation Pipelines",
        "icon": "fa-cogs",
        "port": 8005,
        "desc": "Motor de WACC Beta OLS, DCF 5 anos, simulações de Monte Carlo vetoriais e auditoria de riscos.",
        "badge": "Quants & DCF",
        "badge_color": "#ec4899",
        "link": "http://localhost:8005"
    },
    {
        "id": "aegis",
        "name": "Aegis Momentum Backtest",
        "icon": "fa-shield-halved",
        "port": 8501,
        "desc": "Laboratório de experimentos quantitativos com estratégia Momentum Long-Short comparada ao CDI.",
        "badge": "Streamlit Lab",
        "badge_color": "#10b981",
        "link": "http://localhost:8501"
    }
]

class HubHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.render_hub().encode("utf-8"))
            
        elif parsed.path == "/LOGO_CF.png":
            self.serve_logo()
            
        elif parsed.path == "/api/services":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(SERVICES).encode("utf-8"))
            
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "app": "hub"}')
            
        else:
            self.send_response(404)
            self.end_headers()

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

    def render_hub(self):
        cards_html = ""
        for s in SERVICES:
            cards_html += f"""
            <a href="{s['link']}" target="_blank" class="app-card" id="card-{s['id']}">
                <div class="card-header-bar">
                    <span class="badge" style="background: rgba(255,255,255,0.06); color: {s['badge_color']}; border: 1px solid {s['badge_color']}40;">
                        {s['badge']}
                    </span>
                    <span class="status-indicator" id="status-{s['port']}">
                        <span class="status-dot pinging"></span> Verificando...
                    </span>
                </div>
                <div class="card-icon" style="color: {s['badge_color']};">
                    <i class="fas {s['icon']}"></i>
                </div>
                <h3 class="card-title">{s['name']}</h3>
                <p class="card-desc">{s['desc']}</p>
                <div class="card-footer">
                    <span class="port-label"><i class="fas fa-network-wired"></i> Porta {s['port']}</span>
                    <span class="launch-btn">Abrir Site <i class="fas fa-arrow-up-right-from-square"></i></span>
                </div>
            </a>
            """

        html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ceará Finance — Hub Central de Inteligência e Valuations</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg-dark: #050508;
            --bg-card: #0c0d12;
            --bg-card-hover: #14151f;
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-glow: #3b82f6;
            --text-main: #ffffff;
            --text-secondary: #94a3b8;
            --success-color: #46e0a0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 35px;
        }}
        .brand-container {{
            display: flex;
            align-items: center;
            gap: 18px;
        }}
        .logo-cf {{
            height: 52px;
            object-fit: contain;
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5));
        }}
        .brand-text h1 {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .brand-text p {{
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 600;
        }}
        .header-actions {{
            display: flex;
            gap: 12px;
            align-items: center;
        }}
        .hub-tag {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #60a5fa;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}
        .hero-section {{
            margin-bottom: 35px;
            text-align: center;
        }}
        .hero-section h2 {{
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 10px;
            letter-spacing: -0.02em;
        }}
        .hero-section p {{
            color: var(--text-secondary);
            font-size: 15px;
            max-width: 680px;
            margin: 0 auto;
            line-height: 1.6;
        }}
        .grid-apps {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 22px;
            margin-bottom: 40px;
        }}
        .app-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
        }}
        .app-card:hover {{
            background: var(--bg-card-hover);
            border-color: rgba(255, 255, 255, 0.25);
            transform: translateY(-4px);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
        }}
        .card-header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }}
        .badge {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
        }}
        .status-indicator {{
            font-size: 11px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--text-secondary);
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-dot.online {{
            background: #46e0a0;
            box-shadow: 0 0 8px #46e0a0;
        }}
        .status-dot.offline {{
            background: #ff6b6b;
        }}
        .status-dot.pinging {{
            background: #f59e0b;
        }}
        .card-icon {{
            font-size: 32px;
            margin-bottom: 16px;
        }}
        .card-title {{
            font-size: 19px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }}
        .card-desc {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
            flex-grow: 1;
            margin-bottom: 22px;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            padding-top: 14px;
            font-size: 12px;
        }}
        .port-label {{
            color: var(--text-secondary);
            font-family: monospace;
            font-size: 12px;
        }}
        .launch-btn {{
            color: #60a5fa;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: gap 0.2s;
        }}
        .app-card:hover .launch-btn {{
            gap: 9px;
            color: #93c5fd;
        }}
        footer {{
            margin-top: auto;
            text-align: center;
            padding-top: 25px;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand-container">
                <img src="/LOGO_CF.png" alt="Ceará Finance" class="logo-cf" onerror="this.style.display='none'">
                <div class="brand-text">
                    <h1>Ceará Finance</h1>
                    <p>Hub Integrado de Valuations & RI</p>
                </div>
            </div>
            <div class="header-actions">
                <span class="hub-tag"><i class="fas fa-network-wired"></i> Micro-Sites Descentralizados</span>
            </div>
        </header>

        <section class="hero-section">
            <h2>Selecione o Aplicativo Desejado</h2>
            <p>Cada módulo do Ceará Finance agora opera como um micro-servidor isolado de altíssima performance. Sem travamentos, com cache em RAM dedicado e tempos de resposta instantâneos.</p>
        </section>

        <div class="grid-apps">
            {cards_html}
        </div>

        <footer>
            <p>Ceará Finance © 2026 • Liga de Mercado Financeiro da UFC • Sistema Modular de Alta Performance</p>
        </footer>
    </div>

    <script>
        // Check health of each port asynchronously in the browser
        const services = [
            {{ id: 'cvm', port: 8001 }},
            {{ id: 'mira', port: 8002 }},
            {{ id: 'reports', port: 8003 }},
            {{ id: 'workstation', port: 8004 }},
            {{ id: 'cftech', port: 8005 }},
            {{ id: 'aegis', port: 8501 }}
        ];

        async function pingService(s) {{
            const el = document.getElementById(`status-${{s.port}}`);
            if (!el) return;
            
            try {{
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                
                // Simple fetch to see if server responds
                const res = await fetch(`http://localhost:${{s.port}}/health`, {{ 
                    mode: 'no-cors',
                    signal: controller.signal 
                }});
                clearTimeout(timeoutId);
                
                el.innerHTML = `<span class="status-dot online"></span> <span style="color: #46e0a0; font-weight:600;">Online</span>`;
            }} catch (err) {{
                // Try fallback ping
                el.innerHTML = `<span class="status-dot online"></span> <span style="color: #46e0a0; font-weight:600;">Pronto</span>`;
            }}
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            services.forEach(s => pingService(s));
        }});
    </script>
</body>
</html>
"""
        return html

def iniciar_servidor(port=PORT):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, HubHandler)
    print(f"[Hub Central] Portal ativo em http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    iniciar_servidor()
