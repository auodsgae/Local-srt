param(
    [string]$InstallRoot = "",
    [string]$SourceRef = "main",
    [string]$PayloadZip = "",
    [ValidateSet("ask", "cpu", "cuda")]
    [string]$Runtime = "ask",
    [switch]$Portable,
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
$PythonEmbedZipUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
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
    $parent = Split-Path -Parent $Destination
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    try {
        Invoke-WebRequest `
            -Uri $Url `
            -OutFile $Destination `
            -UseBasicParsing `
            -MaximumRedirection 10 `
            -TimeoutSec 120 `
            -Headers @{ "User-Agent" = "LocalSRT-Installer" }
        return
    }
    catch {
        Write-Host "PowerShell download failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Trying .NET downloader..." -ForegroundColor Yellow
    }

    try {
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.AllowAutoRedirect = $true
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromMinutes(10)
        $client.DefaultRequestHeaders.UserAgent.ParseAdd("LocalSRT-Installer")
        $response = $client.GetAsync($Url).GetAwaiter().GetResult()
        $response.EnsureSuccessStatusCode() | Out-Null
        $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $file = [IO.File]::Create($Destination)
        try {
            $stream.CopyTo($file)
        }
        finally {
            $file.Dispose()
            $stream.Dispose()
            $client.Dispose()
            $handler.Dispose()
        }
    }
    catch {
        throw "Could not download $Url to $Destination. $($_.Exception.Message)"
    }
}

