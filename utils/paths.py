from pathlib import Path
import os


def get_app_data_dir() -> Path:
    """Returns the base app data directory (%LOCALAPPDATA%\\VoiceDictation) and ensures it exists."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data)
    else:
        base_dir = Path.home() / "AppData" / "Local"
    app_dir = base_dir / "VoiceDictation"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_models_dir() -> Path:
    """Returns the directory for speech models and ensures it exists."""
    models_dir = get_app_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_logs_dir() -> Path:
    """Returns the directory for application logs and ensures it exists."""
    logs_dir = get_app_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_assets_dir() -> Path:
    """Returns the project's assets directory."""
    # Project root is one level above utils
    project_root = Path(__file__).resolve().parent.parent
    assets_dir = project_root / "assets"
    return assets_dir
