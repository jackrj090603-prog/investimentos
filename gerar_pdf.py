import os
import subprocess
import sys

def compilar_relatorio_pdf():
    print("[PDF] Iniciando compilação do relatório...")
    
    try:
        import markdown
    except ImportError:
        print("[PDF] Biblioteca 'markdown' não encontrada. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
        import markdown
        
    md_path = "relatorio.md"
    html_path = "relatorio_final.html"
    pdf_path = "relatorio_final.pdf"
    
    if not os.path.exists(md_path):
        print(f"[PDF] Arquivo {md_path} não encontrado!")
        return
        
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    # Converter markdown para HTML
    html_body = markdown.markdown(md_content)
    
    # CSS Institucional Ceará Finance / Poli USP
    css_style = """
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'Outfit', 'Helvetica Neue', Arial, sans-serif;
            color: #111116;
            line-height: 1.6;
            font-size: 11pt;
            background: #ffffff;
            margin: 0;
            padding: 0;
        }
        h1, h2, h3, h4 {
            color: #000000;
            font-weight: 700;
            page-break-after: avoid;
        }
        h1 { font-size: 24pt; margin-top: 0; }
        h2 { font-size: 16pt; border-bottom: 1.5px solid #111116; padding-bottom: 5px; margin-top: 30px; }
        h3 { font-size: 13pt; margin-top: 20px; }
        p { margin-top: 0; margin-bottom: 15px; text-align: justify; }
        code {
            font-family: monospace;
            background: #f1f1f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9.5pt;
        }
        pre {
            background: #f1f1f4;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid #ddd;
        }
        pre code { padding: 0; background: none; }
        .page-break {
            page-break-before: always;
        }
        
        /* Capa Estilo Poli USP / Constellation Challenge */
        .cover {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            page-break-after: always;
            box-sizing: border-box;
            padding: 3cm 0;
        }
        .cover-header {
            border-bottom: 3px solid #000000;
            padding-bottom: 20px;
        }
        .cover-subtitle {
            font-size: 12pt;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #55555c;
            margin-bottom: 10px;
        }
        .cover-title {
            font-size: 32pt;
            font-weight: 900;
            line-height: 1.1;
            margin: 0;
            color: #000000;
        }
        .cover-meta {
            margin-top: auto;
            font-size: 11pt;
            line-height: 1.8;
        }
        .cover-logo-area {
            margin-top: 50px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
    </style>
    """
    
    # Estruturar HTML final com Capa
    data_atual = datetime.now().strftime("%d de %B de %Y")
    
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Relatório Técnico — Aegis Momentum LS</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&display=swap" rel="stylesheet">
    {css_style}
</head>
<body>

    <!-- CAPA INSTITUCIONAL -->
    <div class="cover">
        <div class="cover-header">
            <div class="cover-subtitle">Relatório Quantitativo de Investimentos</div>
            <h1 class="cover-title">AEGIS MOMENTUM<br>LONG-SHORT</h1>
        </div>
        
        <div class="cover-logo-area">
            <!-- SVG do Robô Mascote/Logo em Preto -->
            <svg viewBox="0 0 100 100" width="80" height="80">
                <circle cx="50" cy="50" r="48" fill="#000000"/>
                <path d="M72,42 C68,40 60,38 52,44 C48,47 43,45 38,40 C34,36 30,38 28,42 C24,48 26,56 32,60 C36,63 42,61 46,58 C49,60 52,62 55,62 C62,62 70,55 72,48 C73,46 73,44 72,42 Z" fill="#ffffff"/>
                <path d="M38,40 C36,36 32,32 25,32 C22,32 20,33 18,35 C23,38 28,42 30,46" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round"/>
                <path d="M48,36 C50,32 54,28 62,28 C65,28 68,29 70,31 C65,34 60,38 58,42" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round"/>
            </svg>
            <div>
                <div style="font-weight: 700; font-size: 14pt;">CEARÁ FINANCE</div>
                <div style="font-size: 10pt; color: #555;">Liga de Mercado Financeiro da UFC</div>
            </div>
        </div>
        
        <div class="cover-meta">
            <strong>Membro de Desenvolvimento:</strong> Jack Gregori Rodriguez Cachi<br>
            <strong>Mapeamento Acadêmico:</strong> Constellation Challenge / Poli USP Style<br>
            <strong>Código de Execução:</strong> Aegis Momentum LS Engine v1.0<br>
            <strong>Data de Compilação:</strong> {data_atual}
        </div>
    </div>

    <!-- CORPO DO RELATÓRIO -->
    <div class="report-body">
        {html_body}
    </div>

</body>
</html>
"""
    
    # Salvar arquivo HTML intermediário
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[PDF] HTML intermediário gerado com sucesso em: {html_path}")
    
    # Procurar o Google Chrome headless para compilar em PDF
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe",
        "chrome"  # se estiver no PATH
    ]
    
    chrome_exec = None
    for path in chrome_paths:
        if path == "chrome" or os.path.exists(path):
            chrome_exec = path
            break
            
    if chrome_exec:
        print(f"[PDF] Compilando HTML para PDF usando Chrome Headless em: {chrome_exec}...")
        try:
            cmd = [
                chrome_exec,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                "--no-sandbox",
                html_path
            ]
            subprocess.run(cmd, check=True)
            print(f"[PDF] Sucesso! Relatório PDF salvo em: {pdf_path}")
            return True
        except Exception as e:
            print(f"[PDF] Erro ao compilar com Google Chrome: {e}")
    else:
        print("[PDF] Google Chrome executável não encontrado para compilação headless.")
        
    print("[PDF] DICA: Você pode abrir o arquivo 'relatorio_final.html' no navegador e apertar Ctrl+P para salvar como PDF manualmente.")
    return False

if __name__ == "__main__":
    from datetime import datetime
    compilar_relatorio_pdf()
