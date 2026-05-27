@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-LocalSRT.ps1" -Portable -PayloadZip "%~dp0LocalSRT-source.zip"
if errorlevel 1 (
  echo.
  echo Local SRT portable setup did not finish successfully.
  pause
  exit /b 1
)
echo.
echo Local SRT portable setup finished.
echo Run LocalSRT.cmd from this folder to open the app.
pause
