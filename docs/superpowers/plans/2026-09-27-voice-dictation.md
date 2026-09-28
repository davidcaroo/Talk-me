# Voice Dictation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una aplicación de escritorio nativa para Windows (10/11) con PySide6 de dictado global por voz, con activación por atajo configurable (`Ctrl + Space`), overlay flotante estilo visionOS / liquid glass, detección de silencio (auto-pause), transcripción local con faster-whisper (CPU int8) y pegado automático en la aplicación activa.

**Architecture:** Arquitectura desacoplada en capas (UI PySide6 sin robo de foco, controlador de sesión, captura de audio con sounddevice, VAD adaptativo, hilo asíncrono para faster-whisper y pegado mediante SendInput de Windows). La gestión de atajos se centraliza en `HotkeyManager` con verificación nativa de conflictos y persistencia en `QSettings`.

**Tech Stack:** Python 3.13, PySide6, faster-whisper, sounddevice, numpy, pyperclip, pynput, ctypes (Win32 API), PyInstaller, Inno Setup.

**Spec:** `docs/superpowers/specs/2026-09-27-voice-dictation-design.md`

## Global Constraints
- Target OS: Windows 10 / 11
- Python runtime: Python 3.13+
- Atajo por defecto: `Ctrl+Space` (centralizado, sin hardcoding disperso)
- Transcripción: 100% local, `base` model, `device="cpu"`, `compute_type="int8"`, guardado en `%LOCALAPPDATA%\VoiceDictation\models\`
- No robo de foco: El overlay no debe quitar el foco a la aplicación que el usuario esté usando (`WS_EX_NOACTIVATE` / `Qt.WindowDoesNotAcceptFocus`)
- Pegado: Mediante portapapeles y `Ctrl+V` (soporte completo de tildes, `ñ`, saltos de línea y texto largo)

---

### Task 1: Configuración de Dependencias y Módulos Base (Paths, Logger, Config)

**Files:**
- Create: `requirements.txt`
- Create: `utils/paths.py`
- Create: `utils/logger.py`
- Create: `utils/config.py`
- Create: `models/app_state.py`
- Create: `models/transcription_result.py`
- Test: `tests/test_config.py`

**Interfaces:**
- `ConfigManager`: `get_hotkey() -> str`, `set_hotkey(val: str)`, `get_auto_paste() -> bool`, `set_auto_paste(val: bool)`, `get_auto_pause_seconds() -> float`, `get_microphone_index() -> int | None`, `is_first_run() -> bool`, `set_first_run_completed()`
- `AppState`: Enum (`IDLE`, `LISTENING`, `PAUSED`, `TRANSCRIBING`, `PASTING`, `DONE`, `ERROR`)

- [ ] **Step 1: Instalar dependencias en el entorno**
Instalar `sounddevice`, `pyperclip`, `pynput` mediante pip.

- [ ] **Step 2: Crear `utils/paths.py` y `utils/logger.py`**
Implementar resolución de rutas de `%LOCALAPPDATA%\VoiceDictation` y logging estructurado.

- [ ] **Step 3: Crear `models/app_state.py` y `models/transcription_result.py`**
Definir estados del overlay y el objeto de datos de la transcripción.

- [ ] **Step 4: Crear `utils/config.py` con `QSettings`**
Centralizar `DEFAULT_HOTKEY = "Ctrl+Space"` y persistencia de configuración.

- [ ] **Step 5: Escribir y ejecutar test unitario de configuración**
Verificar carga, actualización y guardado de atajos y valores por defecto.

---

### Task 2: HotkeyManager Centralizado con Registro Nativo Win32 y Detección de Conflictos

**Files:**
- Create: `input/hotkey_manager.py`
- Test: `tests/test_hotkey_manager.py`

**Interfaces:**
- Consumes: `ConfigManager`
- Produces: `HotkeyManager`:
  - `register_hotkey(hotkey_str: str) -> tuple[bool, str]`
  - `unregister_hotkey() -> None`
  - `update_hotkey(new_hotkey: str) -> tuple[bool, str]`
  - `normalize_hotkey(hotkey_str: str) -> str`
  - `validate_hotkey(hotkey_str: str) -> tuple[bool, str]`
  - Signal: `hotkey_triggered` (QObject emit)

- [ ] **Step 1: Escribir test para normalización y validación de atajos**
Probar combinaciones válidas (`Ctrl+Space`, `Ctrl+Shift+D`) e inválidas (`A`, `Ctrl+Alt+Del`).

- [ ] **Step 2: Implementar hilo Win32 con `RegisterHotKey` y `GetMessageW`**
Garantizar detección de error 1409 (`ERROR_HOTKEY_ALREADY_REGISTERED`) y desacoplamiento de hilos.

- [ ] **Step 3: Conectar señales Qt y verificar registro/desregistro dinámico**

---

### Task 3: Selector Interactivo de Atajos (`HotkeySelector`)

**Files:**
- Create: `app/widgets/hotkey_selector.py`
- Test: `tests/test_hotkey_selector.py`

**Interfaces:**
- Consumes: `HotkeyManager`, `ConfigManager`
- Produces: `HotkeySelector(QWidget)`:
  - Botón de captura interactiva que cambia a "Presiona la nueva combinación..."
  - Escucha física de teclas con modificadores
  - Botón "Restaurar combinación recomendada" (Ctrl + Space)
  - Signal: `hotkey_changed(str)`

- [ ] **Step 1: Implementar captura física de teclas con PySide6 `keyPressEvent` y `pynput`**
- [ ] **Step 2: Estilizar badges visuales de teclas (Ctrl, Shift, Space)**
- [ ] **Step 3: Conectar validación en tiempo real y mensaje de error si está ocupado**

---

### Task 4: Captura de Audio y Motor VAD de Auto-Pausa

**Files:**
- Create: `audio/devices.py`
- Create: `audio/vad.py`
- Create: `audio/recorder.py`
- Test: `tests/test_audio_vad.py`

**Interfaces:**
- Consumes: `sounddevice`, `numpy`
- Produces:
  - `AudioDevices.get_input_devices() -> list[dict]`
  - `VADEngine`: `is_speech(chunk: np.ndarray) -> bool`, `reset()`
  - `AudioRecorder`:
    - `start(device_index: int | None = None)`
    - `stop() -> np.ndarray` (audio buffer 16kHz float32)
    - Signals: `amplitude_updated(float)`, `speech_detected`, `silence_detected(float_elapsed)`

- [ ] **Step 1: Implementar algoritmo VAD con RMS adaptativo y umbral dinámico**
- [ ] **Step 2: Implementar `AudioRecorder` con `sounddevice.InputStream`**
- [ ] **Step 3: Escribir test unitario de VAD con silencios y señales simuladas**

---

### Task 5: Motor de Transcripción Local Asíncrono con faster-whisper

**Files:**
- Create: `speech/model_manager.py`
- Create: `speech/transcriber.py`
- Create: `workers/transcription_worker.py`
- Test: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `AudioRecorder` (audio array)
- Produces:
  - `ModelManager.ensure_model_loaded(model_name="base") -> WhisperModel`
  - `TranscriptionWorker(QThread)`:
    - Inputs: `audio_data: np.ndarray`, `language: str = "es"`
    - Signals: `status_changed(str)`, `transcription_finished(str)`, `transcription_failed(str)`

- [ ] **Step 1: Implementar `ModelManager` con almacenamiento en `%LOCALAPPDATA%\VoiceDictation\models\`**
- [ ] **Step 2: Implementar `TranscriptionWorker` con `faster_whisper.WhisperModel(device="cpu", compute_type="int8")`**
- [ ] **Step 3: Escribir test mockeado y de inicialización del worker**

---

### Task 6: Portapapeles y Pegado Automático en Aplicación Activa

**Files:**
- Create: `input/clipboard.py`
- Create: `input/paste.py`
- Test: `tests/test_paste.py`

**Interfaces:**
- Consumes: `pyperclip`, `ctypes.windll.user32.SendInput`
- Produces:
  - `Clipboard.copy(text: str) -> bool`
  - `Paster.paste_clipboard() -> bool`

- [ ] **Step 1: Implementar copia segura UTF-8 en el portapapeles**
- [ ] **Step 2: Implementar simulación de `Ctrl+V` con `SendInput` de Win32 para no perder caracteres especiales ni tildes**
- [ ] **Step 3: Test unitario de portapapeles con caracteres Unicode y tildes**

---

### Task 7: Controlador de Sesión de Dictado (`DictationController`)

**Files:**
- Create: `controllers/dictation_controller.py`
- Test: `tests/test_dictation_controller.py`

**Interfaces:**
- Consumes: `HotkeyManager`, `AudioRecorder`, `TranscriptionWorker`, `Clipboard`, `Paster`, `AppState`
- Produces: `DictationController(QObject)`:
  - `toggle_dictation()` (debounce + control de estado)
  - `cancel_dictation()` (al presionar Esc)
  - Signals: `state_changed(AppState)`, `amplitude_changed(float)`, `text_inserted(str)`

- [ ] **Step 1: Implementar máquina de estados y debounce de hotkeys**
- [ ] **Step 2: Conectar temporizador de auto-pausa a los 1.5s y reactivación inmediata**
- [ ] **Step 3: Conectar finalización -> transcripción -> copiado -> pegado**

---

### Task 8: Overlay Flotante Estilo visionOS / Liquid Glass y Waveform Dinámico

**Files:**
- Create: `app/widgets/waveform_view.py`
- Create: `app/widgets/status_badge.py`
- Create: `app/widgets/dictation_bar.py`
- Create: `app/overlay.py`
- Test: `tests/test_overlay_smoke.py`

**Interfaces:**
- Consumes: `DictationController`
- Produces: `FloatingOverlay(QWidget)`:
  - `WS_EX_NOACTIVATE` / `Qt.WindowDoesNotAcceptFocus`
  - Renderizado custom con `QPainter` (bordes redondeados, degradados vítreos, sombras)
  - Visualizador de ondas reactivo en tiempo real a la voz
  - Subtítulo dinámico con el atajo actual (ej: "Ctrl + Space para finalizar")
  - Soporte de tecla `Esc` para cancelar sesión

- [ ] **Step 1: Implementar `WaveformView` con barras animadas fluidas (QTimer + suavizado)**
- [ ] **Step 2: Implementar `FloatingOverlay` con flags sin robo de foco y estética glassmorphism**
- [ ] **Step 3: Conectar estados: Listening, Auto-paused, Transcribing, Done, Error**

---

### Task 9: Bandeja del Sistema, Primer Inicio y Ventana de Ajustes

**Files:**
- Create: `app/tray.py`
- Create: `app/first_run.py`
- Create: `app/settings_window.py`
- Create: `app/main_window.py`
- Create: `utils/startup.py` (registro de inicio automático con Windows en Registro HKCU)
- Create: `main.py`

**Interfaces:**
- Consumes: Todos los controladores y widgets anteriores
- Produces:
  - `SystemTrayIcon`: menú con atajo actual, abrir ajustes, acerca de, salir
  - `FirstRunWizard`: diálogo inicial elegante ("Tu atajo recomendado es Ctrl + Space", micrófono, idioma)
  - `SettingsWindow`: configuración completa por pestañas

- [ ] **Step 1: Implementar `FirstRunWizard` rápido y visual**
- [ ] **Step 2: Implementar `SettingsWindow` con `HotkeySelector`, selección de micrófono y auto-pegado**
- [ ] **Step 3: Implementar `SystemTrayIcon` con atajo en tiempo real**
- [ ] **Step 4: Implementar `main.py` unificando el ciclo de vida de la aplicación**

---

### Task 10: Empaquetado PyInstaller e Instalador Inno Setup

**Files:**
- Create: `pyinstaller.spec`
- Create: `installer.iss`
- Create: `assets/icons/app_icon.ico` (generación programática de icono minimalista premium)
- Create: `build_release.bat`

- [ ] **Step 1: Crear icono `.ico` profesional y assets visuales**
- [ ] **Step 2: Configurar `pyinstaller.spec` con hooks de faster-whisper, PySide6 y sin bundler de modelos pesados**
- [ ] **Step 3: Configurar `installer.iss` para instalación limpia en Program Files con opción de inicio con Windows**

---

### Task 11: Verificación Completa y Pruebas de Integración

- [ ] **Step 1: Ejecutar suite de pruebas unitarias (`pytest`)**
- [ ] **Step 2: Validar cambio de hotkey en vivo y persistencia entre ejecuciones**
- [ ] **Step 3: Validar que el overlay no robe el foco y el pegado en editor de texto funcione**
