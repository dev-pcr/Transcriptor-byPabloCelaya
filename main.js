const MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*";

// ─── Matrix Scramble ──────────────────────────────────────────────────────
function scrambleText(element, finalValue, duration = 700) {
    element.classList.add('visible');
    let iter = 0;
    const total = 10;
    const iv = setInterval(() => {
        element.textContent = finalValue.split('').map((ch, i) => {
            if (i < (iter / total) * finalValue.length) return finalValue[i];
            return MATRIX_CHARS[Math.floor(Math.random() * MATRIX_CHARS.length)];
        }).join('');
        if (++iter > total) { element.textContent = finalValue; clearInterval(iv); }
    }, duration / total);
}

function runMatrixAnimations() {
    // Ya no usamos .matrix-text en los títulos para permitir la firma estática
    // pero podemos dejarlo para otros elementos si existen.
    document.querySelectorAll('.matrix-text').forEach((el, i) => {
        if (el.classList.contains('no-matrix')) return;
        const txt = el.textContent.trim();
        if (!txt) { el.classList.add('visible'); return; }
        el.textContent = '';
        setTimeout(() => scrambleText(el, txt), i * 120);
    });
}

// ─── Typewriter Matrix (Streaming) ────────────────────────────────────────
async function matrixTypewriter(element, text, delay = 5) {
    const container = document.getElementById('transcription-box');
    
    if (element.textContent.length > 0) {
        element.textContent += '\n\n';
    }

    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        const span = document.createElement('span');
        element.appendChild(span);

        let frames = 0;
        const maxFrames = 2; // Más rápido
        const iv = setInterval(() => {
            if (frames < maxFrames && char !== ' ' && char !== '\n') {
                span.textContent = MATRIX_CHARS[Math.floor(Math.random() * MATRIX_CHARS.length)];
                frames++;
            } else {
                span.textContent = char;
                clearInterval(iv);
            }
        }, 10);

        if (i % 3 === 0) {
            await new Promise(r => setTimeout(r, delay));
            updateStats(element.textContent);
        }
    }
    updateStats(element.textContent, true); // Final update con efecto Matrix
}

// ─── ASCII Player (desde ascii_frames.json) ───────────────────────────────
async function loadAndPlayAscii() {
    const pre = document.getElementById('ascii-render');
    try {
        const res = await fetch('ascii_frames.json');
        if (!res.ok) { if (pre) pre.textContent = '[ sin animacion ]'; return; }
        const { frames, delays } = await res.json();
        let fi = 0;
        const tick = () => {
            if (pre) pre.textContent = frames[fi];
            fi = (fi + 1) % frames.length;
            setTimeout(tick, delays[fi] || 80);
        };
        tick();
    } catch (e) {
        if (pre) pre.textContent = '[ error cargando animacion ]';
    }
}

// ─── Transcripción ────────────────────────────────────────────────────────
let currentAudioName = "transcripcion";
let fullTranscriptionText = ""; // Guardamos el texto completo para copiar
let rawTranscriptionText  = ""; // Guardamos el crudo para re-procesar sin Whisper
let lastModelUsed         = ""; 
let selectedFile          = null; 

function setBox(html) {
    const box = document.getElementById('transcription-box');
    if (box) box.innerHTML = html;
}

function showView(view) {
    const ascii = document.getElementById('ascii-render');
    const trans = document.getElementById('transcription-box');
    const stats = document.getElementById('stats-bar');
    const copy  = document.getElementById('copy-btn');

    if (view === 'results') {
        ascii.classList.remove('active');
        trans.classList.remove('hidden');
        stats.classList.remove('hidden');
        copy.classList.remove('hidden');
    } else {
        ascii.classList.add('active');
        trans.classList.add('hidden');
        stats.classList.add('hidden');
        copy.classList.add('hidden');
    }
}

function updateStats(text, useScramble = false) {
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    const time  = Math.ceil(words / 200) || 1;
    const model = document.getElementById('model-select').value;
    const modelName = model === 'groq' ? 'Groq Turbo' : model.toUpperCase();

    const elWords = document.getElementById('stat-words');
    const elChars = document.getElementById('stat-chars');
    const elTime  = document.getElementById('stat-time');
    const elModel = document.getElementById('stat-model');

    if (useScramble) {
        scrambleText(elWords, words.toString(), 400);
        scrambleText(elChars, chars.toString(), 400);
        scrambleText(elTime, `${time} min`, 500);
        scrambleText(elModel, modelName, 600);
    } else {
        elWords.textContent = words;
        elChars.textContent = chars;
        elTime.textContent  = `${time} min`;
        elModel.textContent  = modelName;
    }
}

async function transcribir(file) {
    setBox('<div class="placeholder-container"><div class="spinner"></div><span class="placeholder">Iniciando transcripción...</span></div>');

    const modelSelect  = document.getElementById('model-select');
    const promptSelect = document.getElementById('prompt-select');
    const customPrompt = document.getElementById('custom-prompt');

    const model        = modelSelect.value;
    let   promptMode   = promptSelect.value;

    // Si es "otro", mandamos el contenido del textarea como el prompt_mode
    // El backend lo interpretará como el prompt directo si no es "base" o "estudio"
    if (promptMode === 'otro') {
        promptMode = customPrompt.value || 'base'; // fallback a base si está vacío
    }

    const formData = new FormData();
    formData.append('audio', file);
    formData.append('model', model);
    formData.append('prompt_mode', promptMode);

    let textoFinal = '';

    try {
        showView('results');
        const res = await fetch('/transcribir', { method: 'POST', body: formData });
        if (!res.ok) { setBox(`<span class="err">Error del servidor: ${res.status}</span>`); return; }

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const event = JSON.parse(line.slice(6));

                if (event.tipo === 'progreso') {
                    setBox(`<div class="placeholder-container"><div class="spinner"></div><span class="placeholder">${event.msg}</span></div>`);
                } else if (event.tipo === 'raw_text') {
                    rawTranscriptionText = event.texto;
                } else if (event.tipo === 'resultado') {
                    setBox('<pre class="result-text"></pre>');
                    const pre = document.querySelector('#transcription-box .result-text');
                    if (pre) {
                        fullTranscriptionText = event.texto;
                        await matrixTypewriter(pre, event.texto);
                    }
                    document.getElementById('copy-btn')?.classList.add('active');
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').innerHTML = 'Volver a Procesar';
                    lucide.createIcons();
                } else if (event.tipo === 'error') {
                    setBox(`<span class="err">Error: ${event.msg}</span>`);
                }
            }
        }
    } catch (err) {
        setBox(`<span class="err">No se pudo conectar con el backend.<br>Asegurate de haber iniciado INICIAR.bat</span>`);
    }

    return textoFinal;
}

