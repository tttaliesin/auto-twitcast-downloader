@echo off
chcp 65001 >nul

echo ========================================
echo TwitCasting Monitor Build
echo ========================================
echo.

echo [1/3] Installing dependencies...
uv sync
if errorlevel 1 (
    echo ERROR: dependency install failed
    pause
    exit /b 1
)
echo Done!
echo.

echo [2/3] Building EXE...
uv run pyinstaller --clean build.spec
if errorlevel 1 (
    echo ERROR: build failed
    pause
    exit /b 1
)
echo Done!
echo.

echo [3/3] Build result:
echo dist\TwitCastingMonitor.exe
echo ========================================
pause
