@echo off
chcp 65001 >nul
echo ========================================
echo 트위캐스트 방송 감시 프로그램 빌드
echo ========================================
echo.

REM 의존성 설치
echo [1/3] 의존성 설치 중...
uv sync
if errorlevel 1 (
    echo 오류: 의존성 설치 실패
    pause
    exit /b 1
)
echo 의존성 설치 완료!
echo.

REM PyInstaller로 빌드
echo [2/3] EXE 파일 빌드 중...
uv run pyinstaller --clean build.spec
if errorlevel 1 (
    echo 오류: 빌드 실패
    pause
    exit /b 1
)
echo 빌드 완료!
echo.

REM 결과 확인
echo [3/3] 빌드 결과:
echo 실행 파일 위치: dist\TwitCastingMonitor.exe
echo.
echo ========================================
echo 빌드 완료!
echo ========================================
pause
