"""Central coordinator for voice dictation sessions."""

from typing import Optional
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from audio.recorder import AudioRecorder
from input.clipboard import Clipboard
from input.hotkey_manager import HotkeyManager
from input.paste import Paster
from models.app_state import AppState
from models.transcription_result import TranscriptionResult
from speech.model_manager import ModelManager
from speech.transcriber import LocalTranscriber
from utils.config import DEFAULT_HOTKEY, ConfigManager
from utils.logger import get_logger
from workers.transcription_worker import TranscriptionWorker

logger = get_logger("controllers.dictation_controller")


class DictationController(QObject):
    """Orchestrates dictation session lifecycle, state transitions, audio capture,

    transcription workers, and auto-pasting without UI coupling.
    """

    state_changed = Signal(AppState)
    amplitude_updated = Signal(float)
    status_text_updated = Signal(str)
    subtext_updated = Signal(str)
    text_inserted = Signal(str)
    session_error = Signal(str)
    hotkey_updated = Signal(str)

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        hotkey_manager: Optional[HotkeyManager] = None,
        audio_recorder: Optional[AudioRecorder] = None,
        clipboard: Optional[Clipboard] = None,
        paster: Optional[Paster] = None,
        model_manager: Optional[ModelManager] = None,
        transcriber: Optional[LocalTranscriber] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._audio_recorder = audio_recorder or AudioRecorder()
        self._clipboard = clipboard or Clipboard()
        self._paster = paster or Paster()
        self._model_manager = model_manager
        self._transcriber = transcriber
        self._hotkey_manager = hotkey_manager

        self._state: AppState = AppState.IDLE
        self._worker: Optional[TranscriptionWorker] = None

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connects signals from audio recorder and hotkey manager."""
        if self._audio_recorder is not None:
            self._audio_recorder.amplitude_updated.connect(self._on_amplitude_updated)
            self._audio_recorder.speech_detected.connect(self.on_speech_detected)
            self._audio_recorder.silence_detected.connect(self.on_silence_detected)
            self._audio_recorder.recording_error.connect(self._on_recording_error)

        if self._hotkey_manager is not None:
            self._hotkey_manager.hotkey_triggered.connect(self.toggle_dictation)

    @property
    def state(self) -> AppState:
        """Current session lifecycle state."""
        return self._state

    @property
    def current_hotkey(self) -> str:
        """Currently active hotkey string."""
        if self._hotkey_manager is not None:
            hk = self._hotkey_manager.get_current_hotkey()
            if hk:
                return hk
        return self._config_manager.get_hotkey() or DEFAULT_HOTKEY

    def _set_state(self, new_state: AppState) -> None:
        """Transitions to a new state and emits state_changed."""
        if self._state != new_state:
            self._state = new_state
            logger.debug(f"Session state transition -> {new_state}")
            self.state_changed.emit(new_state)

    def toggle_dictation(self) -> None:
        """Toggles dictation on or off based on current state."""
        if self._state in (AppState.TRANSCRIBING, AppState.PASTING):
            logger.debug(f"Toggle ignored during state: {self._state}")
            return

        if self._state == AppState.IDLE or self._state in (AppState.DONE, AppState.ERROR):
            self._start_dictation()
        elif self._state in (AppState.LISTENING, AppState.PAUSED):
            self._finish_dictation()

    def _start_dictation(self) -> None:
        """Initiates recording and transitions to LISTENING state."""
        device_idx = self._config_manager.get_microphone_index()
        started = self._audio_recorder.start(device_index=device_idx)
        if not started:
            err = "No se pudo iniciar el grabador de audio"
            logger.error(err)
            self._set_state(AppState.ERROR)
            self.status_text_updated.emit("Error de micrófono")
            self.subtext_updated.emit("Verifica tu dispositivo de entrada")
            self.session_error.emit(err)
            QTimer.singleShot(2000, self._return_to_idle)
            return

        self._set_state(AppState.LISTENING)
        self.status_text_updated.emit("Escuchando...")
        self.subtext_updated.emit(f"{self.current_hotkey} para finalizar")

    def _finish_dictation(self) -> None:
        """Stops recording, checks audio length, and starts transcription."""
        self._set_state(AppState.TRANSCRIBING)
        self.status_text_updated.emit("Transcribiendo...")
        self.subtext_updated.emit("Procesando audio...")

        audio_data = self._audio_recorder.stop()
        sample_rate = getattr(self._audio_recorder, "sample_rate", 16000)
        duration = len(audio_data) / sample_rate if sample_rate > 0 else 0.0

        if len(audio_data) == 0 or duration < 0.2:
            logger.info(f"Audio captured too short ({duration:.2f}s) or empty. Resetting to IDLE.")
            self._set_state(AppState.IDLE)
            self.status_text_updated.emit("Audio no detectado")
            self.subtext_updated.emit(f"Presiona {self.current_hotkey} para comenzar")
            self.amplitude_updated.emit(0.0)
            return

        self._spawn_worker(audio_data)

    def _spawn_worker(self, audio_data: np.ndarray) -> None:
        """Creates and launches background transcription worker thread."""
        model_name = self._config_manager.get_model_name()
        language = self._config_manager.get_language()

        worker = TranscriptionWorker(
            audio_data=audio_data,
            model_name=model_name,
            language=language,
            model_manager=self._model_manager,
            transcriber=self._transcriber,
            parent=self,
        )
        worker.status_changed.connect(self._on_worker_status_changed)
        worker.finished.connect(self.on_transcription_finished)
        worker.failed.connect(self.on_transcription_failed)
        self._worker = worker
        worker.start()

    def _on_worker_status_changed(self, status: str) -> None:
        """Handles intermediate status updates from worker."""
        if self._state == AppState.TRANSCRIBING:
            self.status_text_updated.emit(status)
            if "Descargando" in status:
                self.subtext_updated.emit("Descarga única del modelo (~75-145MB)...")
            elif "Transcribiendo" in status:
                self.subtext_updated.emit("Procesando audio...")

    def on_speech_detected(self) -> None:
        """VAD callback: resumes recording state when speech resumes."""
        if self._state == AppState.PAUSED:
            self._set_state(AppState.LISTENING)
            self.status_text_updated.emit("Escuchando...")
            self.subtext_updated.emit(f"{self.current_hotkey} para finalizar")

    def on_silence_detected(self, silence_sec: float | None = None) -> None:
        """VAD callback: enters auto-pause when silence threshold is reached."""
        if self._state == AppState.LISTENING:
            self._set_state(AppState.PAUSED)
            self.status_text_updated.emit("En pausa automática")
            self.subtext_updated.emit(f"Vuelve a hablar o usa {self.current_hotkey} para finalizar")

    def on_transcription_finished(self, result: TranscriptionResult) -> None:
        """Handles successful transcription output and executes auto-paste."""
        if self._state != AppState.TRANSCRIBING:
            logger.debug(f"Ignoring transcription finished signal in state: {self._state}")
            return

        raw_text = result.text if result and result.text else ""
        text = raw_text.strip()
        if not text:
            logger.info("Transcripción vacía o con solo espacios. Volviendo a IDLE.")
            self._set_state(AppState.IDLE)
            self.status_text_updated.emit("Listo para dictar")
            self.subtext_updated.emit(f"Presiona {self.current_hotkey} para comenzar")
            self.amplitude_updated.emit(0.0)
            return

        # Copiar al portapapeles
        self._clipboard.copy(text)

        auto_paste = self._config_manager.get_auto_paste()
        if auto_paste:
            self._set_state(AppState.PASTING)
            self.status_text_updated.emit("Insertando texto...")
            self._paster.paste_clipboard()

        self._set_state(AppState.DONE)
        self.status_text_updated.emit("Texto insertado" if auto_paste else "Texto copiado")
        self.subtext_updated.emit("")
        self.text_inserted.emit(text)

        # Programar retorno suave a IDLE tras 1.2 segundos
        QTimer.singleShot(1200, self._return_to_idle)

    def on_transcription_failed(self, error: str) -> None:
        """Handles transcription failure."""
        if self._state != AppState.TRANSCRIBING:
            logger.debug(f"Ignoring transcription failed signal in state: {self._state}")
            return

        logger.warning(f"Fallo en transcripción: {error}")
        self._set_state(AppState.ERROR)
        self.status_text_updated.emit("Error en transcripción")
        self.subtext_updated.emit(error)
        self.session_error.emit(error)

        # Programar retorno a IDLE tras 2 segundos
        QTimer.singleShot(2000, self._return_to_idle)

    def cancel_dictation(self) -> None:
        """Aborts active recording or transcription and returns to IDLE."""
        if self._state == AppState.IDLE:
            return

        logger.info("Cancelando sesión de dictado.")
        self._audio_recorder.stop()

        if self._worker is not None:
            try:
                self._worker.status_changed.disconnect()
                self._worker.finished.disconnect()
                self._worker.failed.disconnect()
            except Exception:
                pass

            if hasattr(self._worker, "isRunning") and self._worker.isRunning():
                self._worker.quit()
            self._worker = None

        self._set_state(AppState.IDLE)
        self.status_text_updated.emit("Dictado cancelado")
        self.subtext_updated.emit(f"Presiona {self.current_hotkey} para comenzar")
        self.amplitude_updated.emit(0.0)

    def update_hotkey(self, new_hotkey: str) -> tuple[bool, str]:
        """Registers a new hotkey and updates subtext if session is active."""
        if self._hotkey_manager is None:
            return False, "HotkeyManager no disponible"

        success, msg = self._hotkey_manager.update_hotkey(new_hotkey)
        if success:
            current = self.current_hotkey
            self.hotkey_updated.emit(current)
            if self._state == AppState.LISTENING:
                self.subtext_updated.emit(f"{current} para finalizar")
            elif self._state == AppState.PAUSED:
                self.subtext_updated.emit(f"Vuelve a hablar o usa {current} para finalizar")
            elif self._state == AppState.IDLE:
                self.subtext_updated.emit(f"Presiona {current} para comenzar")
        return success, msg

    def restore_default_hotkey(self) -> tuple[bool, str]:
        """Restores application default hotkey."""
        return self.update_hotkey(DEFAULT_HOTKEY)

    def _on_amplitude_updated(self, amplitude: float) -> None:
        """Forwards amplitude updates from audio recorder."""
        self.amplitude_updated.emit(amplitude)

    def _on_recording_error(self, err_msg: str) -> None:
        """Handles runtime errors from audio recorder."""
        logger.error(f"Error en audio recorder: {err_msg}")
        self._set_state(AppState.ERROR)
        self.status_text_updated.emit("Error de audio")
        self.subtext_updated.emit(err_msg)
        self.session_error.emit(err_msg)
        QTimer.singleShot(2000, self._return_to_idle)

    def _return_to_idle(self) -> None:
        """Resets state to IDLE if in terminal state."""
        if self._state in (AppState.DONE, AppState.ERROR):
            self._set_state(AppState.IDLE)
            self.status_text_updated.emit("Listo para dictar")
            self.subtext_updated.emit(f"Presiona {self.current_hotkey} para comenzar")
            self.amplitude_updated.emit(0.0)

    def cleanup(self) -> None:
        """Releases audio and hotkey resources cleanly."""
        self.cancel_dictation()
        if self._audio_recorder is not None:
            try:
                self._audio_recorder.cleanup()
            except Exception as e:
                logger.warning(f"Error limpiando audio recorder: {e}")
        if self._hotkey_manager is not None:
            try:
                self._hotkey_manager.cleanup()
            except Exception as e:
                logger.warning(f"Error limpiando hotkey manager: {e}")
