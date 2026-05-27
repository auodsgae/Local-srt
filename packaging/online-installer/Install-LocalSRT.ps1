param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\LocalSRT",
    [string]$SourceRef = "main",
    [ValidateSet("ask", "cpu", "cuda")]
    [string]$Runtime = "ask",
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"

$Repository = "auodsgae/Local-srt"
$PythonVersion = "3.12.10"
if ($SourceRef -match "^v[0-9]") {
    $SourceZipUrl = "https://github.com/$Repository/archive/refs/tags/$SourceRef.zip"
}
else {
    $SourceZipUrl = "https://github.com/$Repository/archive/refs/heads/$SourceRef.zip"
}
$PythonInstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$FfmpegZipUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Require-64BitWindows {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw "Local SRT requires 64-bit Windows."
    }
}

function Download-File($Url, $Destination) {
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

function Run-Command($FilePath, [string[]]$Arguments) {
    Write-Host "> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath"
    }
}

function Choose-Runtime {
    if ($Runtime -ne "ask") {
        return $Runtime
    }

    Write-Host ""
    Write-Host "Choose the speech runtime to download:"
    Write-Host "  1. CPU - smaller download, works on most Windows computers"
    Write-Host "  2. NVIDIA GPU - bigger download, faster if this computer has a compatible NVIDIA GPU"
    $choice = Read-Host "Type 1 or 2, then press Enter"
    if ($choice -eq "2") {
        return "cuda"
    }
    return "cpu"
}

function Install-Python($PythonDir, $TempDir) {
    $pythonExe = Join-Path $PythonDir "python.exe"
    if (Test-Path $pythonExe) {
        return $pythonExe
    }

    Write-Step "Installing private Python runtime"
    New-Item -ItemType Directory -Force -Path $PythonDir | Out-Null
    $installer = Join-Path $TempDir "python-installer.exe"
    Download-File $PythonInstallerUrl $installer
    Run-Command $installer @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$PythonDir",
        "Include_launcher=0",
        "Include_pip=1",
        "Include_test=0",
        "PrependPath=0"
    )

    if (-not (Test-Path $pythonExe)) {
        throw "Python was not installed correctly."
    }
    return $pythonExe
}

function Install-Source($AppDir, $TempDir) {
    Write-Step "Downloading Local SRT app files"
    $sourceZip = Join-Path $TempDir "local-srt-source.zip"
    $expanded = Join-Path $TempDir "source"
    Download-File $SourceZipUrl $sourceZip
    Expand-Archive -Force -Path $sourceZip -DestinationPath $expanded
    $sourceRoot = Get-ChildItem -Path $expanded -Directory | Select-Object -First 1
    if (-not $sourceRoot) {
        throw "Could not find Local SRT source files in the download."
    }

    if (Test-Path $AppDir) {
        Remove-Item -Recurse -Force $AppDir
    }
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
    Copy-Item -Recurse -Force (Join-Path $sourceRoot.FullName "src") (Join-Path $AppDir "src")
    Copy-Item -Force (Join-Path $sourceRoot.FullName "pyproject.toml") (Join-Path $AppDir "pyproject.toml")
    Copy-Item -Force (Join-Path $sourceRoot.FullName "README.md") (Join-Path $AppDir "README.md")
}

function Install-Ffmpeg($AppDir, $TempDir) {
    Write-Step "Installing ffmpeg"
    $ffmpegDir = Join-Path $AppDir "ffmpeg"
    $ffmpegExe = Join-Path $ffmpegDir "ffmpeg.exe"
    if (Test-Path $ffmpegExe) {
        return
    }

    $zip = Join-Path $TempDir "ffmpeg.zip"
    $expanded = Join-Path $TempDir "ffmpeg"
    Download-File $FfmpegZipUrl $zip
    Expand-Archive -Force -Path $zip -DestinationPath $expanded
    $downloadedExe = Get-ChildItem -Path $expanded -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    if (-not $downloadedExe) {
        throw "Could not find ffmpeg.exe in the downloaded package."
    }

    New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
    Copy-Item -Force $downloadedExe.FullName $ffmpegExe
}

function Install-PythonPackages($PythonExe, $VenvDir, $AppDir, $SelectedRuntime) {
    Write-Step "Installing Local SRT runtime"
    if (-not (Test-Path $VenvDir)) {
        Run-Command $PythonExe @("-m", "venv", $VenvDir)
    }

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    Run-Command $venvPython @("-m", "pip", "install", "--upgrade", "--no-cache-dir", "pip", "setuptools", "wheel")

    if ($SelectedRuntime -eq "cuda") {
        Run-Command $venvPython @("-m", "pip", "install", "--no-cache-dir", "torch", "--index-url", "https://download.pytorch.org/whl/cu128")
    }
    else {
        Run-Command $venvPython @("-m", "pip", "install", "--no-cache-dir", "torch", "--index-url", "https://download.pytorch.org/whl/cpu")
    }

    Run-Command $venvPython @("-m", "pip", "install", "--no-cache-dir", "hf_xet", "-e", $AppDir)
    Run-Command $venvPython @("-m", "pip", "cache", "purge")
}

function Write-Launcher($InstallRoot, $AppDir, $SelectedRuntime) {
    Write-Step "Creating launcher"
    $launcher = Join-Path $InstallRoot "LocalSRT.cmd"
    $launcherText = @"
@echo off
set "PATH=$AppDir\ffmpeg;%PATH%"
set "LOCAL_SRT_DEFAULT_DEVICE=$SelectedRuntime"
start "Local SRT" "$InstallRoot\.venv\Scripts\pythonw.exe" -m local_srt
"@
    Set-Content -Encoding ASCII -Path $launcher -Value $launcherText
    return $launcher
}

function Create-Shortcuts($Launcher, $InstallRoot) {
    Write-Step "Creating shortcuts"
    $shell = New-Object -ComObject WScript.Shell

    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Local SRT"
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
    $startShortcut = $shell.CreateShortcut((Join-Path $startMenu "Local SRT.lnk"))
    $startShortcut.TargetPath = $Launcher
    $startShortcut.WorkingDirectory = $InstallRoot
    $startShortcut.Save()

    if (-not $NoDesktopShortcut) {
        $desktopShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Local SRT.lnk"))
        $desktopShortcut.TargetPath = $Launcher
        $desktopShortcut.WorkingDirectory = $InstallRoot
        $desktopShortcut.Save()
    }
}

Require-64BitWindows
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$selectedRuntime = Choose-Runtime
$installRootPath = [IO.Path]::GetFullPath($InstallRoot)
$appDir = Join-Path $installRootPath "app"
$pythonDir = Join-Path $installRootPath "python"
$venvDir = Join-Path $installRootPath ".venv"
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ("LocalSRT-Setup-" + [Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $installRootPath | Out-Null
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    Write-Host "Local SRT will be installed to:"
    Write-Host "  $installRootPath"
    Write-Host "Runtime choice: $selectedRuntime"

    Install-Source $appDir $tempDir
    $pythonExe = Install-Python $pythonDir $tempDir
    Install-PythonPackages $pythonExe $venvDir $appDir $selectedRuntime
    Install-Ffmpeg $appDir $tempDir
    $launcher = Write-Launcher $installRootPath $appDir $selectedRuntime
    Create-Shortcuts $launcher $installRootPath

    Write-Step "Done"
    Write-Host "Open Local SRT from the Desktop shortcut or the Start menu."
    Write-Host "The speech models will download the first time you transcribe a file."
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