async function reformatear() {
    setBox('<div class="placeholder-container"><div class="spinner"></div><span class="placeholder">Re-aplicando nuevo formato a la transcripción…</span></div>');

    const promptSelect = document.getElementById('prompt-select');
    const customPrompt = document.getElementById('custom-prompt');
    let   promptMode   = promptSelect.value;

    if (promptMode === 'otro') promptMode = customPrompt.value || 'base';

    try {
        showView('results');
        const res = await fetch('/formatear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                texto: rawTranscriptionText,
                prompt_mode: promptMode
            })
        });

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const event = JSON.parse(line.slice(6));

                if (event.tipo === 'progreso') {
                    setBox(`<div class="placeholder-container"><div class="spinner"></div><span class="placeholder">${event.msg}</span></div>`);
                } else if (event.tipo === 'resultado') {
                    setBox('<pre class="result-text"></pre>');
                    const pre = document.querySelector('#transcription-box .result-text');
                    if (pre) {
                        fullTranscriptionText = event.texto;
                        await matrixTypewriter(pre, event.texto);
                    }
                    document.getElementById('copy-btn')?.classList.add('active');
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').innerHTML = 'Volver a Procesar';
                    lucide.createIcons();
                } else if (event.tipo === 'error') {
                    setBox(`<span class="err">Error: ${event.msg}</span>`);
                }
            }
        }
    } catch (err) {
        setBox(`<span class="err">Error de conexión.</span>`);
    }
}

// ─── UI Events ────────────────────────────────────────────────────────────
function setupUI() {
    const dropzone   = document.getElementById('dropzone');
    const audioInput = document.getElementById('audio-input');
    const startBtn   = document.getElementById('start-btn');
    const resetBtn   = document.getElementById('reset-btn');
    const promptToggle = document.getElementById('prompt-toggle');
    const customPrompt = document.getElementById('custom-prompt');

    // Click en dropzone abre explorador
    dropzone?.addEventListener('click', () => audioInput.click());

    // Drag & Drop
    dropzone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    dropzone?.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone?.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            audioInput.files = e.dataTransfer.files;
            audioInput.dispatchEvent(new Event('change'));
        }
    });

    audioInput?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        selectedFile = file;
        currentAudioName = file.name.split('.').slice(0, -1).join('.');
        
        // Actualizar visual del dropzone
        dropzone.querySelector('.title').textContent = 'Archivo Seleccionado';
        dropzone.querySelector('.subtitle').innerHTML = `<span style="font-size: 1rem; color: var(--fg); font-weight: 700;">${file.name}</span>`;
        dropzone.style.borderColor = 'var(--fg)';
        
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = 'Iniciar Transcripción';
        }
        if (resetBtn) resetBtn.classList.remove('hidden');
    });

    startBtn?.addEventListener('click', async () => {
        if (!selectedFile) return;

        const currentModel = document.getElementById('model-select').value;
        startBtn.disabled = true;

        if (rawTranscriptionText && currentModel === lastModelUsed) {
            await reformatear();
        } else {
            lastModelUsed = currentModel;
            await transcribir(selectedFile);
        }
    });

    resetBtn?.addEventListener('click', () => {
        selectedFile = null;
        fullTranscriptionText = "";
        rawTranscriptionText  = "";
        lastModelUsed         = "";
        setBox('<span class="placeholder">Esperando audio...</span>');
        showView('ascii');
        audioInput.value = "";
        
        dropzone.querySelector('.title').textContent = 'Cargar Audio';
        dropzone.querySelector('.subtitle').textContent = 'MP3, WAV, M4A, MP4 - hasta 2 GB';
        
        startBtn.disabled = true;
        startBtn.innerHTML = 'Iniciar Transcripción';
        resetBtn.classList.add('hidden');
        customPrompt.classList.add('hidden');
        document.getElementById('prompt-select').value = 'base';
    });

    const copyBtn = document.getElementById('copy-btn');
    copyBtn?.addEventListener('click', async () => {
        if (!fullTranscriptionText) return;
        try {
            await navigator.clipboard.writeText(fullTranscriptionText);
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '¡Copiado!';
            setTimeout(() => {
                copyBtn.innerHTML = originalHTML;
            }, 2000);
        } catch (err) {
            console.error('Error al copiar:', err);
        }
    });

    // Mostrar prompt personalizado solo si se elige "otro"
    document.getElementById('prompt-select')?.addEventListener('change', (e) => {
        if (e.target.value === 'otro') {
            customPrompt.classList.remove('hidden');
        } else {
            customPrompt.classList.add('hidden');
        }
    });
}

// ─── Init ─────────────────────────────────────────────────────────────────
const ready = () => { runMatrixAnimations(); setupUI(); loadAndPlayAscii(); lucide.createIcons(); };
document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', ready)
    : ready();
