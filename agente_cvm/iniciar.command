#!/bin/bash

# Direcionar para a pasta do script
cd "$(dirname "$0")"

echo "====================================================================="
echo "         INICIANDO AMBIENTE DO AGENTE CVM & RI (macOS)"
echo "====================================================================="
echo ""

# Verificar se o venv existe, senao criar
if [ ! -d "venv" ]; then
    echo "[Setup] Criando ambiente virtual Python (venv)..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[Erro] Nao foi possivel criar o venv. Verifique o Python 3."
        read -p "Pressione Enter para sair..."
        exit 1
    fi
fi

# Ativar venv e instalar dependencias
echo "[Setup] Ativando venv..."
source venv/bin/activate

echo "[Setup] Instalando/Atualizando dependencias do requirements.txt..."
python3 -m pip install --upgrade pip -q
pip3 install -r requirements.txt

# Garantir existencia do arquivo .env
if [ ! -f ".env" ]; then
    echo "[Setup] Criando arquivo .env a partir de .env.example..."
    cp .env.example .env
    echo "[Alerta] Por favor, configure suas chaves do Telegram e Gemini no arquivo .env!"
fi

echo ""
echo "====================================================================="
echo "         INICIANDO AGENTE & DASHBOARD HTTP"
echo "====================================================================="
echo ""

# Executar o agente
python3 agente.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[Erro] O agente parou com falha."
    read -p "Pressione Enter para fechar..."
fi
