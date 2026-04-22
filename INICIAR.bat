@echo off
title Transcriptor IA - Servidor Activo
cd /d "%~dp0"

echo.
echo  ============================================================
echo       TRANSCRIPTOR IA - by Pablo Celaya [MODO LOCAL]
echo  ============================================================
echo.
echo  [1/2] Iniciando el motor de Inteligencia Artificial...
echo        (Si es la primera vez o cambiaste el modelo,
echo         esto puede tardar 1-2 minutos en cargar).
echo.

python backend.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] ERROR: El servidor se detuvo inesperadamente.
    echo      Asegurate de haber ejecutado INSTALAR.bat primero.
    pause
)

echo.
echo  Servidor cerrado.
pause
