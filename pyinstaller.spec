# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for Voice Dictation.

Produces a lightweight standalone Windows executable (VoiceDictation.exe)
with native windowed mode, visionOS-styled icon, dynamic libraries, and
without embedding heavy Whisper models (models are stored in %LOCALAPPDATA%).
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

block_cipher = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Data files: include assets/ (icons, sounds, etc.)
# NOTE: Whisper models are intentionally NOT bundled here. They are downloaded
# on-demand into %LOCALAPPDATA%\\VoiceDictation\\models\\ to maintain a compact binary.
datas = [
    (os.path.join(BASE_DIR, 'assets'), 'assets'),
]

try:
    datas += collect_data_files('faster_whisper')
except Exception:
    pass

# Dynamic libraries for ctranslate2 (OpenBLAS / Intel MKL runtime)
binaries = []
try:
    binaries += collect_dynamic_libs('ctranslate2')
except Exception:
    pass

# Explicit hidden imports for dynamic imports and runtime dependencies
hiddenimports = [
    'faster_whisper',
    'ctranslate2',
    'sounddevice',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'pyperclip',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'app',
    'app.overlay',
    'app.tray',
    'app.settings_window',
    'app.first_run',
    'app.main_window',
    'audio',
    'controllers',
    'input',
    'models',
    'speech',
    'utils',
    'workers',
]

# Excluded bloated libraries to ensure maximum lightness
excludes = [
    'matplotlib',
    'pandas',
    'scipy',
    'tkinter',
    'IPython',
    'notebook',
    'jupyter',
    'selenium',
    'sqlite3',
    'test',
    'unittest',
    'xmlrpc',
    'pip',
    'setuptools',
]

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VoiceDictation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'icons', 'app_icon.ico'),
)
