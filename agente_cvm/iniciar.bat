@echo off
title Ceara Finance - Agente CVM
chcp 65001 > nul

echo =====================================================================
echo          INICIANDO AMBIENTE DO AGENTE CVM & RI
echo =====================================================================
echo.

:: Verificar se virtualenv existe, caso contrário criar
if not exist venv (
    echo [Setup] Criando ambiente virtual Python (venv)...
    python -m venv venv
    if errorlevel 1 (
        echo [Erro] Nao foi possivel criar o venv. Certifique-se de que o Python 3 esta instalado e no PATH.
        pause
        exit /b
    )
)

:: Ativar venv e instalar dependencias
echo [Setup] Ativando venv...
call venv\Scripts\activate.bat

echo [Setup] Instalando/Atualizando dependencias do requirements.txt...
python -m pip install --upgrade pip -q
pip install -r requirements.txt

:: Garantir existencia do arquivo .env
if not exist .env (
    echo [Setup] Criando arquivo .env a partir de .env.example...
    copy .env.example .env > nul
    echo [Alerta] Por favor, abra o arquivo .env e configure suas chaves do Telegram e Gemini!
)

echo.
echo =====================================================================
echo          INICIANDO AGENTE & DASHBOARD HTTP
echo =====================================================================
echo.

:: Executar o agente
python agente.py

if errorlevel 1 (
    echo.
    echo [Erro] O agente parou de funcionar ou terminou com falha.
    pause
)
