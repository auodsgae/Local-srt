$ErrorActionPreference = "Stop"

python -m pip install -U pip
python -m pip install -e ".[dev]"

python -m PyInstaller --clean --noconfirm packaging/LocalSRT.spec
python -m PyInstaller --clean --noconfirm packaging/subtitle-worker.spec

Copy-Item -Force "dist\subtitle-worker.exe" "dist\LocalSRT\subtitle-worker.exe"

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    $ffmpegDir = "dist\LocalSRT\ffmpeg"
    New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
    Copy-Item -Force $ffmpeg.Source "$ffmpegDir\ffmpeg.exe"
    Write-Host "Copied ffmpeg.exe into dist\LocalSRT\ffmpeg"
}

Write-Host "Built dist\LocalSRT and dist\subtitle-worker"
Write-Host "Use Inno Setup with packaging\local_srt.iss to create the installer."
