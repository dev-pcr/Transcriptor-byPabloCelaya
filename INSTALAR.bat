@echo off
title Transcriptor IA - Instalador
cd /d "%~dp0"

echo.
echo  ============================================================
echo       TRANSCRIPTOR IA - INSTALADOR DE DEPENDENCIAS
echo  ============================================================
echo.

:: Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] ERROR CRITICO: Python no esta instalado o no esta en el PATH.
    echo.
    echo      Paso 1: Ve a https://www.python.org/downloads/
    echo      Paso 2: Descarga la ultima version de Python.
    echo      Paso 3: AL INSTALAR, MARCA LA CASILLA "Add python.exe to PATH" ^(MUY IMPORTANTE^).
    echo.
    echo      Una vez instalado correctamente, vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b
)

echo  [OK] Python detectado.
echo.
echo  1. Actualizando PIP...
python -m pip install --upgrade pip

echo.
echo  2. Instalando librerias base...
python -m pip install setuptools setuptools-rust wheel

echo.
echo  3. Instalando librerias del proyecto...
echo.
python -m pip install flask flask-cors groq pydub openai-whisper python-dotenv
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

echo.
echo  4. Pre-descargando modelos de IA...
echo     Esto evitara esperas cuando uses el programa.
python -c "import whisper; print('--- Descargando Base ---'); whisper.load_model('base'); print('--- Descargando Small ---'); whisper.load_model('small'); print('--- Descargando Medium ---'); whisper.load_model('medium');"

echo.
echo  5. Verificando FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] ADVERTENCIA: No se detecto FFmpeg en el sistema.
    echo      Para que el programa funcione, debes descargar FFmpeg.
    echo      Coloca la carpeta en C:\ffmpeg\bin y agregalo al PATH.
    echo      (Revisa el archivo README o INSTRUCCIONES para mas detalles).
) else (
    echo  [OK] FFmpeg detectado.
)

echo.
echo  INSTALACION COMPLETADA. Usa INICIAR.bat para comenzar.
echo.
pause
