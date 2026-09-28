import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from audio.devices import AudioDevices
from audio.vad import VADEngine
from audio.recorder import AudioRecorder


@pytest.fixture(scope="session")
def qapp():
    """Ensure a QApplication instance exists for Qt Signal tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ============================================================================
# 1. AudioDevices Tests
# ============================================================================

def test_devices_enumeration_real_or_mocked():
    """Test get_input_devices returns expected dictionary keys."""
    devices = AudioDevices.get_input_devices()
    assert isinstance(devices, list)
    for dev in devices:
        assert "index" in dev
        assert "name" in dev
        assert "channels" in dev
        assert "default_samplerate" in dev
        assert "is_default" in dev
        assert dev["channels"] > 0


def test_devices_enumeration_mocked():
    """Test get_input_devices with a controlled mock device list."""
    mock_devs = [
        {"name": "Mic 1", "max_input_channels": 2, "default_samplerate": 44100.0},
        {"name": "Output 1", "max_input_channels": 0, "default_samplerate": 48000.0},
        {"name": "Mic 2", "max_input_channels": 1, "default_samplerate": 16000.0},
    ]
    with patch("sounddevice.query_devices", return_value=mock_devs), \
         patch("sounddevice.default.device", [2, 1]):
        devs = AudioDevices.get_input_devices()
        assert len(devs) == 2
        assert devs[0]["index"] == 0
        assert devs[0]["channels"] == 2
        assert devs[0]["is_default"] is False

        assert devs[1]["index"] == 2
        assert devs[1]["channels"] == 1
        assert devs[1]["is_default"] is True


def test_devices_get_default():
    """Test get_default_input_device returns the marked default device."""
    mock_devs = [
        {"name": "Mic 1", "max_input_channels": 2, "default_samplerate": 44100.0},
        {"name": "Mic 2", "max_input_channels": 1, "default_samplerate": 16000.0},
    ]
    with patch("sounddevice.query_devices", return_value=mock_devs), \
         patch("sounddevice.default.device", [1, 0]):
        default_dev = AudioDevices.get_default_input_device()
        assert default_dev is not None
        assert default_dev["index"] == 1
        assert default_dev["name"] == "Mic 2"
        assert default_dev["is_default"] is True


def test_devices_handles_portaudio_error():
    """Test that AudioDevices returns empty list/None without crashing if sounddevice raises."""
    with patch("sounddevice.query_devices", side_effect=Exception("PortAudio error")):
        assert AudioDevices.get_input_devices() == []
        assert AudioDevices.get_default_input_device() is None


# ============================================================================
# 2. VADEngine Tests
# ============================================================================

def test_vad_init():
    """Test VADEngine initialization defaults."""
    vad = VADEngine(sample_rate=16000, silence_timeout=1.5, energy_threshold=0.015)
    assert vad.sample_rate == 16000
    assert vad.silence_timeout == 1.5
    assert vad.energy_threshold == 0.015
    assert vad.is_speaking is False


def test_vad_silence_detection():
    """Test that zero or near-zero signal is detected as silence."""
    vad = VADEngine(sample_rate=16000, energy_threshold=0.015)
    zeros = np.zeros(800, dtype=np.float32)

    is_speech, rms, auto_pause = vad.process_chunk(zeros)
    assert is_speech is False
    assert rms == 0.0
    assert auto_pause is False
    assert vad.is_speaking is False


def test_vad_speech_detection_synthetic_tone():
    """Test that synthetic voice-like sine wave triggers speech."""
    vad = VADEngine(sample_rate=16000, energy_threshold=0.015)
    t = np.linspace(0, 0.05, 800, endpoint=False)  # 50ms at 16kHz
    sine_wave = (np.sin(2 * np.pi * 300 * t) * 0.1).astype(np.float32)

    is_speech, rms, auto_pause = vad.process_chunk(sine_wave)
    assert is_speech is True
    assert rms > 0.015
    assert auto_pause is False
    assert vad.is_speaking is True


def test_vad_auto_pause_after_timeout():
    """Test that speech followed by >= 1.5s of silence triggers auto_pause."""
    vad = VADEngine(sample_rate=16000, silence_timeout=1.5, energy_threshold=0.015)

    # 1. Trigger speech (50ms of 300Hz tone)
    t = np.linspace(0, 0.05, 800, endpoint=False)
    voice = (np.sin(2 * np.pi * 300 * t) * 0.1).astype(np.float32)
    is_speech, _, auto_pause = vad.process_chunk(voice)
    assert is_speech is True
    assert vad.is_speaking is True
    assert auto_pause is False

    # 2. Feed 1.0s of silence in 50ms chunks (20 chunks of 800 samples)
    silence_chunk = np.zeros(800, dtype=np.float32)
    for _ in range(20):
        is_speech, _, auto_pause = vad.process_chunk(silence_chunk)
        assert is_speech is False
        assert auto_pause is False
        assert vad.is_speaking is True  # still within 1.5s window

    # 3. Feed another 0.5s of silence (10 chunks of 800 samples)
    triggered = False
    for _ in range(10):
        is_speech, _, auto_pause = vad.process_chunk(silence_chunk)
        if auto_pause:
            triggered = True

    assert triggered is True
    assert vad.is_speaking is False


def test_vad_resume_after_auto_pause():
    """Test that speaking again after auto-pause reactivates is_speaking."""
    vad = VADEngine(sample_rate=16000, silence_timeout=1.5, energy_threshold=0.015)
    t = np.linspace(0, 0.05, 800, endpoint=False)
    voice = (np.sin(2 * np.pi * 300 * t) * 0.1).astype(np.float32)
    silence = np.zeros(800, dtype=np.float32)

    # Voice -> Silence for 1.6s -> auto-pause
    vad.process_chunk(voice)
    for _ in range(32):
        vad.process_chunk(silence)
    assert vad.is_speaking is False

    # New voice chunk
    is_speech, _, auto_pause = vad.process_chunk(voice)
    assert is_speech is True
    assert vad.is_speaking is True
    assert auto_pause is False


def test_vad_reset():
    """Test reset clears speaking state and silence timer."""
    vad = VADEngine(sample_rate=16000, silence_timeout=1.5)
    t = np.linspace(0, 0.05, 800, endpoint=False)
    voice = (np.sin(2 * np.pi * 300 * t) * 0.1).astype(np.float32)

    vad.process_chunk(voice)
    assert vad.is_speaking is True

    vad.reset()
    assert vad.is_speaking is False
    assert vad.silence_duration == 0.0


# ============================================================================
# 3. AudioRecorder Tests
# ============================================================================

def test_recorder_initial_state(qapp):
    """Test AudioRecorder default attributes."""
    recorder = AudioRecorder(sample_rate=16000, channels=1, dtype="float32")
    assert recorder.sample_rate == 16000
    assert recorder.channels == 1
    assert recorder.dtype == "float32"
    assert recorder.is_recording() is False
    assert recorder.get_audio_duration() == 0.0


def test_recorder_start_stop(qapp):
    """Test start and stop stream lifecycle with mocked sounddevice."""
    recorder = AudioRecorder(sample_rate=16000)

    mock_stream = MagicMock()
    with patch("sounddevice.InputStream", return_value=mock_stream):
        started = recorder.start(device_index=1)
        assert started is True
        assert recorder.is_recording() is True
        mock_stream.start.assert_called_once()

        # Stop
        audio = recorder.stop()
        assert recorder.is_recording() is False
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 0


def test_recorder_audio_callback_accumulates_and_emits(qapp):
    """Test that _audio_callback accumulates audio and emits Qt signals."""
    recorder = AudioRecorder(sample_rate=16000)

    amps = []
    speeches = []
    silences = []

    recorder.amplitude_updated.connect(lambda a: amps.append(a))
    recorder.speech_detected.connect(lambda: speeches.append(True))
    recorder.silence_detected.connect(lambda s: silences.append(s))

    # Send voice chunk
    t = np.linspace(0, 0.05, 800, endpoint=False)
    voice_chunk = (np.sin(2 * np.pi * 300 * t) * 0.1).astype(np.float32).reshape(-1, 1)

    recorder._audio_callback(voice_chunk, 800, None, None)

    assert len(amps) == 1
    assert 0.0 <= amps[0] <= 1.0
    assert len(speeches) == 1
    assert recorder.get_audio_duration() == 0.05

    # Send silence chunks to trigger silence_detected (1.5s = 30 chunks of 50ms)
    silence_chunk = np.zeros((800, 1), dtype=np.float32)
    for _ in range(31):
        recorder._audio_callback(silence_chunk, 800, None, None)

    assert len(silences) >= 1
    assert silences[0] == 1.5

    # Stop and verify concatenated buffer
    audio = recorder.stop()
    assert len(audio) == 800 * 32
    assert recorder.get_audio_duration() == 0.0  # buffer cleared after stop


def test_recorder_error_signal(qapp):
    """Test start emits recording_error on exception."""
    recorder = AudioRecorder()
    errors = []
    recorder.recording_error.connect(lambda err: errors.append(err))

    with patch("sounddevice.InputStream", side_effect=RuntimeError("Device unavailable")):
        success = recorder.start()
        assert success is False
        assert recorder.is_recording() is False
        assert len(errors) == 1
        assert "Device unavailable" in errors[0]
