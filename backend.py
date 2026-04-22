# ============================================================
#  TRANSCRIPTOR IA — Backend Flask
#  Whisper (Groq) → puntuación (LLaMA) → devuelve texto
#  Sirve también los archivos estáticos del frontend.
# ============================================================

# ─── CONFIGURACIÓN (editar solo esta sección) ─────────────────
import os
from dotenv import load_dotenv
load_dotenv()  # Carga variables desde .env

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
IDIOMA_AUDIO   = "es"                       # idioma del audio
CHUNK_MIN      = 10                         # minutos por fragmento (<25MB)
PALABRAS_CHUNK = 600                   # palabras por bloque de puntuación (free tier: max ~600)
PORT           = 5000                       # puerto local

# Modelo Whisper local (tiny, base, small, medium, large)
# 'base' es rápido, 'small' es mejor, 'medium' es excelente pero lento.
MODELO_WHISPER = "base"
# ──────────────────────────────────────────────────────────────

import math, time, shutil, json, tempfile, webbrowser
from pathlib import Path
from flask import Flask, request, Response, send_from_directory, stream_with_context
from flask_cors import CORS
from groq import Groq
from pydub import AudioSegment
import whisper

app    = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
client = Groq(api_key=GROQ_API_KEY)

# Caché de modelos para no recargar si ya están en memoria
models_cache = {}

def get_whisper_model(model_name):
    if model_name not in models_cache:
        print(f"Cargando modelo Whisper local ({model_name})...")
        models_cache[model_name] = whisper.load_model(model_name)
        print(f"Modelo {model_name} cargado.")
    return models_cache[model_name]

# Cargar el base por defecto al inicio
get_whisper_model(MODELO_WHISPER)

# PROMPTS
PROMPT_BASE = (
    "Sos un asistente especializado en formatear transcripciones automáticas "
    "de clases universitarias de ingeniería.\n\n"
    "Tu única tarea es:\n"
    "1. Agregar puntuación correcta: puntos, comas, dos puntos, signos de pregunta.\n"
    "2. Dividir el texto en párrafos lógicos: uno nuevo cada vez que cambia la idea.\n"
    "3. NO inventar contenido, NO resumir, NO cambiar palabras.\n"
    "4. Respetar los términos técnicos exactamente como aparecen.\n\n"
    "Devolvé ÚNICAMENTE el texto con puntuación y párrafos. Sin comentarios."
)

PROMPT_ESTUDIO = (
    "Actúa como un asistente académico experto en organización de apuntes.\n\n"
    "Tu tarea es transformar una transcripción de clase (texto crudo, desordenado, con repeticiones y errores) "
    "en apuntes claros, estructurados y útiles para estudiar.\n\n"
    "FORMATO OBLIGATORIO:\n\n"
    "1. TÍTULO\n"
    "- Representa el tema principal de la clase.\n\n"
    "2. SUBTÍTULOS\n"
    "- Dividen los temas importantes.\n\n"
    "3. PÁRRAFOS\n"
    "- Explicaciones claras, corregidas y resumidas.\n"
    "- Máximo 3-5 líneas por párrafo.\n"
    "- Usar solo cuando se necesite desarrollar una idea.\n\n"
    "4. LISTAS (USO CLAVE)\n"
    "- NO usar listas solo para enumerar.\n"
    "- Usarlas principalmente para:\n"
    "  • Resumir ideas importantes\n"
    "  • Sintetizar conceptos\n"
    "  • Mostrar características\n"
    "  • Destacar reglas o condiciones\n"
    "  • Anotar puntos clave de explicación del profesor\n\n"
    "- Cada ítem debe ser:\n"
    "  • Corto\n"
    "  • Claro\n"
    "  • Directo\n"
    "  • Fácil de memorizar\n\n"
    "- Incluir sublistas cuando haya jerarquía o desglose.\n"
    "- Evitar párrafos largos si pueden convertirse en lista.\n\n"
    "5. \"DE FINAL:\"\n"
    "- Crear esta sección SOLO cuando el profesor diga explícitamente que algo es importante para examen.\n"
    "- Resumir ese contenido en frases claras y directas.\n\n"
    "REGLAS IMPORTANTES:\n"
    "- No inventar contenido.\n"
    "- No omitir conceptos importantes.\n"
    "- Corregir errores gramaticales.\n"
    "- Eliminar repeticiones innecesarias.\n"
    "- Reorganizar el contenido si está desordenado.\n"
    "- Mantener lenguaje simple y académico.\n"
    "- Priorizar claridad sobre literalidad.\n"
    "- Resaltar en **negrita hasta 3 palabras clave por oración**.\n\n"
    "6. IDEAS CLAVE (OPCIONAL)\n"
    "- Lista final con los conceptos más importantes (5-10 ítems).\n\n"
    "Devolvé ÚNICAMENTE el texto estructurado. Sin comentarios adicionales."
)


