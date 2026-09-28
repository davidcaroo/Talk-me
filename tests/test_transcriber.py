import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from models.transcription_result import TranscriptionResult
from speech.model_manager import ModelManager
from speech.transcriber import LocalTranscriber
from workers.transcription_worker import TranscriptionWorker


@pytest.fixture(scope="session")
def qapp():
    """Ensure a QApplication instance exists for Qt Signal tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def reset_model_manager_cache():
    """Clear ModelManager memory cache between tests."""
    ModelManager.clear_cache()
    yield
    ModelManager.clear_cache()


# ============================================================================
# 1. ModelManager Tests
# ============================================================================

def test_model_manager_default_dir():
    manager = ModelManager()
    assert manager.models_dir.exists()
    assert "models" in str(manager.models_dir)


def test_is_model_cached_with_direct_folder(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    model_folder = tmp_path / "base"
    assert not manager.is_model_cached("base")

    # Create dummy model folder with model.bin
    model_folder.mkdir(parents=True)
    (model_folder / "model.bin").write_text("dummy model content")
    assert manager.is_model_cached("base")


def test_is_model_cached_with_faster_whisper_helper(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    
    # When faster_whisper.download_model succeeds
    with patch("faster_whisper.download_model", return_value=str(tmp_path / "snapshots" / "fake")):
        # Path exists mock
        with patch.object(Path, "exists", return_value=True):
            assert manager.is_model_cached("base")

    # When faster_whisper.download_model raises an exception (e.g. not found locally)
    with patch("faster_whisper.download_model", side_effect=Exception("Not cached")):
        assert not manager.is_model_cached("base")


def test_load_model_lazy_and_cached(tmp_path):
    manager = ModelManager(models_dir=tmp_path)

    mock_whisper_instance = MagicMock()
    with patch("faster_whisper.WhisperModel", return_value=mock_whisper_instance) as mock_cls:
        # First call should instantiate
        model1 = manager.load_model("base", device="cpu", compute_type="int8", cpu_threads=4)
        assert model1 == mock_whisper_instance
        mock_cls.assert_called_once_with(
            "base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            download_root=str(tmp_path),
        )

        # Second call with same parameters should return cached instance without re-instantiating
        model2 = manager.load_model("base", device="cpu", compute_type="int8", cpu_threads=4)
        assert model2 == mock_whisper_instance
        assert mock_cls.call_count == 1


# ============================================================================
# 2. LocalTranscriber Tests
# ============================================================================

def test_local_transcriber_success():
    mock_model = MagicMock()
    mock_seg1 = MagicMock(text=" Hola ")
    mock_seg2 = MagicMock(text=" mundo ")
    mock_info = MagicMock(language="es")
    mock_model.transcribe.return_value = ([mock_seg1, mock_seg2], mock_info)

    mock_manager = MagicMock()
    mock_manager.load_model.return_value = mock_model

    transcriber = LocalTranscriber(model_manager=mock_manager)
    audio = np.zeros(16000, dtype=np.float32)

    result = transcriber.transcribe(audio, language="es", model_name="base")

    assert isinstance(result, TranscriptionResult)
    assert result.success is True
    assert result.text == "Hola mundo"
    assert result.language == "es"
    assert result.duration >= 0.0
    assert result.error is None

    mock_model.transcribe.assert_called_once_with(
        audio,
        language="es",
        beam_size=1,
        temperature=0.0,
        condition_on_previous_text=False,
    )


def test_local_transcriber_error_handling():
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("Inference memory fault")

    mock_manager = MagicMock()
    mock_manager.load_model.return_value = mock_model

    transcriber = LocalTranscriber(model_manager=mock_manager)
    audio = np.zeros(16000, dtype=np.float32)

    result = transcriber.transcribe(audio, language="es", model_name="base")

    assert isinstance(result, TranscriptionResult)
    assert result.success is False
    assert result.text == ""
    assert "Inference memory fault" in result.error
    assert result.duration == 0.0


# ============================================================================
# 3. TranscriptionWorker Tests
# ============================================================================

def test_transcription_worker_uncached_lifecycle(qapp):
    mock_manager = MagicMock()
    mock_manager.is_model_cached.return_value = False

    mock_transcriber = MagicMock()
    expected_result = TranscriptionResult(text="Transcripción de prueba", duration=0.45, language="es", success=True)
    mock_transcriber.transcribe.return_value = expected_result

    audio_data = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=audio_data,
        model_name="base",
        language="es",
        model_manager=mock_manager,
        transcriber=mock_transcriber,
    )

    statuses = []
    results = []
    failures = []

    worker.status_changed.connect(statuses.append)
    worker.finished.connect(results.append)
    worker.failed.connect(failures.append)

    # Run synchronously in test
    worker.run()

    assert "Descargando modelo de voz (única vez)..." in statuses
    assert "Transcribiendo..." in statuses
    assert len(results) == 1
    assert results[0] == expected_result
    assert len(failures) == 0


def test_transcription_worker_cached_lifecycle(qapp):
    mock_manager = MagicMock()
    mock_manager.is_model_cached.return_value = True

    mock_transcriber = MagicMock()
    expected_result = TranscriptionResult(text="Todo listo", duration=0.2, language="es", success=True)
    mock_transcriber.transcribe.return_value = expected_result

    audio_data = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=audio_data,
        model_name="base",
        language="es",
        model_manager=mock_manager,
        transcriber=mock_transcriber,
    )

    statuses = []
    results = []

    worker.status_changed.connect(statuses.append)
    worker.finished.connect(results.append)

    worker.run()

    assert "Preparando motor de dictado..." not in statuses
    assert "Transcribiendo..." in statuses
    assert len(results) == 1
    assert results[0].text == "Todo listo"


def test_transcription_worker_failure(qapp):
    mock_manager = MagicMock()
    mock_manager.is_model_cached.return_value = True

    mock_transcriber = MagicMock()
    failed_result = TranscriptionResult(text="", duration=0.0, language="es", success=False, error="Error de modelo")
    mock_transcriber.transcribe.return_value = failed_result

    audio_data = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=audio_data,
        model_name="base",
        language="es",
        model_manager=mock_manager,
        transcriber=mock_transcriber,
    )

    failures = []
    worker.failed.connect(failures.append)

    worker.run()

    assert len(failures) == 1
    assert "Error de modelo" in failures[0]


def test_transcription_worker_exception_in_run(qapp):
    mock_manager = MagicMock()
    mock_manager.is_model_cached.side_effect = Exception("Crash inesperado")

    audio_data = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=audio_data,
        model_name="base",
        language="es",
        model_manager=mock_manager,
    )

    failures = []
    worker.failed.connect(failures.append)

    worker.run()

    assert len(failures) == 1
    assert "Crash inesperado" in failures[0]


# ============================================================================
# 4. Synthetic Audio Pipeline Test
# ============================================================================

def test_synthetic_audio_pipeline():
    """Verify that a synthetic audio buffer runs through LocalTranscriber with expected types."""
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Probando audio sintético"
    mock_info = MagicMock()
    mock_info.language = "es"
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    mock_manager = MagicMock()
    mock_manager.load_model.return_value = mock_model

    transcriber = LocalTranscriber(model_manager=mock_manager)

    # 1 second of 440Hz sine wave at 16kHz
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)

    res = transcriber.transcribe(audio, language="es")
    assert res.success is True
    assert res.text == "Probando audio sintético"
    assert res.duration >= 0.0
