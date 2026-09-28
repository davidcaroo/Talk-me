"""Background worker thread for asynchronous transcription."""

from typing import Optional
import numpy as np
from PySide6.QtCore import QThread, Signal

from models.transcription_result import TranscriptionResult
from speech.model_manager import ModelManager
from speech.transcriber import LocalTranscriber
from utils.logger import get_logger

logger = get_logger("workers.transcription_worker")


class TranscriptionWorker(QThread):
    """QThread worker that processes audio in the background without blocking the UI."""

    status_changed = Signal(str)
    finished = Signal(object)  # Emits TranscriptionResult
    failed = Signal(str)  # Emits error message

    def __init__(
        self,
        audio_data: np.ndarray,
        model_name: str = "base",
        language: str = "es",
        parent=None,
        model_manager: Optional[ModelManager] = None,
        transcriber: Optional[LocalTranscriber] = None,
    ):
        super().__init__(parent)
        self.audio_data = audio_data
        self.model_name = model_name
        self.language = language
        self.model_manager = model_manager if model_manager is not None else ModelManager()
        self.transcriber = (
            transcriber
            if transcriber is not None
            else LocalTranscriber(model_manager=self.model_manager)
        )

    def run(self) -> None:
        """Executes transcription in background thread and emits status / results."""
        try:
            # Clean any stale locks before starting
            self.model_manager.clean_stale_locks()

            # Notify download status if model needs downloading
            if not self.model_manager.is_model_cached(self.model_name):
                logger.info(f"Modelo '{self.model_name}' no cacheado. Descargando...")
                self.status_changed.emit("Descargando modelo de voz (única vez)...")

            # Ensure model is loaded into memory before starting audio inference
            self.model_manager.load_model(model_name=self.model_name)

            self.status_changed.emit("Transcribiendo...")
            result = self.transcriber.transcribe(
                self.audio_data,
                language=self.language,
                model_name=self.model_name,
            )

            if result.success:
                self.finished.emit(result)
            else:
                error_msg = result.error or "Error desconocido durante la transcripción"
                logger.warning(f"Transcripción no exitosa: {error_msg}")
                self.failed.emit(error_msg)
        except Exception as e:
            logger.error(f"Excepción no controlada en TranscriptionWorker: {e}", exc_info=True)
            self.failed.emit(str(e))
