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
$payloadDir = Join-Path $releaseDir "online-installer-payload\LocalSRT-source"
$payloadZip = Join-Path $stageDir "LocalSRT-source.zip"
$zipPath = Join-Path $releaseDir "LocalSRT-OnlineInstaller-v$version.zip"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
if (Test-Path (Split-Path -Parent $payloadDir)) {
    Remove-Item -Recurse -Force (Split-Path -Parent $payloadDir)
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Force -Path $stageDir | Out-Null
New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "src") (Join-Path $payloadDir "src")
Copy-Item -Force (Join-Path $root "pyproject.toml") (Join-Path $payloadDir "pyproject.toml")
Copy-Item -Force (Join-Path $root "README.md") (Join-Path $payloadDir "README.md")
Compress-Archive -Path (Join-Path $payloadDir "*") -DestinationPath $payloadZip -CompressionLevel Optimal
Remove-Item -Recurse -Force (Split-Path -Parent $payloadDir)

Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.cmd") $stageDir
Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT-Portable.cmd") $stageDir
$installerPath = Join-Path $stageDir "Install-LocalSRT.ps1"
Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.ps1") $installerPath
Copy-Item -Force (Join-Path $root "packaging\online-installer\README.md") $stageDir

$installerText = Get-Content -Raw -Path $installerPath
$installerText = $installerText.Replace('[string]$SourceRef = "main"', "[string]`$SourceRef = `"$SourceRef`"")
Set-Content -Encoding ASCII -Path $installerPath -Value $installerText

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Created $zipPath"
