@echo off
title Ceara Finance - Servidores Multi-Sites
color 0A
echo ==========================================================
echo       INICIALIZANDO ECOSSISTEMA CEARA FINANCE MULTI-APPS
echo ==========================================================
echo.
cd /d "%~dp0"
python iniciar_todos_sites.py
pause
