"""Local audio transcriber wrapping faster-whisper."""

import time
from typing import Optional
import numpy as np

from models.transcription_result import TranscriptionResult
from speech.model_manager import ModelManager
from utils.logger import get_logger

logger = get_logger("speech.transcriber")


class LocalTranscriber:
    """Performs local speech-to-text transcription using faster-whisper."""

    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager if model_manager is not None else ModelManager()

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "es",
        model_name: str = "base",
    ) -> TranscriptionResult:
        """Transcribes raw audio array using the configured Whisper model.

        Fast, real-time configuration:
        - beam_size=1 (greedy search)
        - temperature=0.0 (deterministic)
        - condition_on_previous_text=False (no halluncinations from previous text)

        Args:
            audio: 1D numpy array of 16kHz float32 audio samples.
            language: Target language code ('es', 'en', etc.).
            model_name: Whisper model size/name ('base', 'tiny', etc.).

        Returns:
            TranscriptionResult with transcribed text, duration and status.
        """
        start_time = time.perf_counter()
        try:
            model = self.model_manager.load_model(model_name=model_name)
            logger.debug(
                f"Iniciando transcripción (longitud audio: {len(audio)} muestras, "
                f"idioma: {language}, modelo: {model_name})..."
            )

            segments, _ = model.transcribe(
                audio,
                language=language,
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
            )

            # Iterate over generator to execute inference and clean up text
            parts = [s.text.strip() for s in segments if s.text and s.text.strip()]
            text = " ".join(parts).strip()
            duration = time.perf_counter() - start_time

            logger.info(f"Transcripción completada en {duration:.2f}s: '{text}'")
            return TranscriptionResult(
                text=text,
                duration=duration,
                language=language,
                success=True,
                error=None,
            )
        except Exception as e:
            logger.error(f"Error durante la transcripción de audio: {e}", exc_info=True)
            return TranscriptionResult(
                text="",
                duration=0.0,
                language=language,
                success=False,
                error=str(e),
            )
