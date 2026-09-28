@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo         Voice Dictation - Release Build Script
echo =======================================================
echo.

:: 1. Generate icons
echo [1/3] Generating application icons...
python assets\icons\generate_icon.py
if errorlevel 1 (
    echo [ERROR] Failed to generate icons.
    exit /b 1
)

:: 2. Build executable with PyInstaller
echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller pyinstaller.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

if not exist "dist\VoiceDictation.exe" (
    echo [ERROR] Expected output dist\VoiceDictation.exe not found.
    exit /b 1
)
echo [SUCCESS] Executable generated: dist\VoiceDictation.exe

:: 3. Compile Inno Setup installer
echo.
echo [3/3] Compiling Inno Setup installer...

set "ISCC_EXE="

:: Check if ISCC is in PATH
where iscc >nul 2>nul
if %errorlevel% equ 0 (
    set "ISCC_EXE=iscc"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if defined ISCC_EXE (
    echo Found Inno Setup Compiler at: "!ISCC_EXE!"
    "!ISCC_EXE!" installer.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed.
        exit /b 1
    )
    echo [SUCCESS] Setup installer built in dist\installer\
) else (
    echo [WARNING] Inno Setup 6 (ISCC.exe) was not found in PATH or standard Program Files.
    echo If you wish to build the installer setup, please install Inno Setup 6 or add ISCC to PATH.
    echo The standalone binary is ready at: dist\VoiceDictation.exe
)

echo.
echo =======================================================
echo                 Build Completed!
echo =======================================================
exit /b 0
