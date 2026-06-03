@echo off
echo === YouTube Thumbnails Downloader ===
echo.

:: Проверка существования venv
if not exist venv (
    echo [INFO] Venv not found. Create new one...
    python -m venv venv
    echo [OK] venv создан.
    echo.
)

:: Проверка, активировано ли venv уже
python -c "import sys; exit(0 if sys.prefix != sys.base_prefix else 1)" >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] You are already inside the venv
) else (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate
    echo [OK] venv activated
)
echo.

:: Установка/обновление зависимостей (добавлен pillow)
echo [INFO] Installing/Updating yt-dlp and pillow...
pip install -U yt-dlp pillow >nul 2>&1
echo [OK] Dependencies are ready.
echo.

:: Запуск скрипта
echo [INFO] Starting the script...
echo.
python download_thumbnails.py %1

echo.
echo [INFO] Done. Press any key to exit...
pause >nul