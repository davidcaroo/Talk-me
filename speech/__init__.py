"""Speech transcription package using faster-whisper."""

from speech.model_manager import ModelManager
from speech.transcriber import LocalTranscriber

__all__ = ["ModelManager", "LocalTranscriber"]
