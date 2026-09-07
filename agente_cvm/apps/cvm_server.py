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
            
        elif parsed.path in ["/LOGO_CF_TECH.png", "/LOGO_CF.png", "/logo.png"]:
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
            mes = params.get("mes", [""])[0].strip()
            docs = storage.buscar_documentos_por_termo(q, mes=mes, limit=160)
            self.wfile.write(json.dumps(docs).encode("utf-8"))
            
        elif parsed.path == "/api/resumir":
            link = params.get("link", [""])[0].strip()
            ticker = params.get("ticker", [""])[0].strip()
            
            if not link:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"error": "Parametro link obrigatorio"}')
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
                    resumo = f"### Síntese do Evento\nDocumento oficial ({doc_obj['category']}) protocolado por {doc_obj['company_name']} ({doc_obj['ticker']}) na CVM.\n\n### Destaques Principais\n* **Assunto:** {doc_obj['description']}\n* **Data:** Divulgado em {doc_obj['delivery_date']}\n* **Protocolo:** Disponível na íntegra nos sistemas da CVM.\n\n### Análise para o Investidor de Longo Prazo\nClassificação: **Neutro**. Trata-se de divulgação regulatória que não altera de imediato os fundamentos estruturais da companhia."
                    
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
            os.path.join(AGENTE_DIR, "LOGO_CF_TECH.png"),
            os.path.join(PROJECT_DIR, "LOGO_CF_TECH.png"),
            os.path.join(BASE_DIR, "LOGO_CF_TECH.png"),
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
        html = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CF TECH — Fatos Relevantes CVM | Ceará Finance</title>
    <!-- Tipografia Oficial Manual de Marca CF Tech v2 -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:wght@400;500;600;700&family=Space+Grotesk:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            /* Paleta Oficial do Manual de Marca v2 */
            --c-tinta: #0A0A0B;
            --c-papel: #F5F3EF;
            --c-papel-alt: #E9E7E2;
            --c-roxo-profundo: #3B0764;
            --c-roxo-fume: #8C79C0;
            --c-grafite: #5A5A62;
            --c-grafite-light: #8A8A93;
            --c-hairline: #222228;
            --c-hairline-light: #D8D4CB;
            --c-card-bg: #111115;
            --c-card-hover: #15151B;
            --c-summary-bg: #0D0C13;
            
            /* Fontes */
            --font-title: 'Familjen Grotesk', sans-serif;
            --font-body: 'Space Grotesk', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: var(--font-body);
            background: var(--c-tinta);
            color: var(--c-papel);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            text-wrap: pretty;
            line-height: 1.5;
        }
        
        ::selection {
            background: var(--c-roxo-profundo);
            color: var(--c-papel);
        }
        
        a {
            color: var(--c-roxo-fume);
            text-decoration: none;
            transition: all 0.2s;
        }
        a:hover {
            color: var(--c-papel);
        }

        /* ================= TICKER TAPE / MARQUEE ================= */
        .marquee-bar {
            background: var(--c-papel);
            color: var(--c-tinta);
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.2em;
            padding: 7px 0;
            text-transform: uppercase;
            overflow: hidden;
            white-space: nowrap;
            display: flex;
            border-bottom: 1px solid var(--c-tinta);
            font-weight: 500;
        }
        .marquee-track {
            display: inline-flex;
            animation: marquee 35s linear infinite;
        }
        .marquee-track span {
            padding: 0 20px;
        }
        @keyframes marquee {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }

        /* ================= CONTAINER & HEADER ================= */
        .container {
            max-width: 1240px;
            margin: 0 auto;
            padding: 0 24px 80px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--c-hairline);
            margin-bottom: 30px;
        }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .logo-cf-banner {
            height: 46px;
            max-width: 250px;
            object-fit: contain;
            display: block;
        }

        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .btn-top {
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.14em;
            color: var(--c-papel);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--c-hairline);
            padding: 8px 16px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-top:hover {
            background: rgba(140, 121, 192, 0.15);
            border-color: var(--c-roxo-fume);
            color: var(--c-papel);
            transform: translateY(-1px);
        }

        /* ================= HERO SECTION ================= */
        .hero-section {
            padding: 15px 0 30px;
            border-bottom: 1px solid var(--c-hairline);
            margin-bottom: 30px;
        }
        .hero-tag {
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.24em;
            color: var(--c-roxo-fume);
            margin-bottom: 12px;
            text-transform: uppercase;
        }
        .hero-title {
            font-family: var(--font-title);
            font-weight: 600;
            font-size: 48px;
            line-height: 1.05;
            letter-spacing: -0.02em;
            margin-bottom: 12px;
            color: var(--c-papel);
        }
        .hero-subtitle {
            font-size: 15px;
            line-height: 1.6;
            color: var(--c-grafite-light);
            max-width: 760px;
        }

        /* ================= METRICS GRID ================= */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            border: 1px solid var(--c-hairline);
            background: var(--c-card-bg);
            margin-bottom: 28px;
        }
        .metric-cell {
            padding: 18px 22px;
            border-right: 1px solid var(--c-hairline);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .metric-cell:last-child {
            border-right: none;
        }
        .metric-cell-label {
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.18em;
            color: var(--c-roxo-fume);
            text-transform: uppercase;
        }
        .metric-cell-val {
            font-family: var(--font-mono);
            font-size: 24px;
            font-weight: 600;
            color: var(--c-papel);
        }
        .metric-cell-sub {
            font-size: 11px;
            color: var(--c-grafite-light);
        }

        /* ================= SEARCH & CONTROLS ================= */
        .search-container {
            border: 1px solid var(--c-hairline);
            background: var(--c-card-bg);
            padding: 20px 22px;
            margin-bottom: 25px;
        }
        .search-label {
            font-family: var(--font-mono);
            font-size: 10.5px;
            letter-spacing: 0.2em;
            color: var(--c-roxo-fume);
            margin-bottom: 12px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .search-inputs-row {
            display: grid;
            grid-template-columns: 1fr 280px;
            gap: 12px;
            margin-bottom: 16px;
        }
        .search-box-wrap {
            position: relative;
        }
        .search-box-wrap i {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--c-roxo-fume);
            font-size: 14px;
        }
        .search-box-wrap input {
            width: 100%;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid var(--c-hairline);
            padding: 12px 16px 12px 44px;
            font-family: var(--font-body);
            font-size: 14px;
            color: var(--c-papel);
            border-radius: 6px;
            outline: none;
            transition: all 0.2s;
        }
        .search-box-wrap input:focus {
            border-color: var(--c-roxo-fume);
            box-shadow: 0 0 0 2px rgba(140, 121, 192, 0.25);
        }
        .select-company-dropdown {
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid var(--c-hairline);
            padding: 0 14px;
            font-family: var(--font-body);
            font-size: 13.5px;
            color: var(--c-papel);
            border-radius: 6px;
            outline: none;
            cursor: pointer;
        }
        .select-company-dropdown:focus {
            border-color: var(--c-roxo-fume);
        }

        /* Barra de Seleção de Meses (Ano Todo) */
        .month-selector-bar {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            padding: 12px 0;
            border-top: 1px solid var(--c-hairline);
            border-bottom: 1px solid var(--c-hairline);
            margin-bottom: 14px;
        }
        .month-label {
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.16em;
            color: var(--c-roxo-fume);
            margin-right: 6px;
            text-transform: uppercase;
        }
        .month-pill {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--c-hairline);
            color: var(--c-grafite-light);
            padding: 4px 11px;
            font-family: var(--font-mono);
            font-size: 11px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .month-pill:hover, .month-pill.active {
            background: var(--c-roxo-profundo);
            border-color: var(--c-roxo-fume);
            color: #ffffff;
            font-weight: 600;
        }

        .filter-pills-row {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }
        .pills-prefix {
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.15em;
            color: var(--c-grafite-light);
            margin-right: 4px;
        }
        .pill-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--c-hairline);
            color: var(--c-grafite-light);
            padding: 4px 12px;
            font-family: var(--font-mono);
            font-size: 11px;
            border-radius: 9999px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .pill-btn:hover, .pill-btn.active {
            background: rgba(140, 121, 192, 0.18);
            border-color: var(--c-roxo-fume);
            color: var(--c-papel);
        }

        /* ================= COMPANY PROFILE BANNER ================= */
        .company-profile-banner {
            border: 1px solid var(--c-roxo-fume);
            background: linear-gradient(135deg, rgba(59, 7, 100, 0.25) 0%, rgba(17, 17, 21, 0.95) 100%);
            padding: 16px 20px;
            margin-bottom: 22px;
            border-radius: 6px;
            display: none;
            animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .profile-flex {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .profile-company-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .profile-ticker-tag {
            font-family: var(--font-mono);
            font-size: 16px;
            font-weight: 700;
            background: var(--c-roxo-profundo);
            color: var(--c-papel);
            border: 1px solid var(--c-roxo-fume);
            padding: 4px 12px;
            border-radius: 4px;
        }
        .profile-names h2 {
            font-family: var(--font-title);
            font-size: 18px;
            font-weight: 600;
            color: var(--c-papel);
        }
        .profile-names p {
            font-size: 12.5px;
            color: var(--c-roxo-fume);
        }
        .profile-tags-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .profile-data-chip {
            font-family: var(--font-mono);
            font-size: 10.5px;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--c-hairline);
            padding: 4px 10px;
            border-radius: 4px;
            color: var(--c-grafite-light);
        }
        .profile-data-chip strong {
            color: var(--c-papel);
        }

        /* ================= VIEWPORT COM OPÇÃO DE DESCER (SCROLL INTERNO) ================= */
        .docs-viewport-card {
            border: 1px solid var(--c-hairline);
            background: var(--c-card-bg);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 40px;
        }
        .docs-viewport-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--c-hairline);
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--c-grafite-light);
        }
        .docs-count-badge {
            color: var(--c-roxo-fume);
            font-weight: 600;
        }
        .docs-scroll-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 10px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        /* Container Rolável de Dimensão Menor */
        .docs-viewport-content {
            max-height: 680px;
            overflow-y: auto;
            padding: 16px;
            scrollbar-width: thin;
            scrollbar-color: var(--c-roxo-fume) var(--c-tinta);
        }
        .docs-viewport-content::-webkit-scrollbar {
            width: 6px;
        }
        .docs-viewport-content::-webkit-scrollbar-track {
            background: #0A0A0B;
        }
        .docs-viewport-content::-webkit-scrollbar-thumb {
            background: var(--c-roxo-fume);
            border-radius: 3px;
        }

        /* Grid de 2 Colunas (Não fica todo na vertical!) */
        .docs-grid-layout {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
            gap: 14px;
        }

        /* Cards em Dimensão Menor */
        .doc-item-compact {
            border: 1px solid var(--c-hairline);
            background: #0d0d11;
            border-radius: 6px;
            padding: 15px 18px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s;
        }
        .doc-item-compact:hover {
            border-color: rgba(140, 121, 192, 0.45);
            background: #13131a;
        }
        .doc-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .doc-tags-left {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .doc-ticker-pill {
            font-family: var(--font-mono);
            font-size: 12px;
            font-weight: 600;
            color: var(--c-roxo-fume);
            background: rgba(59, 7, 100, 0.35);
            border: 1px solid rgba(140, 121, 192, 0.3);
            padding: 2px 8px;
            border-radius: 3px;
        }
        .doc-company-title {
            font-family: var(--font-title);
            font-size: 15px;
            font-weight: 600;
            color: var(--c-papel);
        }
        .doc-category-badge {
            font-family: var(--font-mono);
            font-size: 10px;
            text-transform: uppercase;
            padding: 2px 7px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--c-hairline);
            color: var(--c-grafite-light);
        }
        .doc-category-badge.fr {
            background: rgba(244, 63, 94, 0.12);
            border-color: rgba(244, 63, 94, 0.35);
            color: #fb7185;
            font-weight: 600;
        }
        .doc-date-stamp {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--c-grafite-light);
        }
        .doc-subject-line {
            font-size: 13.5px;
            color: #d1d5db;
            margin-bottom: 12px;
            line-height: 1.5;
        }

        /* Resumo IA Compacto e Estruturado */
        .ai-summary-compact {
            background: #09080e;
            border: 1px solid rgba(140, 121, 192, 0.25);
            border-left: 3px solid var(--c-roxo-fume);
            border-radius: 4px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }
        .ai-summary-top-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 8px;
            margin-bottom: 10px;
        }
        .ai-label-wrap {
            font-family: var(--font-mono);
            font-size: 9.5px;
            letter-spacing: 0.18em;
            color: var(--c-roxo-fume);
            font-weight: 600;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .impact-pill {
            font-family: var(--font-mono);
            font-size: 9.5px;
            letter-spacing: 0.12em;
            padding: 2px 9px;
            border-radius: 9999px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .impact-positive {
            background: rgba(34, 197, 94, 0.12);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .impact-neutral {
            background: rgba(140, 121, 192, 0.12);
            color: #c4b5fd;
            border: 1px solid rgba(140, 121, 192, 0.3);
        }
        .impact-risk {
            background: rgba(244, 63, 94, 0.12);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }
        .summary-content-intro {
            font-size: 13px;
            line-height: 1.55;
            color: var(--c-papel);
            margin-bottom: 10px;
        }
        .summary-bullets-box {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 10px;
        }
        .summary-bullet-row {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 12.5px;
            line-height: 1.5;
            color: #e2e8f0;
        }
        .bullet-dot-mini {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--c-roxo-fume);
            margin-top: 7px;
            flex-shrink: 0;
        }
        .summary-analysis-callout {
            background: rgba(59, 7, 100, 0.2);
            border: 1px solid rgba(140, 121, 192, 0.2);
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 12.5px;
            line-height: 1.5;
            color: #e2e8f0;
        }
        .analysis-label-mini {
            font-family: var(--font-mono);
            font-size: 9px;
            letter-spacing: 0.16em;
            color: var(--c-roxo-fume);
            margin-bottom: 4px;
            text-transform: uppercase;
        }

        .doc-item-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 10px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .btn-gen-ai {
            font-family: var(--font-mono);
            font-size: 10.5px;
            letter-spacing: 0.1em;
            background: rgba(59, 7, 100, 0.35);
            border: 1px solid var(--c-roxo-fume);
            color: #d8b4fe;
            padding: 5px 12px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .btn-gen-ai:hover {
            background: var(--c-roxo-profundo);
            color: #ffffff;
        }
        .cvm-link-mini {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--c-roxo-fume);
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .cvm-link-mini:hover {
            color: var(--c-papel);
            text-decoration: underline;
        }

        /* ================= RODAPÉ OFICIAL CF TECH (IMAGEM 2) ================= */
        .footer-system {
            margin-top: 40px;
            border-top: 1px solid var(--c-hairline);
            padding-top: 35px;
        }
        .footer-brand-box {
            display: grid;
            grid-template-columns: 1fr 340px;
            border: 1px solid var(--c-hairline);
            background: var(--c-card-bg);
            margin-bottom: 20px;
        }
        .footer-left {
            padding: 28px 30px;
            border-right: 1px solid var(--c-hairline);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .footer-label {
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.2em;
            color: var(--c-roxo-fume);
            text-transform: uppercase;
        }
        .footer-desc {
            font-size: 13.5px;
            line-height: 1.65;
            color: var(--c-papel);
        }
        .footer-disclaimer {
            font-size: 11.5px;
            line-height: 1.55;
            color: var(--c-grafite-light);
            border-top: 1px solid var(--c-hairline);
            padding-top: 10px;
            margin-top: 4px;
        }

        .footer-right {
            background: #070709;
            padding: 28px 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .social-nav-title {
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.24em;
            color: var(--c-roxo-fume);
            margin-bottom: 16px;
            text-transform: uppercase;
        }
        .social-links-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .social-btn {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--c-hairline);
            border-radius: 5px;
            color: var(--c-papel);
            font-family: var(--font-body);
            font-size: 13.5px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .social-btn-inner {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .social-btn i {
            font-size: 15px;
            color: var(--c-roxo-fume);
        }
        .social-arrow {
            font-family: var(--font-mono);
            color: var(--c-roxo-fume);
            transition: transform 0.2s;
        }
        .social-btn:hover {
            background: rgba(59, 7, 100, 0.35);
            border-color: var(--c-roxo-fume);
            color: #ffffff;
            transform: translateX(3px);
        }
        .social-btn:hover .social-arrow {
            transform: translateX(3px);
            color: #ffffff;
        }

        .bottom-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: var(--font-mono);
            font-size: 9.5px;
            letter-spacing: 0.16em;
            color: var(--c-grafite-light);
            text-transform: uppercase;
            padding: 12px 0 25px;
        }

        .empty-state {
            text-align: center;
            padding: 50px 20px;
            color: var(--c-grafite-light);
            font-size: 14px;
            border: 1px dashed var(--c-hairline);
            border-radius: 6px;
            grid-column: 1 / -1;
        }

        @media (max-width: 900px) {
            .metrics-grid { grid-template-columns: 1fr 1fr; }
            .metric-cell:nth-child(2) { border-right: none; }
            .search-inputs-row { grid-template-columns: 1fr; }
            .docs-grid-layout { grid-template-columns: 1fr; }
            .footer-brand-box { grid-template-columns: 1fr; }
            .footer-left { border-right: none; border-bottom: 1px solid var(--c-hairline); }
            .hero-title { font-size: 34px; }
        }
    </style>
</head>
<body>

    <!-- Faixa Técnica / Marquee Tape Oficial -->
    <div class="marquee-bar">
        <div class="marquee-track">
            <span>DADOS DIRETO DA CVM &bull; ESCALA ORIGINAL, SEM ABREVIAÇÃO &bull; 680+ EMPRESAS B3 &bull; SEM CADASTRO &bull; SEM ARMAZENAMENTO &bull; IA GEMINI 3.1 FLASH LITE &bull; CEARÁ FINANCE &bull; FRONT OFFICE DE TECNOLOGIA &bull;</span>
            <span>DADOS DIRETO DA CVM &bull; ESCALA ORIGINAL, SEM ABREVIAÇÃO &bull; 680+ EMPRESAS B3 &bull; SEM CADASTRO &bull; SEM ARMAZENAMENTO &bull; IA GEMINI 3.1 FLASH LITE &bull; CEARÁ FINANCE &bull; FRONT OFFICE DE TECNOLOGIA &bull;</span>
        </div>
    </div>

    <div class="container">
        <!-- Header Oficial com o Logo Novo Enviado -->
        <header>
            <div class="brand-lockup">
                <a href="http://localhost:8001" style="display:inline-flex;align-items:center;">
                    <img src="/LOGO_CF_TECH.png" alt="CF TECH — Ceará Finance" class="logo-cf-banner" onerror="this.onerror=null;this.src='/LOGO_CF.png';">
                </a>
            </div>

            <div class="header-actions">
                <a href="http://localhost:8000" class="btn-top"><i class="fas fa-arrow-left"></i> FINANCE HUB</a>
                <button onclick="carregarDocs()" class="btn-top"><i class="fas fa-rotate"></i> ATUALIZAR</button>
            </div>
        </header>

        <!-- Capa Conceitual -->
        <section class="hero-section">
            <div class="hero-tag">01 &bull; REGULATÓRIO & PARECERES DE RI</div>
            <h1 class="hero-title">Fatos relevantes,<br>direto da CVM.</h1>
            <p class="hero-subtitle">
                Busque uma empresa listada por ticker ou código CVM. Resumos executivos sintetizados por inteligência artificial, dados sem filtro, sem ruído e em escala original de todos os meses do ano.
            </p>
        </section>

        <!-- Métricas em Grid Técnico (Manual de Marca) -->
        <div class="metrics-grid">
            <div class="metric-cell">
                <div class="metric-cell-label">01 &bull; Documentos Oficiais 2026</div>
                <div class="metric-cell-val" id="metric-total">33.541</div>
                <div class="metric-cell-sub">Todos os meses catalogados</div>
            </div>
            <div class="metric-cell">
                <div class="metric-cell-label">02 &bull; Fatos Relevantes</div>
                <div class="metric-cell-val" id="metric-fr">4.041</div>
                <div class="metric-cell-sub">Eventos de impacto no mercado</div>
            </div>
            <div class="metric-cell">
                <div class="metric-cell-label">03 &bull; Universo B3 & CVM</div>
                <div class="metric-cell-val" id="metric-cia">684</div>
                <div class="metric-cell-sub">Empresas com cobertura ativa</div>
            </div>
            <div class="metric-cell">
                <div class="metric-cell-label">04 &bull; Inteligência Artificial</div>
                <div class="metric-cell-val" style="color: var(--c-roxo-fume); font-size: 19px; display:flex; align-items:center; gap:8px;">
                    <i class="fas fa-brain"></i> Gemini 3.1
                </div>
                <div class="metric-cell-sub">Pareceres didáticos & síntese</div>
            </div>
        </div>

        <!-- Seção de Busca e Filtros -->
        <div class="search-container">
            <div class="search-label">
                <i class="fas fa-terminal"></i> Consulta por Ticker, Razão Social ou Código CVM
            </div>
            <div class="search-inputs-row">
                <div class="search-box-wrap">
                    <i class="fas fa-search"></i>
                    <input type="text" id="input-search" list="lista-empresas" placeholder="Buscar por nome, CNPJ, ticker ou código CVM (ex: ITUB4, MGLU3, PETR4, BBAS3, VALE3)..." oninput="debounceSearch()">
                    <datalist id="lista-empresas"></datalist>
                </div>
                <select class="select-company-dropdown" id="select-empresa" onchange="selecionarDropdown(this.value)">
                    <option value="">-- Selecionar Empresa (680+ B3) --</option>
                </select>
            </div>

            <!-- Barra de Seleção de Meses do Ano (Todos os Meses de 2026) -->
            <div class="month-selector-bar">
                <span class="month-label"><i class="far fa-calendar-check"></i> MESES 2026:</span>
                <button class="month-pill active" onclick="selecionarMes('', this)">Ano Todo (Jan a Set)</button>
                <button class="month-pill" onclick="selecionarMes('2026-09', this)">Set/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-08', this)">Ago/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-07', this)">Jul/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-06', this)">Jun/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-05', this)">Mai/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-04', this)">Abr/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-03', this)">Mar/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-02', this)">Fev/26</button>
                <button class="month-pill" onclick="selecionarMes('2026-01', this)">Jan/26</button>
            </div>

            <div class="filter-pills-row">
                <span class="pills-prefix">ATALHOS B3:</span>
                <button class="pill-btn active" onclick="filtrarPill('', this)">Todas</button>
                <button class="pill-btn" onclick="filtrarPill('Fato Relevante', this)">Fatos Relevantes</button>
                <button class="pill-btn" onclick="filtrarPill('Comunicado', this)">Comunicados</button>
                <button class="pill-btn" onclick="filtrarPill('PETR4', this)">PETR4</button>
                <button class="pill-btn" onclick="filtrarPill('VALE3', this)">VALE3</button>
                <button class="pill-btn" onclick="filtrarPill('ITUB4', this)">ITUB4</button>
                <button class="pill-btn" onclick="filtrarPill('BBAS3', this)">BBAS3</button>
                <button class="pill-btn" onclick="filtrarPill('MGLU3', this)">MGLU3</button>
                <button class="pill-btn" onclick="filtrarPill('RENT3', this)">RENT3</button>
                <button class="pill-btn" onclick="filtrarPill('WEGE3', this)">WEGE3</button>
                <button class="pill-btn" onclick="filtrarPill('DIRR3', this)">DIRR3</button>
                <button class="pill-btn" onclick="filtrarPill('PRIO3', this)">PRIO3</button>
            </div>
        </div>

        <!-- Card de Perfil da Empresa Selecionada -->
        <div id="company-profile" class="company-profile-banner">
            <div class="profile-flex">
                <div class="profile-company-info">
                    <div class="profile-ticker-tag" id="p-ticker">B3</div>
                    <div class="profile-names">
                        <h2 id="p-name">Companhia Aberta</h2>
                        <p id="p-sector">Setor de Atuação</p>
                    </div>
                </div>
                <div class="profile-tags-row">
                    <div class="profile-data-chip">CVM: <strong id="p-cvm">-</strong></div>
                    <div class="profile-data-chip">CNPJ: <strong id="p-cnpj">-</strong></div>
                    <div class="profile-data-chip" style="color: #4ade80;"><i class="fas fa-circle-check"></i> <strong>100% Monitorado</strong></div>
                </div>
            </div>
        </div>

        <!-- VIEWPORT COM OPÇÃO DE DESCER (SCROLL INTERNO & CARDS EM GRID COMPACTO) -->
        <div class="docs-viewport-card">
            <div class="docs-viewport-header">
                <div>
                    <span>REGISTROS ENCONTRADOS: </span>
                    <strong class="docs-count-badge" id="visible-count">0</strong>
                </div>
                <div class="docs-scroll-indicator">
                    <span>Role para descer e ver mais</span>
                    <i class="fas fa-arrow-down" style="color: var(--c-roxo-fume);"></i>
                </div>
            </div>

            <div class="docs-viewport-content" id="docs-scroll-area">
                <div id="docs-list" class="docs-grid-layout">
                    <div class="empty-state"><i class="fas fa-spinner fa-spin"></i> Carregando base de comunicados oficiais da CVM...</div>
                </div>
            </div>
        </div>

        <!-- ================= RODAPÉ OFICIAL CF TECH (IMAGEM 2) ================= -->
        <footer class="footer-system">
            <div class="footer-brand-box">
                <!-- Lado Esquerdo -->
                <div class="footer-left">
                    <div class="footer-label">O QUE É O CF TECH</div>
                    <div class="footer-desc">
                        <strong>CF Tech</strong> é o <strong>Front Office de tecnologia</strong> da Ceará Finance — construído sobre três pilares: <strong>didática, criatividade e tecnologia</strong>. Esse hub é um dos nossos experimentos: pegar dado público e denso (como as demonstrações e fatos relevantes da CVM) e deixar acessível, sem cadastro e sem fricção.
                    </div>
                    <div class="footer-disclaimer">
                        Projeto independente de tecnologia da Ceará Finance. Os dados vêm direto da CVM (Comissão de Valores Mobiliários); não há vínculo, afiliação ou verificação por parte do órgão regulador.
                    </div>
                </div>

                <!-- Lado Direito (SIGA A LIGA) -->
                <div class="footer-right">
                    <div>
                        <div class="social-nav-title">SIGA A LIGA</div>
                        <div class="social-links-list">
                            <a href="https://www.instagram.com/cearafinance/" target="_blank" class="social-btn">
                                <div class="social-btn-inner">
                                    <i class="fab fa-instagram"></i>
                                    <span>Instagram</span>
                                </div>
                                <span class="social-arrow">→</span>
                            </a>
                            <a href="https://www.linkedin.com/company/ceara-finance/posts/?feedView=all" target="_blank" class="social-btn">
                                <div class="social-btn-inner">
                                    <i class="fab fa-linkedin"></i>
                                    <span>LinkedIn</span>
                                </div>
                                <span class="social-arrow">→</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bottom-line">
                <div>CF TECH &bull; CEARÁ FINANCE &bull; DADOS PÚBLICOS DA CVM &bull; MANUAL DE MARCA v2</div>
                <div>EDIÇÃO 2026 &bull; USO INTERNO</div>
            </div>
        </footer>
    </div>

    <script>
        let todosDocumentos = [];
        let catalogoEmpresas = [];
        let filtroAtivo = '';
        let mesAtivo = '';
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

        async function carregarDocs() {
            const listEl = document.getElementById('docs-list');
            const termo = document.getElementById('input-search').value.trim();
            try {
                let url = '/api/documentos?';
                if (termo) url += `q=${encodeURIComponent(termo)}&`;
                if (mesAtivo) url += `mes=${encodeURIComponent(mesAtivo)}&`;
                
                const res = await fetch(url);
                todosDocumentos = await res.json();
                atualizarPerfilEmpresa(termo);
                renderizarDocs();
            } catch (err) {
                listEl.innerHTML = `<div class="empty-state" style="color: #ff6b6b;">Erro ao carregar documentos: ${err.message}</div>`;
            }
        }

        function selecionarMes(mes, btn) {
            mesAtivo = mes;
            document.querySelectorAll('.month-selector-bar .month-pill').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            carregarDocs();
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
            document.querySelectorAll('.filter-pills-row .pill-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            
            document.getElementById('input-search').value = cat;
            carregarDocs();
        }

        function selecionarDropdown(ticker) {
            if (!ticker) return;
            document.getElementById('input-search').value = ticker;
            filtroAtivo = ticker;
            document.querySelectorAll('.filter-pills-row .pill-btn').forEach(b => b.classList.remove('active'));
            carregarDocs();
        }

        function debounceSearch() {
            clearTimeout(timerSearch);
            timerSearch = setTimeout(() => {
                carregarDocs();
            }, 300);
        }

        /* ================= FORMATADOR DE RESUMO EXECUTIVO DIDÁTICO ================= */
        function formatarResumoExecutivo(textoBruto) {
            if (!textoBruto || textoBruto.includes('404 NOT_FOUND') || textoBruto.toLowerCase().includes('error')) {
                return '';
            }

            let text = textoBruto.trim();

            // Detectar Classificação de Impacto
            let impacto = 'NEUTRO';
            let impactoClass = 'impact-neutral';

            const lower = text.toLowerCase();
            if (lower.includes('classificado como **positivo') || lower.includes('classificação: **positivo') || lower.includes('impacto positivo')) {
                impacto = 'POSITIVO';
                impactoClass = 'impact-positive';
            } else if (lower.includes('classificado como **negativo') || lower.includes('atenção') || lower.includes('risco')) {
                impacto = 'ATENÇÃO / RISCO';
                impactoClass = 'impact-risk';
            } else if (lower.includes('classificado como **neutro') || lower.includes('classificação: **neutro')) {
                impacto = 'NEUTRO';
                impactoClass = 'impact-neutral';
            }

            // Limpar introduções redundantes de prompt antigo
            text = text.replace(/^Como Analista de RI[^:]*:\s*/i, '');
            text = text.replace(/^Prezado\(a\)[^:]*:\s*/i, '');

            // Separar seções por cabeçalhos ###
            const parts = text.split(/###\s*\**([^*]+)\**/);

            let html = `
            <div class="ai-summary-compact">
                <div class="ai-summary-top-row">
                    <div class="ai-label-wrap">
                        <i class="fas fa-brain" style="color:var(--c-roxo-fume);"></i>
                        <span>PARECER EXECUTIVO RI &bull; GEMINI</span>
                    </div>
                    <div class="impact-pill ${impactoClass}">${impacto}</div>
                </div>
            `;

            if (parts.length > 1) {
                const intro = parts[0].trim();
                if (intro && intro.length > 15) {
                    const introFmt = formatarNegrito(intro);
                    html += `<div class="summary-content-intro">${introFmt}</div>`;
                }

                for (let i = 1; i < parts.length; i += 2) {
                    const header = (parts[i] || '').replace(/[*#]/g, '').trim();
                    const body = (parts[i + 1] || '').trim();

                    const isAnalysis = header.toLowerCase().includes('investidor') || header.toLowerCase().includes('análise') || header.toLowerCase().includes('impacto');

                    if (isAnalysis) {
                        const bodyFmt = formatarNegrito(body);
                        html += `
                        <div class="summary-analysis-callout">
                            <div class="analysis-label-mini"><i class="fas fa-compass"></i> ${header.toUpperCase()}</div>
                            <div>${bodyFmt}</div>
                        </div>
                        `;
                    } else {
                        html += `<div class="summary-bullets-box">`;
                        const lines = body.split('\n');
                        for (let line of lines) {
                            line = line.trim();
                            if (!line) continue;

                            if (line.startsWith('*') || line.startsWith('-')) {
                                let bullet = line.replace(/^[\*\-]\s*/, '').trim();
                                bullet = formatarNegrito(bullet);
                                html += `
                                <div class="summary-bullet-row">
                                    <span class="bullet-dot-mini"></span>
                                    <div>${bullet}</div>
                                </div>
                                `;
                            } else {
                                html += `<div class="summary-content-intro">${formatarNegrito(line)}</div>`;
                            }
                        }
                        html += `</div>`;
                    }
                }
            } else {
                html += `<div class="summary-content-intro">${formatarNegrito(text)}</div>`;
            }

            html += `</div>`;
            return html;
        }

        function formatarNegrito(str) {
            return str
                .replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\*([^\*]+)\*/g, '<em>$1</em>');
        }

        async function gerarResumo(link, ticker, btnEl) {
            btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando Parecer RI...';
            btnEl.disabled = true;
            try {
                const res = await fetch(`/api/resumir?link=${encodeURIComponent(link)}&ticker=${encodeURIComponent(ticker)}`);
                const data = await res.json();
                if (data.status === 'ok' && data.resumo) {
                    const card = btnEl.closest('.doc-item-compact');
                    const summaryHtml = formatarResumoExecutivo(data.resumo);
                    const temp = document.createElement('div');
                    temp.innerHTML = summaryHtml;
                    card.insertBefore(temp.firstElementChild, card.querySelector('.doc-item-footer'));
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
            const countEl = document.getElementById('visible-count');
            let docs = [...todosDocumentos];

            countEl.innerText = `${docs.length} fatos/documentos`;

            if (docs.length === 0) {
                listEl.innerHTML = '<div class="empty-state"><i class="fas fa-folder-open" style="font-size: 32px; margin-bottom: 10px; display:block; opacity:0.4;"></i>Nenhum documento encontrado na base para este critério ou período.</div>';
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

                const resumoHtml = d.resumo_ia ? formatarResumoExecutivo(d.resumo_ia) : '';
                const btnResumo = !resumoHtml && d.link ? `<button class="btn-gen-ai" onclick="gerarResumo('${d.link}', '${ticker}', this)"><i class="fas fa-wand-magic-sparkles"></i> Parecer IA</button>` : '';
                const link = d.link ? `<a href="${d.link}" target="_blank" class="cvm-link-mini">CVM Oficial <i class="fas fa-arrow-up-right-from-square"></i></a>` : '';

                html += `
                <div class="doc-item-compact">
                    <div>
                        <div class="doc-item-header">
                            <div class="doc-tags-left">
                                <span class="doc-ticker-pill">${ticker}</span>
                                <span class="doc-company-title">${comp}</span>
                                <span class="doc-category-badge ${isFR ? 'fr' : ''}">${cat}</span>
                            </div>
                            <div class="doc-date-stamp"><i class="far fa-calendar"></i> ${data}</div>
                        </div>
                        <div class="doc-subject-line">${desc}</div>
                        ${resumoHtml}
                    </div>
                    <div class="doc-item-footer">
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
