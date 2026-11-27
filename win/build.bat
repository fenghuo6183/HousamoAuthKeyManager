@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing build dependencies...
python -m pip install --upgrade pyinstaller pillow || goto :err

echo [2/3] Checking assets...
if not exist "assets\platform-tools\adb.exe" (
  echo WARNING: assets\platform-tools\adb.exe not found.
  echo          Run: python tools\fetch_toolchain.py
)
if not exist "..\docs\icon.png" echo WARNING: ..\docs\icon.png not found.

echo [3/3] Building AuthKeyManager.exe...
python -m PyInstaller --noconfirm --clean --windowed --name AuthKeyManager ^
  --icon "..\docs\icon.png" ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import app.updater ^
  --add-data "assets\platform-tools;assets\platform-tools" ^
  --add-data "..\docs\icon.png;assets" ^
  main.py || goto :err

echo.
echo Build finished: dist\AuthKeyManager\AuthKeyManager.exe
goto :eof

:err
echo Build failed.
exit /b 1
