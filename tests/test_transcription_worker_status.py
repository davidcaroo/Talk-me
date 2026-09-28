import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from models.transcription_result import TranscriptionResult
from speech.model_manager import ModelManager
from speech.transcriber import LocalTranscriber
from workers.transcription_worker import TranscriptionWorker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_worker_emits_downloading_when_model_not_cached(qapp):
    mock_mgr = MagicMock(spec=ModelManager)
    mock_mgr.is_model_cached.return_value = False

    mock_transcriber = MagicMock(spec=LocalTranscriber)
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="Prueba",
        duration=0.5,
        language="es",
        success=True,
    )

    dummy_audio = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=dummy_audio,
        model_name="base",
        language="es",
        model_manager=mock_mgr,
        transcriber=mock_transcriber,
    )

    statuses = []
    worker.status_changed.connect(lambda s: statuses.append(s))

    worker.run()

    # Must emit downloading status before transcribing status
    assert len(statuses) >= 2
    assert "Descargando" in statuses[0]
    assert statuses[-1] == "Transcribiendo..."
    mock_mgr.load_model.assert_called_once_with(model_name="base")


def test_worker_skips_download_status_when_already_cached(qapp):
    mock_mgr = MagicMock(spec=ModelManager)
    mock_mgr.is_model_cached.return_value = True

    mock_transcriber = MagicMock(spec=LocalTranscriber)
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="Prueba",
        duration=0.5,
        language="es",
        success=True,
    )

    dummy_audio = np.zeros(16000, dtype=np.float32)
    worker = TranscriptionWorker(
        audio_data=dummy_audio,
        model_name="base",
        language="es",
        model_manager=mock_mgr,
        transcriber=mock_transcriber,
    )

    statuses = []
    worker.status_changed.connect(lambda s: statuses.append(s))

    worker.run()

    # Should not emit Descargando
    assert not any("Descargando" in s for s in statuses)
    assert statuses[-1] == "Transcribiendo..."
