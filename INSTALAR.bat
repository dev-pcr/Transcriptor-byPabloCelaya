@echo off
chcp 65001 >nul
title Transcriptor IA — Instalador
cd /d "%~dp0"

echo.
echo  ============================================================
echo       TRANSCRIPTOR IA — INSTALADOR DE DEPENDENCIAS
echo  ============================================================
echo.
echo  1. Actualizando PIP...
python -m pip install --upgrade pip

echo.
echo  2. Instalando librerías (Flask, Groq, Pydub, Whisper, Torch)...
echo.
pip install flask flask-cors groq pydub openai-whisper torch torchvision torchaudio python-dotenv --index-url https://download.pytorch.org/whl/cpu

echo.
echo  3. Pre-descargando modelos de IA (Base, Small, Medium)...
echo     Esto evitará esperas cuando uses el programa.
python -c "import whisper; print('--- Descargando Base ---'); whisper.load_model('base'); print('--- Descargando Small ---'); whisper.load_model('small'); print('--- Descargando Medium ---'); whisper.load_model('medium');"

echo.
echo  4. Verificando FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] ADVERTENCIA: No se detectó FFmpeg en el sistema.
    echo      Asegúrate de tenerlo en C:\ffmpeg\bin y en el PATH.
) else (
    echo  [OK] FFmpeg detectado.
)

echo.
echo  INSTALACIÓN COMPLETADA. Usa INICIAR.bat para comenzar.
echo.
pause
