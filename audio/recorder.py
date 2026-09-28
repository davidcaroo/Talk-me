"""Audio stream recorder with real-time VAD processing and Qt signal emission."""

import logging
import threading
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from audio.vad import VADEngine

logger = logging.getLogger(__name__)


class AudioRecorder(QObject):
    """Captures microphone audio via sounddevice and runs real-time VAD detection.

    Signals:
        amplitude_updated (Signal(float)): Normalized amplitude (0.0 to 1.0) for WaveformView.
        speech_detected (Signal()): Emitted when speech activity starts or resumes.
        silence_detected (Signal(float)): Emitted when silence timeout (1.5s) is reached.
        recording_error (Signal(str)): Emitted when audio stream encounters an error.
    """

    amplitude_updated = Signal(float)
    speech_detected = Signal()
    silence_detected = Signal(float)
    recording_error = Signal(str)

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
        blocksize: int = 800,
        vad_engine: VADEngine | None = None,
        parent: QObject | None = None,
    ):
        """Initialize AudioRecorder.

        Args:
            sample_rate (int): Sampling rate in Hz (default 16000).
            channels (int): Channel count, mono=1 (default 1).
            dtype (str): Sample data type (default 'float32').
            blocksize (int): Frame buffer block size (default 800 samples = 50ms at 16kHz).
            vad_engine (VADEngine | None): Custom VADEngine instance or None to instantiate default.
            parent (QObject | None): Optional Qt parent.
        """
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.blocksize = blocksize

        self.vad = vad_engine or VADEngine(sample_rate=sample_rate)

        self._buffer: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._is_recording = False
        self._speech_active = False
        self._lock = threading.Lock()

    def start(self, device_index: int | None = None) -> bool:
        """Start capturing audio stream from specified device.

        Args:
            device_index (int | None): Device index or None for default device.

        Returns:
            bool: True if started successfully, False otherwise.
        """
        if self._is_recording:
            return True

        self.stop()

        try:
            self._stream = sd.InputStream(
                device=device_index,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._is_recording = True
            logger.info(f"Audio recording started on device index {device_index}")
            return True
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self._is_recording = False
            self.recording_error.emit(str(e))
            return False

    def stop(self) -> np.ndarray:
        """Stop capturing audio and return concatenated 1D float32 audio buffer.

        Returns:
            np.ndarray: Concatenated float32 audio buffer.
        """
        with self._lock:
            if self._stream is not None:
                try:
                    if hasattr(self._stream, "active") and self._stream.active:
                        self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.warning(f"Error closing audio stream: {e}")
                finally:
                    self._stream = None

            self._is_recording = False
            self._speech_active = False
            self.vad.reset()

            if self._buffer:
                recorded_audio = np.concatenate(self._buffer).astype(np.float32)
                self._buffer.clear()
            else:
                recorded_audio = np.zeros(0, dtype=np.float32)

        logger.info(f"Audio recording stopped, captured {len(recorded_audio)} samples")
        return recorded_audio

    def is_recording(self) -> bool:
        """Return True if currently capturing audio stream."""
        return self._is_recording

    def get_audio_duration(self) -> float:
        """Return total duration in seconds of audio captured in the current session."""
        with self._lock:
            total_samples = sum(len(b) for b in self._buffer)
        return total_samples / self.sample_rate if self.sample_rate > 0 else 0.0

    def cleanup(self) -> None:
        """Release audio stream resources."""
        self.stop()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        """Internal sounddevice stream callback."""
        if status:
            logger.debug(f"Audio stream status flag: {status}")

        if indata.ndim > 1:
            chunk = indata[:, 0].copy().astype(np.float32)
        else:
            chunk = indata.flatten().copy().astype(np.float32)

        with self._lock:
            self._buffer.append(chunk)

        # Process with VAD
        chunk_is_speech, rms, auto_pause = self.vad.process_chunk(chunk)

        # Normalize amplitude to [0.0, 1.0] for Waveform visualizer
        norm_amplitude = min(1.0, max(0.0, float(rms * 4.0)))
        self.amplitude_updated.emit(norm_amplitude)

        # Trigger speech detected signal on rising edge
        if chunk_is_speech:
            if not self._speech_active:
                self._speech_active = True
                self.speech_detected.emit()

        # Trigger auto-pause silence detected signal
        if auto_pause:
            self._speech_active = False
            self.silence_detected.emit(self.vad.silence_timeout)
