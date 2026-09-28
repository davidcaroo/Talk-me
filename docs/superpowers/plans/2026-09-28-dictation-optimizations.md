# Dictation Performance & Reliability Optimizations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate cold-start transcription hangs, ensure reliable auto-paste into active applications without modifier collision, pre-warm Whisper models in background RAM, and produce a verified installer build.

**Architecture:** 
1. Cache integrity: Fix `ModelManager.is_model_cached()` to require physical existence of `model.bin` (> 10MB) and automatically purge orphaned `.lock` and `.incomplete` files left by interrupted downloads.
2. Zero-latency inference: Introduce asynchronous background model pre-warming in `MainWindow` upon application startup.
3. Transparent worker UX: `TranscriptionWorker` properly signals `"Descargando modelo de voz..."` when downloading and only transitions to `"Transcribiendo..."` when inference starts.
4. Robust keystroke inking: Enhance `Paster` to release modifier keys (`Ctrl`, `Space`, `Shift`) and wait for key stabilization (80ms) before inking `Ctrl+V` into target windows.
5. Packaging: Execute release build and generate tested installer.

**Tech Stack:** Python 3.13, PySide6, faster-whisper (CTranslate2), ctypes / Win32 SendInput, PyInstaller, Inno Setup (ISCC).

**Spec:** Documented in conversation transcript and root cause analysis:
- Whisper `base` and `tiny` caching in `%LOCALAPPDATA%\VoiceDictation\models\`
- Background warmup without blocking Qt event loop
- Auto-paste into foreground window with modifier key safety

## Global Constraints

- No external network calls in unit tests (use mocks or synthetic test data).
- Thread-safe Qt signal-slot architecture.
- Keep PySide6 GUI responsive at all times (no blocking in main GUI thread).
- Windows 10/11 x64 compatibility with ctypes Win32 API.
- All 153+ existing pytest tests must pass without regressions.

---

### Task 1: Strict Model Cache Verification & Stale Lock Cleanup

**Files:**
- Modify: `speech/model_manager.py`
- Test: `tests/test_model_manager.py`

**Interfaces:**
- Consumes: `utils.paths.get_models_dir`
- Produces: `ModelManager.is_model_cached(model_name: str) -> bool`, `ModelManager.clean_stale_locks() -> int`

- [ ] **Step 1: Write the failing tests in `tests/test_model_manager.py`**
Verify that:
1. An empty directory or directory with 0-byte `incomplete` files returns `is_model_cached == False`.
2. A directory with a valid `model.bin` (> 10MB) returns `True`.
3. Stale `.lock` and `.incomplete` files are cleaned up by `clean_stale_locks()`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_model_manager.py -v`

- [ ] **Step 3: Implement `clean_stale_locks` and strict `is_model_cached` in `speech/model_manager.py`**
Inspect snapshot directories and direct model directories for `model.bin` with `stat().st_size > 1_000_000`. Remove `.lock` and `.incomplete` files if no active downloading thread is present.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_model_manager.py -v`

- [ ] **Step 5: Commit**
`git add speech/model_manager.py tests/test_model_manager.py`
`git commit -m "fix(speech): add strict model cache verification and lock cleanup"`

---

### Task 2: Background Model Pre-warming on App Startup

**Files:**
- Modify: `speech/model_manager.py`
- Modify: `app/main_window.py`
- Test: `tests/test_model_warmup.py`

**Interfaces:**
- Consumes: `ModelManager.load_model`
- Produces: `MainWindow._start_model_warmup()`, `ModelManager.preload_model_async(model_name: str)`

- [ ] **Step 1: Write the failing tests in `tests/test_model_warmup.py`**
Verify that `preload_model_async` spawns a thread and populates `_loaded_models` without blocking.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_model_warmup.py -v`

- [ ] **Step 3: Implement `preload_model_async` in `ModelManager` and trigger in `MainWindow.start`**
When `MainWindow.start()` runs, trigger a background QThread / daemon thread to pre-warm the configured Whisper model if cached.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_model_warmup.py -v`

- [ ] **Step 5: Commit**
`git add speech/model_manager.py app/main_window.py tests/test_model_warmup.py`
`git commit -m "feat(app): add asynchronous model pre-warming on startup"`

---

### Task 3: Transparent Download Feedback & Worker Status Updates

**Files:**
- Modify: `workers/transcription_worker.py`
- Modify: `controllers/dictation_controller.py`
- Test: `tests/test_transcription_worker_status.py`

**Interfaces:**
- Consumes: `TranscriptionWorker.status_changed(str)`
- Produces: Correct UX status progression ("Descargando modelo de voz..." -> "Cargando motor de voz..." -> "Transcribiendo...")

- [ ] **Step 1: Write the failing tests in `tests/test_transcription_worker_status.py`**
Verify signal emission order when model is not cached vs when model is cached.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_transcription_worker_status.py -v`

- [ ] **Step 3: Update `TranscriptionWorker.run` and `DictationController`**
Emit informative status messages and avoid premature "Transcribiendo..." before model download/load finishes.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_transcription_worker_status.py -v`

- [ ] **Step 5: Commit**
`git add workers/transcription_worker.py controllers/dictation_controller.py tests/test_transcription_worker_status.py`
`git commit -m "feat(workers): provide transparent download and preparation status updates"`

---

### Task 4: Robust Auto-Paste with Modifier Key Release & Win32 Clipboard

**Files:**
- Modify: `input/paste.py`
- Modify: `input/clipboard.py`
- Test: `tests/test_paste_robustness.py`

**Interfaces:**
- Consumes: `ctypes.windll.user32.SendInput`
- Produces: `Paster.paste_clipboard(delay_ms: int = 80) -> bool`, explicit modifier release before paste

- [ ] **Step 1: Write the failing tests in `tests/test_paste_robustness.py`**
Verify that `_send_input_paste` releases any dangling `Ctrl`, `Shift`, `Alt`, `Space` before sending `Ctrl+V`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_paste_robustness.py -v`

- [ ] **Step 3: Implement modifier release in `input/paste.py` and ensure Win32 clipboard sync in `input/clipboard.py`**
In `input/paste.py`, release `VK_CONTROL`, `VK_SPACE`, `VK_SHIFT`, `VK_MENU` keyup events before sending Ctrl down + V down + V up + Ctrl up. Set default delay to 80ms for key release stabilization.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_paste_robustness.py -v`

- [ ] **Step 5: Commit**
`git add input/paste.py input/clipboard.py tests/test_paste_robustness.py`
`git commit -m "fix(input): ensure modifier keys release and improve clipboard paste reliability"`

---

### Task 5: Full Regression Testing

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run full pytest suite**
Run: `pytest`
Expected: 100% PASS with 0 errors.

---

### Task 6: Release Build & Inno Setup Installer

**Files:**
- Target: `dist/VoiceDictation/VoiceDictation.exe`
- Target: `dist/VoiceDictation-Setup-v1.0.0.exe`

- [ ] **Step 1: Run PyInstaller build**
Run: `pyinstaller --clean -y pyinstaller.spec`

- [ ] **Step 2: Compile Inno Setup installer**
Run ISCC on `installer.iss`.

- [ ] **Step 3: Verify build artifacts exist and have non-zero size**
Ensure `dist/VoiceDictation/VoiceDictation.exe` and installer executable exist.
