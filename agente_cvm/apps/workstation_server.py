import os
import sys
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

PORT = 8004

def obter_caminho_workstation():
    paths = [
        os.path.join(PROJECT_DIR, "Mira", "ai_studio_code (28) (3).html"),
        os.path.join(PROJECT_DIR, "ai_studio_code (28) (3).html"),
        os.path.join(AGENTE_DIR, "Mira", "ai_studio_code (28) (3).html")
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]

class WorkstationHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path in ["/", "/index.html"]:
            file_path = obter_caminho_workstation()
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>Arquivo ai_studio_code (28) (3).html nao encontrado.</h1>")
                
        elif parsed.path == "/LOGO_CF.png":
            self.serve_logo()
            
        elif parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "app": "workstation"}')
            
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

def iniciar_servidor(port=PORT):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, WorkstationHandler)
    print(f"[Workstation Server] Gregori Markets ativo em http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    iniciar_servidor()
