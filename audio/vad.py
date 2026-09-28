"""Adaptive Voice Activity Detection (VAD) engine using RMS and Zero Crossing Rate (ZCR)."""

import numpy as np


class VADEngine:
    """Voice Activity Detection engine with adaptive noise floor and auto-pause timeout."""

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_timeout: float = 1.5,
        energy_threshold: float = 0.015,
        noise_adaptation_rate: float = 0.05,
    ):
        """Initialize VAD engine.

        Args:
            sample_rate (int): Audio sample rate in Hz (default 16000).
            silence_timeout (float): Silence duration in seconds to trigger auto-pause (default 1.5s).
            energy_threshold (float): Minimum RMS energy threshold for speech (default 0.015).
            noise_adaptation_rate (float): Exponential smoothing weight for noise floor (default 0.05).
        """
        self.sample_rate = sample_rate
        self.silence_timeout = silence_timeout
        self.energy_threshold = energy_threshold
        self.noise_adaptation_rate = noise_adaptation_rate

        self.noise_floor = energy_threshold * 0.3
        self.is_speaking = False
        self.silence_duration = 0.0
        self.last_rms = 0.0
        self.last_zcr = 0.0

    def reset(self) -> None:
        """Reset internal speech state and silence timer."""
        self.is_speaking = False
        self.silence_duration = 0.0
        self.last_rms = 0.0
        self.last_zcr = 0.0

    def process_chunk(self, chunk: np.ndarray) -> tuple[bool, float, bool]:
        """Process a single audio chunk and return VAD status.

        Args:
            chunk (np.ndarray): 1D float32 audio chunk.

        Returns:
            tuple[bool, float, bool]:
                - is_speech (bool): True if speech detected in this chunk.
                - rms_amplitude (float): Root mean square amplitude of the chunk.
                - auto_pause_triggered (bool): True if silence timeout reached while speaking.
        """
        if chunk is None or len(chunk) == 0:
            return False, 0.0, False

        if chunk.ndim > 1:
            chunk = chunk.flatten()

        # 1. Compute RMS amplitude: np.sqrt(np.mean(chunk**2))
        squared_mean = np.mean(chunk.astype(np.float64) ** 2)
        rms = float(np.sqrt(squared_mean))
        self.last_rms = rms

        # 2. Compute Zero-Crossing Rate (ZCR): np.mean(np.abs(np.diff(np.sign(chunk)))) / 2
        if len(chunk) > 1:
            signs = np.sign(chunk)
            diffs = np.diff(signs)
            zcr = float(np.mean(np.abs(diffs)) / 2.0)
        else:
            zcr = 0.0
        self.last_zcr = zcr

        # 3. Dynamic Thresholding (Adaptive Noise Floor)
        dynamic_threshold = max(self.energy_threshold, self.noise_floor * 1.8)

        # Human voice typically has ZCR < 0.70; very high ZCR (> 0.70) is HF noise/hiss
        chunk_is_speech = (rms >= dynamic_threshold) and (zcr < 0.70)

        chunk_duration = len(chunk) / self.sample_rate if self.sample_rate > 0 else 0.0
        auto_pause_triggered = False

        if chunk_is_speech:
            self.is_speaking = True
            self.silence_duration = 0.0
        else:
            if self.is_speaking:
                self.silence_duration += chunk_duration
                if self.silence_duration >= self.silence_timeout:
                    self.is_speaking = False
                    auto_pause_triggered = True
                    self.silence_duration = 0.0
            else:
                # Update adaptive noise floor smoothly during ambient silence
                clamped_rms = min(rms, self.energy_threshold)
                self.noise_floor = (
                    (1.0 - self.noise_adaptation_rate) * self.noise_floor
                    + self.noise_adaptation_rate * clamped_rms
                )

        return chunk_is_speech, rms, auto_pause_triggered
