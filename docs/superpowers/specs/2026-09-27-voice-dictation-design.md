# Voice Dictation - Especificación de Diseño y Arquitectura

**Versión:** 1.0.0  
**Autor:** David Caro (@ing.davidcaro)  
**Fecha:** 2026-09-27  
**Estado:** Aprobado para implementación  

---

## 1. Visión del Producto y Objetivos

**Voice Dictation** es una utilidad de escritorio profesional y nativa para Windows (10/11) que permite dictar texto en cualquier aplicación con activación mediante un atajo de teclado global configurable (predeterminado: `Ctrl + Space`).

### Principios Fundamentales:
1. **100% Local y Privado:** Sin nube, sin servicios externos, sin suscripciones por minuto ni recopilación de telemetría.
2. **Sin LLMs ni Chatbots:** Utilidad pura de dictado directo y eficiente.
3. **Mínima Latencia & Carga Ligera:** Motor `faster-whisper` (`base`, `int8`, CPU) con carga perezosa (*lazy loading*).
4. **Experiencia Visual Premium:** Barra overlay flotante inspirada en visionOS / *liquid glass*, con visualizador dinámico reactivo a la voz y sin robo de foco de la ventana activa.
5. **Auto-pausa Inteligente:** Detección de silencio a los 1.5s que entra en modo espera visual sin cortar la sesión hasta que el usuario pulse de nuevo el atajo global.

---

## 2. Estructura de Directorios

```
voice_dictation/
│
├── main.py
├── requirements.txt
├── pyinstaller.spec
├── installer.iss
│
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   ├── overlay.py
│   ├── tray.py
│   ├── first_run.py
│   ├── settings_window.py
│   └── widgets/
│       ├── __init__.py
│       ├── dictation_bar.py
│       ├── waveform_view.py
│       ├── hotkey_selector.py
│       └── status_badge.py
│
├── audio/
│   ├── __init__.py
│   ├── recorder.py
│   ├── vad.py
│   └── devices.py
│
├── speech/
│   ├── __init__.py
│   ├── transcriber.py
│   └── model_manager.py
│
├── input/
│   ├── __init__.py
│   ├── hotkey_manager.py
│   ├── clipboard.py
│   └── paste.py
│
├── controllers/
│   ├── __init__.py
│   └── dictation_controller.py
│
├── workers/
│   ├── __init__.py
│   └── transcription_worker.py
│
├── models/
│   ├── __init__.py
│   ├── app_state.py
│   └── transcription_result.py
│
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── paths.py
│   └── startup.py
│
└── assets/
    ├── icons/
    └── styles/
```

---

## 3. Especificación de Componentes

### 3.1. Gestión de Atajos Globales (`input/hotkey_manager.py` y `app/widgets/hotkey_selector.py`)
- **API Nativa:** Utiliza `ctypes.windll.user32.RegisterHotKey` y `UnregisterHotKey` en un hilo de mensajes de Windows (`MSG` loop), garantizando detección de atajos globales incluso cuando la app está minimizada en la bandeja y permitiendo verificar conflictos de inmediato (código de error `GetLastError() == 1409` - `ERROR_HOTKEY_ALREADY_REGISTERED`).
- **Selector Físico de Atajos:** Componente `HotkeySelector` con modo de escucha en vivo (`pynput.keyboard.Listener`). Captura modificadores (`Ctrl`, `Alt`, `Shift`, `Win`) y teclas principales físicamente, formateando cadenas amigables como `"Ctrl+Space"`, `"Ctrl+Shift+D"`.
- **Validaciones:**
  - Requiere al menos una tecla modificadora o función especial (evita bloquear teclas alfanuméricas simples).
  - Bloquea combinaciones reservadas críticas del sistema (`Ctrl+Alt+Del`, `Win+L`, `Alt+F4`, `Alt+Tab`).
  - Prueba en caliente el registro antes de confirmar el guardado.
- **Botón de Restauración:** "Restaurar combinación recomendada" restablece inmediatamente a `Ctrl+Space`.
- **Persistencia en Vivo:** Guarda en `QSettings` y propaga el cambio sin necesidad de reiniciar la aplicación, actualizando la bandeja y los subtítulos del overlay.

