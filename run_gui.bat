@echo off
title XAMPP & PHP Upgrade Master
cd /d "%~dp0"

echo ========================================================
echo   Iniciando XAMPP & PHP Upgrade Master...
echo ========================================================

REM Verifica se o python esta acessivel
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no PATH do sistema.
    echo Por favor, instale o Python 3.10+ ou adicione-o ao PATH.
    pause
    exit /b 1
)

start "" pythonw main.py
if %errorlevel% neq 0 (
    python main.py
)
exit /b 0
