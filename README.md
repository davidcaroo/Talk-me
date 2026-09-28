# Voice Dictation (Talk-me) 🎙️✨

**Voice Dictation** es una utilidad de escritorio nativa para Windows (10/11) desarrollada con Python y PySide6. Permite activar el micrófono mediante una combinación de teclas global configurable, dictar texto, transcribirlo localmente con `faster-whisper` (100% privado y sin conexión a la nube) y pegar el resultado automáticamente en la aplicación activa.

Desarrollado por **David Caro** ([@ing.davidcaro](https://github.com/davidcaroo)).

---

## 🌟 Características Principales

- **Atajo Global Configurable:**
  - Combinación recomendada por defecto: `Ctrl + Space`.
  - Selector físico interactivo (`HotkeySelector`) que detecta combinaciones en vivo con badges visuales.
  - Validación de atajos y detección nativa de conflictos con Windows (código 1409).
  - Restablecimiento instantáneo a `Ctrl + Space` con un solo clic.
  - Cambio en tiempo real sin necesidad de reiniciar la app y persistencia con `QSettings`.

- **Overlay Flotante Moderno (Estilo visionOS / Liquid Glass):**
  - Barra translúcida con sombras difusas, bordes iluminados y tipografía nítida.
  - Sin robo de foco: utiliza atributos nativos de Windows (`WS_EX_NOACTIVATE` y `Qt.WindowDoesNotAcceptFocus`) para que Word, VS Code, Chrome o el Bloc de notas nunca pierdan el cursor.
  - Visualizador dinámico de audio (Waveform) reactivo a la voz en tiempo real.
  - Tecla `Esc` para cancelar inmediatamente la sesión.

- **Detección de Silencio y Auto-Pausa:**
  - Algoritmo VAD adaptativo basado en energía RMS y cruce por cero (ZCR), sin dependencias complejas de compilación en C.
  - A los ~1.5 segundos de silencio pasa automáticamente a estado `Auto-paused`.
  - Reanuda la captura instantáneamente al volver a hablar.
  - La sesión concluye formalmente al volver a presionar el atajo global.

- **Transcripción Local Asíncrona (faster-whisper):**
  - Modelo `base` optimizado para CPU (`int8`), ultrarrápido y ligero (~140 MB de descarga automática única).
  - Los modelos se almacenan de forma desacoplada en `%LOCALAPPDATA%\VoiceDictation\models\`.
  - 100% privado: cero envío de audio a servidores externos, cero costos por minuto.

- **Portapapeles y Pegado Automático:**
  - Copia segura en UTF-8 con soporte total para tildes, `ñ`, caracteres multilínea y símbolos.
  - Pegado instantáneo en la app enfocada mediante `Ctrl + V` vía `SendInput` de Win32.

- **Bandeja del Sistema y Ajustes:**
  - Icono en System Tray con estado en tiempo real y menú con el atajo dinámico.
  - Asistente de primer inicio (*First Run Wizard*) con bienvenida y configuración rápida.
  - Ventana de configuración completa: micrófono, idioma, modelo, auto-pegado, tiempo de auto-pausa y arranque automático con Windows.

- **Empaquetado y Distribución:**
  - Configurado para generar ejecutable portable con `PyInstaller` (`pyinstaller.spec`).
  - Instalador nativo para Windows con `Inno Setup` (`installer.iss`).

---

## 🛠️ Requisitos e Instalación

### Requisitos:
- Windows 10 o Windows 11
- Python 3.11 o superior (probado en Python 3.13)

### Instalación de dependencias:
```bash
pip install -r requirements.txt
```

### Ejecutar en modo desarrollo:
```bash
python main.py
```

### Ejecutar tests automatizados:
```bash
pytest
```

---

## 📦 Compilación para Distribución

### Generar ejecutable portable con PyInstaller:
```bash
pyinstaller pyinstaller.spec --clean
```
El ejecutable se generará en `dist/VoiceDictation.exe`.

### Generar instalador con Inno Setup:
Compila `installer.iss` usando Inno Setup Compiler o ejecuta:
```cmd
build_release.bat
```

---

## 👤 Autor

- **David Caro** - [@ing.davidcaro](https://github.com/davidcaroo)
