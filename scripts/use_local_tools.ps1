$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonRoot = Join-Path $ProjectRoot ".python312\tools"
$VenvRoot = Join-Path $ProjectRoot ".venv"
$GitCmd = Join-Path $ProjectRoot ".tools\MinGit\cmd"

$paths = @(
    (Join-Path $VenvRoot "Scripts"),
    $GitCmd,
    $PythonRoot,
    (Join-Path $PythonRoot "Scripts")
) | Where-Object { Test-Path $_ }

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    $paths += Split-Path -Parent $ffmpeg.Source
}

$newPath = (($paths + @($env:Path)) -join ";")
[Environment]::SetEnvironmentVariable("Path", $null, "Process")
[Environment]::SetEnvironmentVariable("PATH", $newPath, "Process")
$env:Path = $newPath

Write-Host "Project tools are ready for this PowerShell window."
python --version
git --version
if ($ffmpeg) {
    ffmpeg -version | Select-Object -First 1
}
