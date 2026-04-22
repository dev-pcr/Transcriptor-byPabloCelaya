# Transcriptor IA — by Pablo Celaya

Este proyecto permite transcribir audios largos de forma gratuita usando Whisper (local) o Groq (nube) y formatearlos automáticamente como apuntes de estudio profesionales.

## 🤖 Instalación Automática con IA
Si usas un asistente de programación IA (como **Antigravity** o Cline), puedes ahorrarte todos los pasos manuales. Solo tienes que abrir este proyecto en tu editor y decirle a la IA:
> *"Lee el archivo README.md y haz la instalación y configuración completa por mí."*
La IA se encargará de configurar tu entorno, instalar las librerías necesarias y dejar todo listo para funcionar.

## 🚀 Primera Vez — Configuración Manual

### 1. Python & FFmpeg
- Asegúrate de tener **Python 3.10+** instalado y agregado al `PATH`.
- Instala **FFmpeg** y agrega la carpeta `/bin` al `PATH` de tu sistema (necesario para el manejo interno de archivos de audio).

### 2. Dependencias
- Ejecuta el archivo `INSTALAR.bat`. Esto descargará todas las librerías necesarias (Flask, Pydub, Groq, Whisper, Torch) de forma automática. El sistema detectará automáticamente si te falta instalar Python.

### 3. Configuración de API Key (IMPORTANTE)
Este proyecto utiliza Groq para el formateo ultra rápido de textos con Llama 3. Es 100% gratis.
1. Crea una cuenta en [Console Groq](https://console.groq.com).
2. Crea una API Key.
3. En la carpeta raíz del proyecto, renombra el archivo `.env.example` a `.env` (o crea uno nuevo llamado `.env`).
4. Pega tu clave dentro del archivo de la siguiente manera:
   ```env
   GROQ_API_KEY=tu_clave_de_groq_aqui
   ```

## 🖥️ Crear un Acceso Directo (Recomendado)

Para tener la aplicación siempre a mano en tu escritorio con su logo oficial:
1. Haz clic derecho sobre el archivo `INICIAR.bat`.
2. Selecciona **"Mostrar más opciones"** (si estás en Windows 11) y luego **"Enviar a" > "Escritorio (crear acceso directo)"**.
3. Ve a tu Escritorio, haz clic derecho sobre el acceso directo recién creado y selecciona **"Propiedades"**.
4. Ve a la pestaña **"Acceso directo"** y haz clic en el botón **"Cambiar icono..."**.
5. Haz clic en "Examinar", busca la carpeta de este proyecto y selecciona el archivo `logo.ico`.
6. Haz clic en "Aceptar" y ¡listo! Tendrás la aplicación en tu escritorio como un programa nativo.

## 💻 Uso del Programa

1. Inicia el servidor ejecutando tu acceso directo o **`INICIAR.bat`**. La interfaz se abrirá automáticamente en tu navegador en `http://localhost:5000`.
2. Arrastra tu audio (MP3, WAV, M4A) al área de carga.
3. Elige el modelo de transcripción: 
   - **FAST/PRECISE**: Procesamiento local (usa tu CPU/GPU a través de Whisper).
   - **CLOUD (Groq)**: Procesamiento en la nube (ultra rápido).
4. Elige el modo de salida (Apuntes, Transcripción Simple o Prompt Personalizado).
5. Haz clic en **"Iniciar Transcripción"**.
6. Al terminar, usa el botón **"Copiar Texto"** para llevar tus apuntes a Word, Notion o cualquier otro editor.

## 🛠 Notas Técnicas
- **Corte Inteligente:** El sistema divide audios largos automáticamente buscando silencios en la voz, evitando cortar palabras o explicaciones a la mitad.
- **Caché de Texto:** Si cambias el prompt o el modo de salida después de transcribir, haz clic en "Volver a Procesar" para obtener el nuevo formato al instante, sin tener que esperar a que la IA vuelva a escuchar y transcribir el audio completo.