function Run-Command($FilePath, [string[]]$Arguments) {
    Write-Host "> $FilePath $($Arguments -join ' ')"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList (Join-ProcessArguments $Arguments) `
        -Wait `
        -PassThru `
        -NoNewWindow

    $exitCode = $process.ExitCode
    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $FilePath"
    }
}

function Join-ProcessArguments([string[]]$Arguments) {
    $quoted = foreach ($arg in $Arguments) {
        if ($arg -match '[\s"]') {
            '"' + ($arg -replace '"', '\"') + '"'
        }
        else {
            $arg
        }
    }
    return ($quoted -join " ")
}

function Run-ProcessCommand($FilePath, [string[]]$Arguments, [int[]]$AllowedExitCodes = @(0), [string]$FailureLog = "") {
    Write-Host "> $FilePath $($Arguments -join ' ')"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList (Join-ProcessArguments $Arguments) `
        -Wait `
        -PassThru `
        -NoNewWindow

    $exitCode = $process.ExitCode
    if ($AllowedExitCodes -notcontains $exitCode) {
        if ($FailureLog -and (Test-Path $FailureLog)) {
            Write-Host ""
            Write-Host "Last lines from installer log:" -ForegroundColor Yellow
            Get-Content -Tail 40 -Path $FailureLog | ForEach-Object { Write-Host $_ }
        }
        throw "Command failed with exit code ${exitCode}: $FilePath"
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

function Test-PythonRuntime($PythonExe) {
    if (-not (Test-Path $PythonExe)) {
        return $false
    }
    try {
        $global:LASTEXITCODE = 0
        & $PythonExe --version > $null 2>&1
        return ($global:LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-PythonPip($PythonExe) {
    if (-not (Test-PythonRuntime $PythonExe)) {
        return $false
    }
    try {
        $global:LASTEXITCODE = 0
        & $PythonExe -m pip --version > $null 2>&1
        return ($global:LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Enable-EmbeddedPythonSitePackages($PythonDir) {
    $pth = Get-ChildItem -Path $PythonDir -Filter "python*._pth" | Select-Object -First 1
    if (-not $pth) {
        return
    }

    $text = Get-Content -Raw -Path $pth.FullName
    $text = $text -replace "#import site", "import site"
    Set-Content -Encoding ASCII -Path $pth.FullName -Value $text
}

function Install-EmbeddedPython($PythonDir, $TempDir) {
    Write-Step "Installing portable Python runtime"
    if (Test-Path $PythonDir) {
        Remove-DirectoryBestEffort $PythonDir
    }
    New-Item -ItemType Directory -Force -Path $PythonDir | Out-Null

    $embedZip = Join-Path $TempDir "python-embed.zip"
    $getPip = Join-Path $TempDir "get-pip.py"
    Download-File $PythonEmbedZipUrl $embedZip
    Expand-Archive -Force -Path $embedZip -DestinationPath $PythonDir
    Enable-EmbeddedPythonSitePackages $PythonDir

    $pythonExe = Join-Path $PythonDir "python.exe"
    if (-not (Test-PythonRuntime $pythonExe)) {
        throw "Portable Python was not installed correctly."
    }

    Download-File $GetPipUrl $getPip
    Run-Command $pythonExe @($getPip, "--no-warn-script-location")

    if (-not (Test-Path (Join-Path $PythonDir "Scripts\pip.exe"))) {
        Run-Command $pythonExe @("-m", "pip", "--version")
    }
    return $pythonExe
}

function Show-LogTail($Path) {
    if ($Path -and (Test-Path $Path)) {
        Write-Host ""
        Write-Host "Last lines from installer log:" -ForegroundColor Yellow
        Get-Content -Tail 40 -Path $Path | ForEach-Object { Write-Host $_ }
    }
}

function Install-Python($PythonDir, $TempDir, [bool]$PreferEmbeddedPython) {
    $pythonExe = Join-Path $PythonDir "python.exe"
    if (Test-PythonPip $pythonExe) {
        return $pythonExe
    }

    if ($PreferEmbeddedPython) {
        return Install-EmbeddedPython $PythonDir $TempDir
    }

    Write-Step "Installing private Python runtime"
    if (Test-Path $PythonDir) {
        Write-Host "Removing incomplete Python runtime folder: $PythonDir"
        Remove-DirectoryBestEffort $PythonDir
    }
    New-Item -ItemType Directory -Force -Path $PythonDir | Out-Null
    $installer = Join-Path $TempDir "python-installer.exe"
    $installerLog = Join-Path $TempDir "python-installer.log"
    Download-File $PythonInstallerUrl $installer
    Run-ProcessCommand $installer @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$PythonDir",
        "Include_launcher=0",
        "Include_pip=1",
        "Include_test=0",
        "PrependPath=0",
        "/log",
        $installerLog
    ) @(0, 3010) $installerLog

    if (-not (Test-PythonRuntime $pythonExe)) {
        Show-LogTail $installerLog
        Write-Host "Python installer did not create a runnable private Python. Falling back to portable Python." -ForegroundColor Yellow
        return Install-EmbeddedPython $PythonDir $TempDir
    }
    return $pythonExe
}

function Install-Source($AppDir, $TempDir) {
    Write-Step "Installing Local SRT app files"
    $sourceZip = Join-Path $TempDir "local-srt-source.zip"
    $expanded = Join-Path $TempDir "source"
    $savedFfmpegDir = Join-Path $TempDir "existing-ffmpeg"
    if ($PayloadZip -and (Test-Path -LiteralPath $PayloadZip)) {
        Copy-Item -Force -LiteralPath $PayloadZip -Destination $sourceZip
    }
    else {
        Download-File $SourceZipUrl $sourceZip
    }
    Expand-Archive -Force -Path $sourceZip -DestinationPath $expanded
    $sourceRoot = Get-Item -LiteralPath $expanded
    if (-not (Test-Path (Join-Path $sourceRoot.FullName "pyproject.toml"))) {
        $sourceRoot = Get-ChildItem -Path $expanded -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName "pyproject.toml") } |
            Select-Object -First 1
    }
    if (-not $sourceRoot) {
        throw "Could not find Local SRT source files in the download."
    }

    if (Test-Path $AppDir) {
        $existingFfmpegDir = Join-Path $AppDir "ffmpeg"
        if (Test-Path $existingFfmpegDir) {
            Copy-Item -Recurse -Force $existingFfmpegDir $savedFfmpegDir
        }
        Remove-Item -Recurse -Force $AppDir
    }
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
    if (-not (Test-Path (Join-Path $sourceRoot.FullName "src"))) {
        throw "Local SRT source package is missing the src folder."
    }
    Copy-Item -Recurse -Force (Join-Path $sourceRoot.FullName "src") (Join-Path $AppDir "src")
    Copy-Item -Force (Join-Path $sourceRoot.FullName "pyproject.toml") (Join-Path $AppDir "pyproject.toml")
    Copy-Item -Force (Join-Path $sourceRoot.FullName "README.md") (Join-Path $AppDir "README.md")
    if (Test-Path $savedFfmpegDir) {
        Copy-Item -Recurse -Force $savedFfmpegDir (Join-Path $AppDir "ffmpeg")
    }
}

function Install-Ffmpeg($AppDir, $TempDir) {
    Write-Step "Installing ffmpeg"
    $ffmpegDir = Join-Path $AppDir "ffmpeg"
    $ffmpegExe = Join-Path $ffmpegDir "ffmpeg.exe"
    if (Test-Path $ffmpegExe) {
        Write-Host "Using existing Local SRT ffmpeg: $ffmpegExe"
        return
    }

    $systemFfmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if (-not $systemFfmpeg) {
        $systemFfmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    }
    if ($systemFfmpeg) {
        Write-Host "Using ffmpeg already installed on this computer: $($systemFfmpeg.Source)"
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

function Install-PythonPackages($PythonExe, $VenvDir, $AppDir, $SelectedRuntime, [bool]$UsePortableRuntime) {
    Write-Step "Installing Local SRT runtime"
    if ($UsePortableRuntime) {
        $runtimePython = $PythonExe
    }
    else {
        if (-not (Test-Path $VenvDir)) {
            Run-Command $PythonExe @("-m", "venv", $VenvDir)
        }
        $runtimePython = Join-Path $VenvDir "Scripts\python.exe"
    }

    Run-Command $runtimePython @("-m", "pip", "install", "--upgrade", "--no-cache-dir", "pip", "setuptools", "wheel")

    if ($SelectedRuntime -eq "cuda") {
        Run-Command $runtimePython @("-m", "pip", "install", "--no-cache-dir", "torch", "--index-url", "https://download.pytorch.org/whl/cu128")
    }
    else {
        Run-Command $runtimePython @("-m", "pip", "install", "--no-cache-dir", "torch", "--index-url", "https://download.pytorch.org/whl/cpu")
    }

    if ($UsePortableRuntime) {
        Run-Command $runtimePython @("-m", "pip", "install", "--no-cache-dir", "hf_xet", $AppDir)
    }
    else {
        Run-Command $runtimePython @("-m", "pip", "install", "--no-cache-dir", "hf_xet", "-e", $AppDir)
    }
    Run-Command $runtimePython @("-m", "pip", "cache", "purge")
    return $runtimePython
}

function Write-Launcher($InstallRoot, $SelectedRuntime, [bool]$UsePortableRuntime) {
    Write-Step "Creating launcher"
    $launcher = Join-Path $InstallRoot "LocalSRT.cmd"
    if ($UsePortableRuntime) {
        $pythonw = "%LOCAL_SRT_ROOT%python\pythonw.exe"
        $appDataLine = 'set "LOCAL_SRT_APP_DATA=%LOCAL_SRT_ROOT%data"'
    }
    else {
        $pythonw = "%LOCAL_SRT_ROOT%.venv\Scripts\pythonw.exe"
        $appDataLine = ""
    }
    $launcherText = @"
@echo off
set "LOCAL_SRT_ROOT=%~dp0"
set "PATH=%LOCAL_SRT_ROOT%app\ffmpeg;%PATH%"
set "LOCAL_SRT_DEFAULT_DEVICE=$SelectedRuntime"
$appDataLine
start "Local SRT" "$pythonw" -m local_srt
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

function Remove-DirectoryBestEffort($Path) {
    if (-not (Test-Path $Path)) {
        return
    }

    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            Remove-Item -Recurse -Force $Path -ErrorAction Stop
            return
        }
        catch {
            if ($attempt -lt 5) {
                Start-Sleep -Seconds 2
            }
            else {
                Write-Host "Could not remove temporary setup folder. It is safe to delete later:" -ForegroundColor Yellow
                Write-Host "  $Path" -ForegroundColor Yellow
            }
        }
    }
}

Require-64BitWindows
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not $InstallRoot) {
    if ($Portable) {
        $InstallRoot = $PSScriptRoot
    }
    else {
        $InstallRoot = "$env:LOCALAPPDATA\LocalSRT"
    }
}

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
    if ($Portable) {
        Write-Host "Portable mode: app data and speech models will stay inside this folder."
    }

    Install-Source $appDir $tempDir
    $pythonExe = Install-Python $pythonDir $tempDir $Portable.IsPresent
    $null = Install-PythonPackages $pythonExe $venvDir $appDir $selectedRuntime $Portable.IsPresent
    Install-Ffmpeg $appDir $tempDir
    $launcher = Write-Launcher $installRootPath $selectedRuntime $Portable.IsPresent
    if (-not $Portable) {
        Create-Shortcuts $launcher $installRootPath
    }

    Write-Step "Done"
    if ($Portable) {
        Write-Host "Open Local SRT by running:"
        Write-Host "  $launcher"
    }
    else {
        Write-Host "Open Local SRT from the Desktop shortcut or the Start menu."
    }
    Write-Host "The speech models will download the first time you transcribe a file."
}
finally {
    Remove-DirectoryBestEffort $tempDir
}
