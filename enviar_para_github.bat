@echo off
title Enviar Projeto para o GitHub
color 0B
echo ==========================================================
echo        ENVIANDO PROJETO PARA O GITHUB (INVESTIMENTOS)
echo ==========================================================
echo.
cd /d "%~dp0"
echo Repositorio: https://github.com/jackrj090603-prog/investimentos.git
echo Enviando arquivos...
echo.
echo Se uma janela abrir solicitando login, clique em "Sign in with your browser".
echo.
"C:\Program Files\Git\cmd\git.exe" push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ==========================================================
    echo  [SUCESSO] PROJETO PUBLICADO COM SUCESSO NO GITHUB!
    echo  Acesse em: https://github.com/jackrj090603-prog/investimentos
    echo ==========================================================
) else (
    echo [AVISO] Se nao completou, certifique-se de autorizar no navegador.
)
echo.
pause