### 3.2. Audio y Detección de Silencio (`audio/recorder.py`, `audio/vad.py`, `audio/devices.py`)
- **Captura:** `sounddevice.InputStream` a 16000 Hz, mono, `float32`.
- **Detección de Silencio (VAD):** Algoritmo basado en RMS dinámico y tasa de cruce por cero (ZCR) calibrado para voz humana en 16 kHz.
- **Temporizador de Auto-pausa:** Si durante ~1.5 segundos consecutivos el nivel se mantiene por debajo del umbral de habla, el estado pasa de `Listening` a `Auto-paused`.
- **Reactivación:** En cuanto el nivel RMS supera el umbral, regresa inmediatamente a `Listening`.
- **Gestión de Dispositivos:** Enumeración de micrófonos disponibles a través de `sounddevice.query_devices()` con selección del dispositivo predeterminado o personalizado.

### 3.3. Transcripción Local (`speech/transcriber.py`, `speech/model_manager.py`, `workers/transcription_worker.py`)
- **Motor:** `faster-whisper` (`WhisperModel`).
- **Parámetros:** `model_size_or_path="base"`, `device="cpu"`, `compute_type="int8"`.
- **Directorio de Modelos:** `%LOCALAPPDATA%\VoiceDictation\models\` para mantener el ejecutable ligero e independiente.
- **Carga Perezosa (Lazy):** Se carga en un hilo secundario la primera vez que se requiere o en segundo plano tras el inicio, sin bloquear la interfaz. Si aún no está descargado, emite estado `Preparing` ("Preparando motor de dictado...").
- **Procesamiento Asíncrono:** `TranscriptionWorker` (subclase de `QThread`) recibe el array numpy de audio y emite `finished(str)`, `error(str)` o `progress(str)`.

### 3.4. Portapapeles y Pegado Automático (`input/clipboard.py`, `input/paste.py`)
- **Portapapeles:** Copia segura en el portapapeles de Windows (`QClipboard` / `pyperclip`) con soporte nativo de UTF-8 (tildes, `ñ`, caracteres especiales y multilínea).
- **Pegado Inteligente:** Envío de evento de teclado `Ctrl + V` mediante `SendInput` de la API de Windows con un intervalo mínimo de estabilización (~40ms). No usa escritura letra por letra para evitar desincronizaciones de caracteres especiales.
- **Configurable:** Opción en Ajustes para activar o desactivar el pegado automático.

### 3.5. Barra Overlay Flotante (`app/overlay.py`, `app/widgets/waveform_view.py`)
- **Estilo Visual:** Inspirado en *visionOS* y *liquid glass*, con bordes redondeados (radio 24px), fondo semitransparente con desenfoque simulado, acentos luminosos y sombras suaves.
- **Flags de Ventana:** `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus`.
- **Atributos Win32:** `WS_EX_NOACTIVATE` para impedir que robe el foco de la ventana activa.
- **Estados:**
  - `Listening`: Micrófono verde/azul pulsante, waveform reactivo a la amplitud real del micrófono, texto *"Escuchando..."*, subtítulo *"[Atajo] para finalizar"*.
  - `Auto-paused`: Icono ámbar sutil, waveform en reposo suave, texto *"En pausa automática"*, subtítulo *"Vuelve a hablar o usa [Atajo] para finalizar"*.
  - `Transcribing`: Indicador animado de procesamiento, texto *"Transcribiendo..."*.
  - `Done`: Check azul/verde, texto *"Texto insertado"*, desvanecimiento automático tras 1 segundo.
  - `Error`: Indicador de advertencia y mensaje de error con auto-ocultado.
- **Teclado:** `Esc` cancela la sesión activa sin pegar nada.

### 3.6. Ventanas de Interfaz
- **Primer Inicio (`app/first_run.py`):** Diálogo de bienvenida de configuración rápida (selección de micrófono, presentación clara del atajo recomendado `Ctrl + Space`, botón para probar/cambiar, toggle de auto-pegado e idioma).
- **Configuración (`app/settings_window.py`):** Pestañas General, Dictado y Apariencia (posición superior/inferior, tamaño compacto/normal, tiempo de auto-pausa, inicio con Windows).
- **Bandeja del Sistema (`app/tray.py`):** Menú contextual con estado actual, atajo dinámico ("Iniciar dictado    Ctrl + Space"), Ajustes, Acerca de y Salir.
- **Acerca de:** Nombre: *Voice Dictation*, Versión: *v1.0.0*, Desarrollado por: *David Caro (@ing.davidcaro)*.

### 3.7. Empaquetado y Distribución
- **PyInstaller (`pyinstaller.spec`):** Genera binario portable standalone sin incluir los modelos pesados dentro del `.exe` (los modelos se descargan y persisten en `%LOCALAPPDATA%`).
- **Inno Setup (`installer.iss`):** Instalador limpio para Windows que instala en `Program Files`, crea accesos directos opcionales y provee desinstalador completo.
