import time
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication

from speech.model_manager import ModelManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_preload_model_async_loads_model_in_background(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    
    mock_model = MagicMock()
    with patch.object(manager, "is_model_cached", return_value=True), \
         patch.object(manager, "load_model", return_value=mock_model) as mock_load:
        
        thread = manager.preload_model_async("base")
        assert thread is not None
        thread.join(timeout=2.0)
        
        mock_load.assert_called_once_with(
            model_name="base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
        )


def test_preload_model_async_skips_if_not_cached(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    
    with patch.object(manager, "is_model_cached", return_value=False), \
         patch.object(manager, "load_model") as mock_load:
        
        thread = manager.preload_model_async("base")
        assert thread is not None
        thread.join(timeout=2.0)
        
        mock_load.assert_not_called()


def test_main_window_triggers_model_warmup(qapp):
    from app.main_window import MainWindow
    from utils.config import ConfigManager

    mock_mgr = MagicMock()
    mock_config = MagicMock(spec=ConfigManager)
    mock_config.get_model_name.return_value = "base"
    mock_config.is_first_run.return_value = True

    window = MainWindow(
        config_manager=mock_config,
        model_manager=mock_mgr,
    )
    window.start()

    mock_mgr.preload_model_async.assert_called_once_with(model_name="base")

