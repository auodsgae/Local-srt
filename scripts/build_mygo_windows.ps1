param(
    [Parameter(Mandatory)]
    [string]$Output
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$version = (Select-String -LiteralPath (Join-Path $root "pyproject.toml") -Pattern '^version = "([^"]+)"$').Matches[0].Groups[1].Value
$outputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Output)
Push-Location (Join-Path $root "desktop")
try {
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    $env:CGO_ENABLED = "0"
    go build -trimpath -ldflags "-H windowsgui -X main.appVersion=$version" -o $outputPath .
    if ($LASTEXITCODE -ne 0) {
        throw "Could not build the MyGO Windows desktop app."
    }
} finally {
    Pop-Location
}
