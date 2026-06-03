$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== YouTube Thumbnails Downloader ===" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка существования venv
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Venv not found. Creating a new one..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "[OK] venv создан." -ForegroundColor Green
    Write-Host ""
}

# 2. Проверка активного окружения venv
$inVenv = python -c "import sys; exit(0 if sys.prefix != sys.base_prefix else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] You are already inside the venv" -ForegroundColor Green
} else {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
    . venv\Scripts\Activate.ps1
    Write-Host "[OK] venv activated" -ForegroundColor Green
}
Write-Host ""

# 3. Установка и обновление зависимостей (Добавлен pillow для конвертации картинки в .jpg)
Write-Host "[INFO] Installing/Updating yt-dlp and pillow..." -ForegroundColor Yellow
pip install -U yt-dlp pillow > $null 2>&1
Write-Host "[OK] Dependencies are ready." -ForegroundColor Green
Write-Host ""

# 4. Запуск скрипта
Write-Host "[INFO] Starting the script..." -ForegroundColor Yellow
Write-Host ""

if ($args.Count -gt 0) {
    python download_thumbnails.py $args[0]
} else {
    python download_thumbnails.py
}

Write-Host ""
Write-Host "[INFO] Done. Press any key to exit..." -ForegroundColor Cyan
[void][Console]::ReadKey($true)