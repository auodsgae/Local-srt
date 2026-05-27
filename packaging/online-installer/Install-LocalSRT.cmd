@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-LocalSRT.ps1" -PayloadZip "%~dp0LocalSRT-source.zip"
if errorlevel 1 (
  echo.
  echo Local SRT setup did not finish successfully.
  pause
  exit /b 1
)
echo.
echo Local SRT setup finished.
pause