# ─── Utilidades de audio ───────────────────────────────────────

from pydub.silence import detect_silence

def dividir_audio(audio_path: Path, tmp_dir: Path) -> list[Path]:
    audio = AudioSegment.from_file(str(audio_path))
    duration_ms = len(audio)
    chunk_ms_target = CHUNK_MIN * 60 * 1000
    chunks = []
    
    current_pos = 0
    while current_pos < duration_ms:
        next_target = current_pos + chunk_ms_target
        
        # Si falta menos de un chunk, terminamos aquí
        if next_target >= duration_ms:
            split_pos = duration_ms
        else:
            # Buscar un silencio cerca del objetivo (ventana de 10 seg antes y 2 seg después)
            search_start = max(0, next_target - 10000)
            search_end = min(duration_ms, next_target + 2000)
            window = audio[search_start:search_end]
            
            # Detectar silencias de al menos 500ms con un umbral de -40dBFS
            silences = detect_silence(window, min_silence_len=500, silence_thresh=-40)
            
            if silences:
                # Usar el último silencio encontrado en la ventana para maximizar el tamaño del chunk
                s_start, s_end = silences[-1]
                # El tiempo es relativo a la ventana, lo pasamos a absoluto
                split_pos = search_start + s_start + (s_end - s_start) // 2
            else:
                # Si no hay silencios, cortar en el objetivo
                split_pos = next_target
        
        parte = audio[current_pos:split_pos]
        dest  = tmp_dir / f"chunk_{len(chunks):03d}.mp3"
        parte.export(dest, format="mp3", bitrate="64k")
        chunks.append(dest)
        current_pos = split_pos
        
    return chunks, len(chunks)


def transcribir_chunks(chunks: list[Path]) -> str:
    texto = ""
    for cp in chunks:
        with open(cp, "rb") as f:
            r = client.audio.transcriptions.create(
                file=(cp.name, f.read()),
                model="whisper-large-v3",
                language=IDIOMA_AUDIO,
                response_format="text"
            )
        texto += str(r) + " "
        time.sleep(1)
    return texto.strip()


def puntuar_bloque(texto: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user",   "content": texto}
        ],
        temperature=0.05,
        max_tokens=4096
    )
    return resp.choices[0].message.content.strip()


def puntuar_texto(texto: str, prompt: str) -> str:
    palabras  = texto.split()
    total     = len(palabras)
    n_bloques = math.ceil(total / PALABRAS_CHUNK)
    partes    = []
    for i in range(n_bloques):
        bloque = " ".join(palabras[i * PALABRAS_CHUNK : (i + 1) * PALABRAS_CHUNK])
        partes.append(puntuar_bloque(bloque, prompt))
        if i < n_bloques - 1:
            time.sleep(2)
    return "\n\n".join(partes)


# ─── Helpers SSE ──────────────────────────────────────────────

