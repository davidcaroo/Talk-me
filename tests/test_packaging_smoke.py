"""Packaging smoke tests for Voice Dictation (PyInstaller & Inno Setup)."""

import ast
import os
import sys
from pathlib import Path
from PIL import Image
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_icon_generation_and_properties():
    """Verify that assets/icons/app_icon.ico and app_icon.png exist and have correct formats and sizes."""
    icon_dir = REPO_ROOT / "assets" / "icons"
    ico_path = icon_dir / "app_icon.ico"
    png_path = icon_dir / "app_icon.png"
    gen_script = icon_dir / "generate_icon.py"

    assert gen_script.is_file(), f"Icon generator script not found at {gen_script}"
    assert ico_path.is_file(), f"Icon file not found at {ico_path}"
    assert png_path.is_file(), f"PNG icon not found at {png_path}"

    # Verify PNG size
    with Image.open(png_path) as img:
        assert img.format == "PNG"
        assert img.size == (256, 256)
        assert img.mode in ("RGBA", "RGB")

    # Verify ICO sizes
    with Image.open(ico_path) as ico:
        assert ico.format == "ICO"
        sizes = getattr(ico, "_sizes", set()) or ico.info.get("sizes", set())
        if not sizes:
            sizes = set()
            try:
                frame = 0
                while True:
                    ico.seek(frame)
                    sizes.add(ico.size)
                    frame += 1
            except EOFError:
                pass

        required_sizes = {(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
        assert required_sizes.issubset(sizes), f"ICO missing required sizes: {required_sizes - sizes}"


def test_generate_icon_programmatic(tmp_path):
    """Verify generate_icon module functions execute cleanly and write output to target dir."""
    sys.path.insert(0, str(REPO_ROOT / "assets" / "icons"))
    try:
        from generate_icon import create_visionos_mic_icon, generate_all_icons

        master = create_visionos_mic_icon(size=512)
        assert master.size == (512, 512)
        assert master.mode == "RGBA"

        ico_out, png_out = generate_all_icons(target_dir=tmp_path)
        assert ico_out.is_file()
        assert png_out.is_file()
        assert ico_out.stat().st_size > 0
        assert png_out.stat().st_size > 0
    finally:
        if str(REPO_ROOT / "assets" / "icons") in sys.path:
            sys.path.remove(str(REPO_ROOT / "assets" / "icons"))


def test_pyinstaller_spec_configuration():
    """Verify pyinstaller.spec file syntax, entry points, and bundle parameters."""
    spec_path = REPO_ROOT / "pyinstaller.spec"
    assert spec_path.is_file(), f"pyinstaller.spec not found at {spec_path}"

    content = spec_path.read_text(encoding="utf-8")

    # Verify spec can be parsed as valid Python AST
    tree = ast.parse(content, filename=str(spec_path))
    assert tree is not None

    # Verify key configurations in spec
    assert "VoiceDictation" in content, "VoiceDictation executable name not configured in spec"
    assert "console=False" in content, "console=False must be specified for GUI window mode"
    assert "app_icon.ico" in content, "app_icon.ico must be configured as executable icon"

    # Verify hiddenimports
    expected_imports = [
        "faster_whisper",
        "ctranslate2",
        "sounddevice",
        "pynput",
        "pyperclip",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ]
    for imp in expected_imports:
        assert imp in content, f"Hidden import {imp} missing from pyinstaller.spec"

    # Verify bloated package exclusions
    expected_excludes = ["matplotlib", "pandas", "scipy", "tkinter"]
    for exc in expected_excludes:
        assert exc in content, f"Exclusion {exc} missing from pyinstaller.spec"

    # Verify whisper models are NOT bundled in datas
    assert "models/" not in content.lower() or "not bundle" in content.lower() or "models" not in content, (
        "Whisper models must not be bundled in executable datas"
    )


def test_installer_iss_configuration():
    """Verify Inno Setup 6 installer script configuration."""
    iss_path = REPO_ROOT / "installer.iss"
    assert iss_path.is_file(), f"installer.iss not found at {iss_path}"

    content = iss_path.read_text(encoding="utf-8")

    # Inno Setup directives
    assert "Voice Dictation" in content, "App name 'Voice Dictation' missing"
    assert "1.0.0" in content, "Version 1.0.0 missing"
    assert "David Caro" in content, "Publisher missing"
    assert "autopf" in content, "autopf base directory missing"
    assert "VoiceDictation.exe" in content, "Target executable VoiceDictation.exe missing"
    assert "tasks: desktopicon" in content.lower() or "desktopicon" in content, "Desktop shortcut missing"
    assert "startupicon" in content, "Startup icon / Windows autostart option missing"
    assert "[Run]" in content, "[Run] section missing"
    assert "[UninstallDelete]" in content, "[UninstallDelete] section missing"


def test_build_release_bat_exists_and_configured():
    """Verify build_release.bat script exists and contains build steps."""
    bat_path = REPO_ROOT / "build_release.bat"
    assert bat_path.is_file(), f"build_release.bat not found at {bat_path}"

    content = bat_path.read_text(encoding="utf-8")
    assert "pyinstaller" in content.lower()
    assert "pyinstaller.spec" in content.lower()
    assert "iscc" in content.lower() or "inno" in content.lower()
    assert "assets\\icons\\generate_icon.py" in content or "generate_icon.py" in content
