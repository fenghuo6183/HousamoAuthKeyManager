@echo off
setlocal
cd /d "%~dp0"

echo [1/2] Installing PyInstaller...
python -m pip install --upgrade pyinstaller || goto :err

echo [2/2] Building AuthKeyManager.exe...
python -m PyInstaller --noconfirm --clean --windowed --name AuthKeyManager --add-data "assets/platform-tools;assets/platform-tools" main.py || goto :err

echo.
echo Build finished: dist\AuthKeyManager\AuthKeyManager.exe
goto :eof

:err
echo Build failed.
exit /b 1
