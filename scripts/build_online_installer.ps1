param(
    [string]$SourceRef = "main"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$versionLine = Select-String -Path (Join-Path $root "pyproject.toml") -Pattern '^version = "([^"]+)"$'
if (-not $versionLine) {
    throw "Could not read version from pyproject.toml"
}
$version = $versionLine.Matches[0].Groups[1].Value

$releaseDir = Join-Path $root "release"
$stageDir = Join-Path $releaseDir "LocalSRT-OnlineInstaller-v$version"
$zipPath = Join-Path $releaseDir "LocalSRT-OnlineInstaller-v$version.zip"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Force -Path $stageDir | Out-Null
Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.cmd") $stageDir
$installerPath = Join-Path $stageDir "Install-LocalSRT.ps1"
Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.ps1") $installerPath
Copy-Item -Force (Join-Path $root "packaging\online-installer\README.md") $stageDir

$installerText = Get-Content -Raw -Path $installerPath
$installerText = $installerText.Replace('[string]$SourceRef = "main"', "[string]`$SourceRef = `"$SourceRef`"")
Set-Content -Encoding ASCII -Path $installerPath -Value $installerText

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Created $zipPath"
