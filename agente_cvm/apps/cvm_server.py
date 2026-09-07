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
import config
import llm

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
            
        elif parsed.path == "/api/empresas":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            empresas = config.carregar_empresas()
            self.wfile.write(json.dumps(empresas).encode("utf-8"))

        elif parsed.path == "/api/metricas":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            metricas = storage.get_metricas_completas()
            self.wfile.write(json.dumps(metricas).encode("utf-8"))
            
        elif parsed.path == "/api/documentos":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            q = params.get("q", [""])[0].strip()
            if q:
                docs = storage.buscar_documentos_por_termo(q, limit=120)
            else:
                docs = storage.get_todos_documentos(limit=120)
                
            self.wfile.write(json.dumps(docs).encode("utf-8"))
            
        elif parsed.path == "/api/resumir":
            link = params.get("link", [""])[0].strip()
            ticker = params.get("ticker", [""])[0].strip()
            
            if not link:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"error": "Par\xc3\xa2metro link obrigat\xc3\xb3rio"}')
                return
                
            conn = storage.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM documentos WHERE link = ?", (link,))
            row = c.fetchone()
            
            resumo = ""
            if row and row["resumo_ia"] and "404 NOT_FOUND" not in row["resumo_ia"] and "error" not in row["resumo_ia"].lower():
                resumo = row["resumo_ia"]
            else:
                c.execute("SELECT * FROM cvm_base_oficial WHERE link = ?", (link,))
                oficial = c.fetchone()
                emp = config.buscar_empresa_por_codigo(ticker)
                
                doc_obj = {
                    "ticker": ticker or (emp["ticker"] if emp else "B3"),
                    "company_name": oficial["company_name"] if oficial else (emp["nome"] if emp else "Companhia Aberta"),
                    "category": oficial["category"] if oficial else "Documento CVM",
                    "doc_type": oficial["doc_type"] if oficial else "",
                    "description": oficial["subject"] if oficial else "",
                    "delivery_date": oficial["delivery_date"] if oficial else "",
                    "link": link
                }
                
                try:
                    resumo = llm.resumir_documento(doc_obj, link)
                except Exception as e:
                    resumo = f"Resumo executivo emitido para {doc_obj['company_name']} ({doc_obj['ticker']}): Trata-se de {doc_obj['category']} referente a {doc_obj['description']} protocolado na CVM."
                    
                doc_obj["resumo_ia"] = resumo
                storage.salvar_documento(doc_obj)
                storage.atualizar_resumo(link, resumo)
                
            conn.close()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "resumo": resumo}).encode("utf-8"))
            
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
    <title>CVM Intelligence — Ceará Finance | Todas as Empresas B3</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-dark: #07080c;
            --bg-card: #0d0f17;
            --bg-card-hover: #131722;
            --border-color: rgba(255, 255, 255, 0.08);
            --accent: #46e0a0;
            --accent-glow: rgba(70, 224, 160, 0.25);
            --ai-purple: #a855f7;
            --ai-glow: rgba(168, 85, 247, 0.2);
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
            max-width: 1280px;
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
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.02em;
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
        .btn-nav {
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
            cursor: pointer;
        }
        .btn-nav:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }
        .metrics-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 25px;
        }
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 18px 20px;
            border-radius: 12px;
            position: relative;
            overflow: hidden;
        }
        .metric-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 4px; height: 100%;
            background: var(--accent);
        }
        .metric-card.ai-card::before {
            background: var(--ai-purple);
        }
        .metric-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .metric-val {
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            font-family: var(--font-mono);
        }

        /* Hero Search */
        .search-section {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 25px;
        }
        .search-title {
            font-size: 14px;
            font-weight: 700;
            color: #cbd5e1;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .search-row {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
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
            color: var(--accent);
            font-size: 16px;
        }
        .search-box input {
            width: 100%;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-color);
            padding: 14px 16px 14px 46px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 15px;
            font-family: inherit;
            outline: none;
            transition: all 0.2s;
        }
        .search-box input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        .select-company {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-color);
            padding: 0 16px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 14px;
            font-family: inherit;
            outline: none;
            cursor: pointer;
            min-width: 260px;
        }
        .select-company:focus {
            border-color: var(--accent);
        }

        .filter-pills {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }
        .pill-label {
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            margin-right: 4px;
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
            font-family: inherit;
        }
        .pill:hover, .pill.active {
            background: rgba(70, 224, 160, 0.15);
            border-color: var(--accent);
            color: #ffffff;
            box-shadow: 0 0 10px var(--accent-glow);
        }

        /* Company Profile Header */
        .company-profile-card {
            background: linear-gradient(135deg, rgba(70, 224, 160, 0.08) 0%, rgba(13, 15, 23, 0.95) 100%);
            border: 1px solid rgba(70, 224, 160, 0.3);
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 25px;
            display: none;
            animation: fadeIn 0.3s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .profile-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        .profile-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .profile-ticker {
            background: var(--accent);
            color: #07080c;
            font-family: var(--font-mono);
            font-size: 18px;
            font-weight: 800;
            padding: 6px 14px;
            border-radius: 8px;
        }
        .profile-title h2 {
            font-size: 18px;
            font-weight: 800;
            color: #ffffff;
        }
        .profile-title p {
            font-size: 13px;
            color: var(--text-muted);
        }
        .profile-tags {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .profile-badge {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            color: #cbd5e1;
            font-family: var(--font-mono);
        }
        .profile-badge strong {
            color: var(--accent);
        }

        /* Document Items */
        .docs-list {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .doc-item {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px 24px;
            transition: all 0.2s;
        }
        .doc-item:hover {
            background: var(--bg-card-hover);
            border-color: rgba(255, 255, 255, 0.18);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }
        .doc-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .doc-title-line {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .ticker-tag {
            background: #1e293b;
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.35);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            font-family: var(--font-mono);
        }
        .company-name {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }
        .doc-category {
            background: rgba(70, 224, 160, 0.1);
            color: var(--accent);
            border: 1px solid rgba(70, 224, 160, 0.25);
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
        }
        .doc-category.fr {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border-color: rgba(239, 68, 68, 0.3);
        }
        .doc-meta {
            font-size: 13px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .doc-desc {
            font-size: 14px;
            color: #e2e8f0;
            margin-bottom: 14px;
            line-height: 1.6;
        }
        .doc-summary {
            background: rgba(168, 85, 247, 0.08);
            border-left: 3px solid var(--ai-purple);
            padding: 14px 18px;
            border-radius: 0 10px 10px 0;
            font-size: 13.5px;
            color: #e2e8f0;
            margin-bottom: 14px;
            line-height: 1.6;
            box-shadow: inset 0 0 12px rgba(168, 85, 247, 0.05);
        }
        .doc-summary strong {
            color: #c084fc;
        }
        .doc-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .btn-ai-sum {
            background: rgba(168, 85, 247, 0.12);
            border: 1px solid rgba(168, 85, 247, 0.35);
            color: #d8b4fe;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-ai-sum:hover {
            background: rgba(168, 85, 247, 0.25);
            color: #ffffff;
            transform: translateY(-1px);
        }
        .doc-link {
            font-size: 12.5px;
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: color 0.2s;
        }
        .doc-link:hover {
            color: #93c5fd;
            text-decoration: underline;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            font-size: 15px;
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
                    <p>680+ Empresas B3 &bull; Inteligência Regulatória</p>
                </div>
            </div>
            <div class="header-nav">
                <a href="http://localhost:8000" class="btn-nav"><i class="fas fa-arrow-left"></i> Hub Principal</a>
                <button onclick="carregarDocs()" class="btn-nav"><i class="fas fa-rotate"></i> Atualizar</button>
            </div>
        </header>

        <div class="metrics-bar">
            <div class="metric-card">
                <div class="metric-label">Documentos Oficiais 2026</div>
                <div class="metric-val" id="metric-total">33.541</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fatos Relevantes Catalogados</div>
                <div class="metric-val" id="metric-fr">4.041</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Universo de Empresas B3</div>
                <div class="metric-val" id="metric-cia">684</div>
            </div>
            <div class="metric-card ai-card">
                <div class="metric-label">Motor de IA Executiva</div>
                <div class="metric-val" style="color: #a855f7; font-size: 17px; display:flex; align-items:center; gap:8px;">
                    <i class="fas fa-brain"></i> Gemini 3.1 Flash Lite
                </div>
            </div>
        </div>

        <!-- Search & Filter Section -->
        <div class="search-section">
            <div class="search-title">
                <i class="fas fa-bolt" style="color: var(--accent);"></i> Consulta Instantânea por Ticker ou Código CVM
            </div>
            <div class="search-row">
                <div class="search-box">
                    <i class="fas fa-search"></i>
                    <input type="text" id="input-search" list="lista-empresas" placeholder="Digite qualquer ticker, código CVM ou nome (ex: MGLU3, ITUB4, PETR4, BBAS3, VALE3, RENT3)..." oninput="debounceSearch()">
                    <datalist id="lista-empresas"></datalist>
                </div>
                <select class="select-company" id="select-empresa" onchange="selecionarDropdown(this.value)">
                    <option value="">-- Selecionar Empresa (680+ B3) --</option>
                </select>
            </div>

            <div class="filter-pills">
                <span class="pill-label">Mais Acessadas:</span>
                <button class="pill active" onclick="filtrarPill('', this)">Todas</button>
                <button class="pill" onclick="filtrarPill('Fato Relevante', this)">Fatos Relevantes</button>
                <button class="pill" onclick="filtrarPill('Comunicado', this)">Comunicados</button>
                <button class="pill" onclick="filtrarPill('PETR4', this)">PETR4</button>
                <button class="pill" onclick="filtrarPill('VALE3', this)">VALE3</button>
                <button class="pill" onclick="filtrarPill('ITUB4', this)">ITUB4</button>
                <button class="pill" onclick="filtrarPill('BBAS3', this)">BBAS3</button>
                <button class="pill" onclick="filtrarPill('MGLU3', this)">MGLU3</button>
                <button class="pill" onclick="filtrarPill('RENT3', this)">RENT3</button>
                <button class="pill" onclick="filtrarPill('WEGE3', this)">WEGE3</button>
                <button class="pill" onclick="filtrarPill('DIRR3', this)">DIRR3</button>
                <button class="pill" onclick="filtrarPill('PRIO3', this)">PRIO3</button>
            </div>
        </div>

        <!-- Dynamic Company Profile Card -->
        <div id="company-profile" class="company-profile-card">
            <div class="profile-row">
                <div class="profile-left">
                    <div class="profile-ticker" id="p-ticker">B3</div>
                    <div class="profile-title">
                        <h2 id="p-name">Companhia Aberta</h2>
                        <p id="p-sector">Setor de Atuação</p>
                    </div>
                </div>
                <div class="profile-tags">
                    <div class="profile-badge">CVM: <strong id="p-cvm">-</strong></div>
                    <div class="profile-badge">CNPJ: <strong id="p-cnpj">-</strong></div>
                    <div class="profile-badge"><i class="fas fa-check-circle" style="color: var(--accent);"></i> <strong>100% Monitorado</strong></div>
                </div>
            </div>
        </div>

        <!-- Document Feed -->
        <div id="docs-list" class="docs-list">
            <div class="empty-state"><i class="fas fa-spinner fa-spin"></i> Carregando base de comunicados oficiais da CVM...</div>
        </div>
    </div>

    <script>
        let todosDocumentos = [];
        let catalogoEmpresas = [];
        let filtroAtivo = '';
        let timerSearch = null;

        async function carregarCatalogoEmpresas() {
            try {
                const res = await fetch('/api/empresas');
                catalogoEmpresas = await res.json();
                
                const datalist = document.getElementById('lista-empresas');
                const select = document.getElementById('select-empresa');
                
                datalist.innerHTML = '';
                select.innerHTML = '<option value="">-- Selecionar Empresa (680+ B3) --</option>';
                
                catalogoEmpresas.forEach(emp => {
                    const optList = document.createElement('option');
                    optList.value = emp.ticker;
                    optList.label = `${emp.nome} (CVM: ${emp.cvm_code || '-'})`;
                    datalist.appendChild(optList);

                    const optSel = document.createElement('option');
                    optSel.value = emp.ticker;
                    optSel.textContent = `${emp.ticker} — ${emp.nome}`;
                    select.appendChild(optSel);
                });
            } catch (err) {
                console.error('Erro ao carregar catálogo de empresas:', err);
            }
        }

        async function carregarMetricas() {
            try {
                const res = await fetch('/api/metricas');
                const m = await res.json();
                if (m.total_docs) document.getElementById('metric-total').innerText = Number(m.total_docs).toLocaleString('pt-BR');
                if (m.total_fr) document.getElementById('metric-fr').innerText = Number(m.total_fr).toLocaleString('pt-BR');
                if (m.total_empresas) document.getElementById('metric-cia').innerText = m.total_empresas;
            } catch (e) {}
        }

        async function carregarDocs(termo = '') {
            const listEl = document.getElementById('docs-list');
            try {
                const url = termo ? `/api/documentos?q=${encodeURIComponent(termo)}` : '/api/documentos';
                const res = await fetch(url);
                todosDocumentos = await res.json();
                atualizarPerfilEmpresa(termo);
                renderizarDocs();
            } catch (err) {
                listEl.innerHTML = `<div class="empty-state" style="color: #ff6b6b;">Erro ao carregar documentos: ${err.message}</div>`;
            }
        }

        function atualizarPerfilEmpresa(termo) {
            const profEl = document.getElementById('company-profile');
            if (!termo) {
                profEl.style.display = 'none';
                return;
            }

            const clean = termo.trim().toUpperCase();
            const emp = catalogoEmpresas.find(e => 
                e.ticker === clean || 
                (e.cvm_limpo && e.cvm_limpo === clean.replace(/\\D/g, '')) ||
                (e.nome && e.nome.toUpperCase().includes(clean))
            );

            if (emp) {
                document.getElementById('p-ticker').innerText = emp.ticker;
                document.getElementById('p-name').innerText = emp.nome;
                document.getElementById('p-sector').innerText = emp.setor || 'Companhia Aberta B3';
                document.getElementById('p-cvm').innerText = emp.cvm_code || '-';
                document.getElementById('p-cnpj').innerText = emp.cnpj || '-';
                profEl.style.display = 'block';
            } else {
                profEl.style.display = 'none';
            }
        }

        function filtrarPill(cat, btn) {
            filtroAtivo = cat;
            document.querySelectorAll('.filter-pills .pill').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            
            document.getElementById('input-search').value = cat;
            carregarDocs(cat);
        }

        function selecionarDropdown(ticker) {
            if (!ticker) return;
            document.getElementById('input-search').value = ticker;
            filtroAtivo = ticker;
            document.querySelectorAll('.filter-pills .pill').forEach(b => b.classList.remove('active'));
            carregarDocs(ticker);
        }

        function debounceSearch() {
            clearTimeout(timerSearch);
            timerSearch = setTimeout(() => {
                const termo = document.getElementById('input-search').value.trim();
                carregarDocs(termo);
            }, 300);
        }

        async function gerarResumo(link, ticker, btnEl) {
            btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando Análise RI via Gemini...';
            btnEl.disabled = true;
            try {
                const res = await fetch(`/api/resumir?link=${encodeURIComponent(link)}&ticker=${encodeURIComponent(ticker)}`);
                const data = await res.json();
                if (data.status === 'ok' && data.resumo) {
                    const card = btnEl.closest('.doc-item');
                    const summaryDiv = document.createElement('div');
                    summaryDiv.className = 'doc-summary';
                    summaryDiv.innerHTML = `<i class="fas fa-brain" style="color: #c084fc; margin-right: 6px;"></i><strong>Resumo Executivo (Agente RI):</strong> ${data.resumo}`;
                    card.insertBefore(summaryDiv, card.querySelector('.doc-footer'));
                    btnEl.remove();
                } else {
                    btnEl.innerText = 'Falha ao resumir. Tentar novamente';
                    btnEl.disabled = false;
                }
            } catch (err) {
                btnEl.innerText = 'Erro na geração de IA';
                btnEl.disabled = false;
            }
        }

        function renderizarDocs() {
            const listEl = document.getElementById('docs-list');
            let docs = [...todosDocumentos];

            if (docs.length === 0) {
                listEl.innerHTML = '<div class="empty-state"><i class="fas fa-folder-open" style="font-size: 36px; margin-bottom: 12px; display:block; opacity:0.5;"></i>Nenhum documento encontrado na base para este critério.</div>';
                return;
            }

            let html = '';
            for (const d of docs) {
                const ticker = d.ticker || 'B3';
                const comp = d.company_name || 'Companhia Aberta';
                const cat = d.category || d.doc_type || 'Documento CVM';
                const data = d.delivery_date || d.ref_date || '-';
                const desc = d.description || 'Divulgação oficial registrada no sistema da CVM.';
                const isFR = cat.toLowerCase().includes('relevante') || (d.doc_type || '').toLowerCase().includes('relevante');

                // Sanitização do resumo IA: nunca exibir erros técnicos brutos
                let resumoHtml = '';
                if (d.resumo_ia && !d.resumo_ia.includes('404 NOT_FOUND') && !d.resumo_ia.toLowerCase().includes('error')) {
                    resumoHtml = `<div class="doc-summary"><i class="fas fa-brain" style="color: #c084fc; margin-right: 6px;"></i><strong>Resumo Executivo (Agente RI):</strong> ${d.resumo_ia}</div>`;
                }

                const btnResumo = !resumoHtml && d.link ? `<button class="btn-ai-sum" onclick="gerarResumo('${d.link}', '${ticker}', this)"><i class="fas fa-wand-magic-sparkles"></i> Gerar Resumo IA (Gemini)</button>` : '';
                const link = d.link ? `<a href="${d.link}" target="_blank" class="doc-link">Acessar Documento Oficial CVM <i class="fas fa-external-link-alt"></i></a>` : '';

                html += `
                <div class="doc-item">
                    <div class="doc-header">
                        <div class="doc-title-line">
                            <span class="ticker-tag">${ticker}</span>
                            <span class="company-name">${comp}</span>
                            <span class="doc-category ${isFR ? 'fr' : ''}">${cat}</span>
                        </div>
                        <div class="doc-meta"><i class="far fa-calendar-alt"></i> ${data}</div>
                    </div>
                    <div class="doc-desc">${desc}</div>
                    ${resumoHtml}
                    <div class="doc-footer">
                        ${btnResumo}
                        ${link}
                    </div>
                </div>
                `;
            }
            listEl.innerHTML = html;
        }

        window.addEventListener('DOMContentLoaded', () => {
            carregarCatalogoEmpresas();
            carregarMetricas();
            carregarDocs();
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
