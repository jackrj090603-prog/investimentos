import os
import sys
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

if AGENTE_DIR not in sys.path:
    sys.path.insert(0, AGENTE_DIR)

import storage

PORT = 8001

class CVMHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.render_cvm_dashboard().encode("utf-8"))
            
        elif parsed.path == "/LOGO_CF.png":
            self.serve_logo()
            
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "app": "cvm"}')
            
        elif parsed.path == "/api/documentos":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            q = params.get("q", [""])[0].strip()
            if q:
                docs = storage.buscar_documentos_por_termo(q)
            else:
                docs = storage.get_todos_documentos(limit=150)
                
            self.wfile.write(json.dumps(docs).encode("utf-8"))
            
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

    def render_cvm_dashboard(self):
        html = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CVM Intelligence — Ceará Finance</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-dark: #07080c;
            --bg-card: #0d0f17;
            --border-color: rgba(255, 255, 255, 0.08);
            --accent: #46e0a0;
            --text-main: #ffffff;
            --text-muted: #8e9bb0;
            --font-mono: 'JetBrains Mono', monospace;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 24px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 25px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .brand img {
            height: 48px;
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
        .header-nav {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .btn-hub {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .btn-hub:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .search-container {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        .search-box {
            flex-grow: 1;
            position: relative;
        }
        .search-box i {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
        }
        .search-box input {
            width: 100%;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 12px 16px 12px 44px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 14px;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-box input:focus {
            border-color: var(--accent);
        }
        .filter-pills {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 25px;
        }
        .pill {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .pill:hover, .pill.active {
            background: rgba(70, 224, 160, 0.12);
            border-color: var(--accent);
            color: #ffffff;
        }
        .metrics-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 25px;
        }
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 16px;
            border-radius: 12px;
        }
        .metric-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        .metric-val {
            font-size: 22px;
            font-weight: 800;
            color: #ffffff;
            font-family: var(--font-mono);
        }
        .docs-list {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .doc-item {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px 22px;
            transition: transform 0.15s, border-color 0.15s;
        }
        .doc-item:hover {
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }
        .doc-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .doc-title-line {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .ticker-tag {
            background: #1e293b;
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            font-family: var(--font-mono);
        }
        .company-name {
            font-size: 15px;
            font-weight: 700;
        }
        .doc-category {
            background: rgba(70, 224, 160, 0.08);
            color: var(--accent);
            border: 1px solid rgba(70, 224, 160, 0.25);
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
        }
        .doc-meta {
            font-size: 12px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }
        .doc-desc {
            font-size: 14px;
            color: #cbd5e1;
            margin-bottom: 12px;
            line-height: 1.5;
        }
        .doc-summary {
            background: rgba(0, 0, 0, 0.35);
            border-left: 3px solid var(--accent);
            padding: 10px 14px;
            border-radius: 0 8px 8px 0;
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 12px;
            line-height: 1.5;
        }
        .doc-footer {
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }
        .doc-link {
            font-size: 12px;
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .doc-link:hover {
            text-decoration: underline;
        }
        .empty-state {
            text-align: center;
            padding: 50px 20px;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <img src="/LOGO_CF.png" alt="Ceará Finance" onerror="this.style.display='none'">
                <div class="brand-title">
                    <h1>Alertas & Consultas CVM</h1>
                    <p>Monitoramento Regulatório Instantâneo</p>
                </div>
            </div>
            <div class="header-nav">
                <a href="http://localhost:8000" class="btn-hub"><i class="fas fa-arrow-left"></i> Voltar ao Hub</a>
                <button onclick="carregarDocs()" class="btn-hub" style="cursor:pointer;"><i class="fas fa-rotate"></i> Atualizar</button>
            </div>
        </header>

        <div class="metrics-bar">
            <div class="metric-card">
                <div class="metric-label">Total de Documentos no Banco</div>
                <div class="metric-val" id="metric-total">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fatos Relevantes Detectados</div>
                <div class="metric-val" id="metric-fr">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Empresas Monitoradas</div>
                <div class="metric-val" id="metric-cia">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Status da Conexão</div>
                <div class="metric-val" style="color: #46e0a0; font-size: 16px; display:flex; align-items:center; gap:8px;">
                    <i class="fas fa-circle-check"></i> SQLite Live
                </div>
            </div>
        </div>

        <div class="search-container">
            <div class="search-box">
                <i class="fas fa-search"></i>
                <input type="text" id="input-search" placeholder="Buscar por ticker, nome da empresa, assunto ou palavra-chave (ex: DIRR3, dividendo, balanço)..." oninput="debounceSearch()">
            </div>
        </div>

        <div class="filter-pills">
            <button class="pill active" onclick="filtrarCategoria('', this)">Todos</button>
            <button class="pill" onclick="filtrarCategoria('Fato Relevante', this)">Fatos Relevantes</button>
            <button class="pill" onclick="filtrarCategoria('Comunicado', this)">Comunicados</button>
            <button class="pill" onclick="filtrarCategoria('DIRR3', this)">DIRR3</button>
            <button class="pill" onclick="filtrarCategoria('PETR4', this)">PETR4</button>
            <button class="pill" onclick="filtrarCategoria('VALE3', this)">VALE3</button>
            <button class="pill" onclick="filtrarCategoria('WEGE3', this)">WEGE3</button>
        </div>

        <div id="docs-list" class="docs-list">
            <div class="empty-state"><i class="fas fa-spinner fa-spin"></i> Carregando comunicados da CVM...</div>
        </div>
    </div>

    <script>
        let todosDocumentos = [];
        let filtroAtivo = '';
        let timerSearch = null;

        async function carregarDocs(termo = '') {
            const listEl = document.getElementById('docs-list');
            try {
                const url = termo ? `/api/documentos?q=${encodeURIComponent(termo)}` : '/api/documentos';
                const res = await fetch(url);
                todosDocumentos = await res.json();
                renderizarDocs();
                atualizarMetricas();
            } catch (err) {
                listEl.innerHTML = `<div class="empty-state" style="color: #ff6b6b;">Erro ao carregar documentos: ${err.message}</div>`;
            }
        }

        function atualizarMetricas() {
            document.getElementById('metric-total').innerText = todosDocumentos.length;
            const frCount = todosDocumentos.filter(d => (d.category || '').toLowerCase().includes('relevante') || (d.doc_type || '').toLowerCase().includes('relevante')).length;
            document.getElementById('metric-fr').innerText = frCount;
            const cias = new Set(todosDocumentos.map(d => d.ticker || d.company_name).filter(Boolean));
            document.getElementById('metric-cia').innerText = cias.size || 4;
        }

        function filtrarCategoria(cat, btn) {
            filtroAtivo = cat;
            document.querySelectorAll('.filter-pills .pill').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            renderizarDocs();
        }

        function debounceSearch() {
            clearTimeout(timerSearch);
            timerSearch = setTimeout(() => {
                const termo = document.getElementById('input-search').value.trim();
                carregarDocs(termo);
            }, 300);
        }

        function renderizarDocs() {
            const listEl = document.getElementById('docs-list');
            let docs = [...todosDocumentos];

            if (filtroAtivo) {
                const f = filtroAtivo.toLowerCase();
                docs = docs.filter(d => {
                    const str = `${d.ticker} ${d.company_name} ${d.category} ${d.doc_type} ${d.description}`.toLowerCase();
                    return str.includes(f);
                });
            }

            if (docs.length === 0) {
                listEl.innerHTML = '<div class="empty-state"><i class="fas fa-folder-open" style="font-size: 32px; margin-bottom: 12px; display:block;"></i>Nenhum documento encontrado com os critérios de busca.</div>';
                return;
            }

            let html = '';
            for (const d of docs) {
                const ticker = d.ticker || 'CVM';
                const comp = d.company_name || 'Companhia Aberta';
                const cat = d.category || d.doc_type || 'Documento CVM';
                const data = d.delivery_date || d.ref_date || d.data_processamento || '-';
                const desc = d.description || 'Sem descrição cadastrada.';
                const resumo = d.resumo_ia ? `<div class="doc-summary"><i class="fas fa-brain" style="color: #a472ff; margin-right: 6px;"></i><strong>Resumo IA:</strong> ${d.resumo_ia}</div>` : '';
                const link = d.link ? `<a href="${d.link}" target="_blank" class="doc-link">Acessar na CVM <i class="fas fa-external-link-alt"></i></a>` : '';

                html += `
                <div class="doc-item">
                    <div class="doc-header">
                        <div class="doc-title-line">
                            <span class="ticker-tag">${ticker}</span>
                            <span class="company-name">${comp}</span>
                            <span class="doc-category">${cat}</span>
                        </div>
                        <div class="doc-meta"><i class="far fa-clock"></i> ${data}</div>
                    </div>
                    <div class="doc-desc">${desc}</div>
                    ${resumo}
                    <div class="doc-footer">
                        ${link}
                    </div>
                </div>
                `;
            }
            listEl.innerHTML = html;
        }

        window.addEventListener('DOMContentLoaded', () => {
            carregarDocs();
            setInterval(() => carregarDocs(document.getElementById('input-search').value.trim()), 30000);
        });
    </script>
</body>
</html>
"""
        return html

def iniciar_servidor(port=PORT):
    storage.init_db()
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, CVMHandler)
    print(f"[CVM Server] Alertas CVM ativos em http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    iniciar_servidor()