def sse(tipo: str, **kwargs) -> str:
    payload = json.dumps({"tipo": tipo, **kwargs}, ensure_ascii=False)
    return f"data: {payload}\n\n"


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/transcribir", methods=["POST"])
def transcribir():
    if "audio" not in request.files:
        return {"error": "No se recibió ningún archivo"}, 400

    audio_file = request.files["audio"]
    model_name = request.form.get("model", MODELO_WHISPER) # Usar el enviado o el por defecto
    suffix     = Path(audio_file.filename).suffix or ".mp3"

    def generate():
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            # (Opcional) Cargar modelo local si no es Groq
            if model_name != "groq":
                get_whisper_model(model_name)

            prompt_mode     = request.form.get("prompt_mode", "estudio")
            
            if prompt_mode == "estudio":
                selected_prompt = PROMPT_ESTUDIO
            elif prompt_mode == "base":
                selected_prompt = PROMPT_BASE
            else:
                # Si no es ninguno de los predefinidos, es un prompt personalizado
                selected_prompt = prompt_mode

            # Guardar audio recibido
            audio_path = tmp_dir / f"audio{suffix}"
            audio_file.save(str(audio_path))
            yield sse("progreso", msg=f"¡Audio recibido! Usando modelo {model_name.upper()}...")

            # 1. Dividir
            chunks, n = dividir_audio(audio_path, tmp_dir)
            yield sse("progreso", msg=f"Preparando {n} parte(s) para la transcripción inteligente...")

            # 2. Transcribir chunk a chunk (Local o Groq)
            texto_crudo = ""
            for i, cp in enumerate(chunks):
                modo_label = "GROQ TURBO" if model_name == "groq" else model_name.upper()
                yield sse("progreso", msg=f"Escuchando y convirtiendo audio (Parte {i+1} de {n}) [{modo_label}]...")
                
                if model_name == "groq":
                    # Transcripción vía API de Groq
                    with open(cp, "rb") as f:
                        r = client.audio.transcriptions.create(
                            file=(cp.name, f.read()),
                            model="whisper-large-v3",
                            language=IDIOMA_AUDIO,
                            response_format="text"
                        )
                    texto_crudo += str(r) + " "
                    time.sleep(0.5) # Pequeño respiro para la API
                else:
                    # Transcripción local
                    current_model = get_whisper_model(model_name)
                    result = current_model.transcribe(str(cp), language=IDIOMA_AUDIO)
                    texto_crudo += result["text"] + " "
                
            texto_crudo = texto_crudo.strip()
            yield sse("raw_text", texto=texto_crudo) # Enviamos el crudo al frontend para re-procesar si hace falta
            palabras    = len(texto_crudo.split())
            yield sse("progreso", msg=f"Transcripción inicial completa. Ahora la IA organizará el texto con puntos y párrafos...")

            # 3. Puntuar
            n_bloques = math.ceil(palabras / PALABRAS_CHUNK)
            partes    = []
            for i in range(n_bloques):
                bloque = " ".join(texto_crudo.split()[i * PALABRAS_CHUNK : (i + 1) * PALABRAS_CHUNK])
                yield sse("progreso", msg=f"Dando formato y sentido al texto (Bloque {i+1} de {n_bloques})...")
                partes.append(puntuar_bloque(bloque, selected_prompt))
                if i < n_bloques - 1:
                    time.sleep(2)
            texto_final = "\n\n".join(partes)

            yield sse("progreso", msg="¡Todo listo! Generando vista final...")
            # 4. Devolver resultado
            yield sse("resultado", texto=texto_final)

        except Exception as e:
            yield sse("error", msg=str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/formatear", methods=["POST"])
def formatear():
    data        = request.json
    texto_crudo = data.get("texto", "")
    prompt_mode = data.get("prompt_mode", "estudio")
    
    if not texto_crudo:
        return {"error": "No hay texto para formatear"}, 400

    if prompt_mode == "estudio":
        selected_prompt = PROMPT_ESTUDIO
    elif prompt_mode == "base":
        selected_prompt = PROMPT_BASE
    else:
        selected_prompt = prompt_mode

    def generate():
        try:
            palabras  = len(texto_crudo.split())
            n_bloques = math.ceil(palabras / PALABRAS_CHUNK)
            partes    = []
            
            yield sse("progreso", msg=f"Re-procesando texto con nuevo prompt ({n_bloques} bloques)...")
            
            for i in range(n_bloques):
                bloque = " ".join(texto_crudo.split()[i * PALABRAS_CHUNK : (i + 1) * PALABRAS_CHUNK])
                yield sse("progreso", msg=f"Dando formato y sentido al texto (Bloque {i+1} de {n_bloques})...")
                partes.append(puntuar_bloque(bloque, selected_prompt))
                if i < n_bloques - 1:
                    time.sleep(2)
            
            texto_final = "\n\n".join(partes)
            yield sse("resultado", texto=texto_final)
            
        except Exception as e:
            yield sse("error", msg=str(e))

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ─── Arranque ─────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  Transcriptor IA corriendo en http://localhost:{PORT}")
    print("  Cerrá esta ventana para detener el servidor.\n")
    
    # Abrir el navegador automáticamente al iniciar
    webbrowser.open(f"http://localhost:{PORT}")
    
    app.run(port=PORT, debug=False, threaded=True)
