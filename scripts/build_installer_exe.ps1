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
$buildDir = Join-Path $releaseDir "installer-exe-build"
$payloadDir = Join-Path $buildDir "payload\LocalSRT-source"
$payloadZip = Join-Path $buildDir "LocalSRT-source.zip"
$installerScript = Join-Path $buildDir "Install-LocalSRT.ps1"
$sourcePath = Join-Path $buildDir "LocalSRTInstaller.cs"
$exePath = Join-Path $releaseDir "LocalSRT-Setup-v$version.exe"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
}
if (Test-Path $exePath) {
    Remove-Item -Force $exePath
}

New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "src") (Join-Path $payloadDir "src")
Copy-Item -Force (Join-Path $root "pyproject.toml") (Join-Path $payloadDir "pyproject.toml")
Copy-Item -Force (Join-Path $root "README.md") (Join-Path $payloadDir "README.md")
Compress-Archive -Path (Join-Path $payloadDir "*") -DestinationPath $payloadZip -CompressionLevel Optimal

Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.ps1") $installerScript
$installerText = Get-Content -Raw -Path $installerScript
$installerText = $installerText.Replace('[string]$SourceRef = "main"', "[string]`$SourceRef = `"$SourceRef`"")
Set-Content -Encoding ASCII -Path $installerScript -Value $installerText

function Convert-ToCSharpStringExpression($Path) {
    $base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Path))
    $parts = [regex]::Matches($base64, ".{1,100}") | ForEach-Object { $_.Value }
    return (($parts | ForEach-Object { '            "' + $_ + '"' }) -join " +`r`n")
}

$scriptExpression = Convert-ToCSharpStringExpression $installerScript
$payloadExpression = Convert-ToCSharpStringExpression $payloadZip

$csharp = @"
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;

internal static class LocalSrtInstaller
{
    private const string Version = "$version";

    private static readonly string InstallerScriptBase64 =
$scriptExpression;

    private static readonly string PayloadZipBase64 =
$payloadExpression;

    [STAThread]
    private static int Main(string[] args)
    {
        foreach (string arg in args)
        {
            if (arg == "--help" || arg == "/?" || arg == "-h")
            {
                Console.WriteLine("Local SRT Setup " + Version);
                Console.WriteLine("Double-click to install, or run with --cpu / --cuda.");
                Console.WriteLine("Options: --cpu, --cuda, --no-desktop-shortcut");
                return 0;
            }
        }

        string tempDir = Path.Combine(Path.GetTempPath(), "LocalSRT-Setup-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);
        string scriptPath = Path.Combine(tempDir, "Install-LocalSRT.ps1");
        string payloadPath = Path.Combine(tempDir, "LocalSRT-source.zip");

        try
        {
            File.WriteAllBytes(scriptPath, Convert.FromBase64String(InstallerScriptBase64));
            File.WriteAllBytes(payloadPath, Convert.FromBase64String(PayloadZipBase64));

            var psArgs = new List<string>
            {
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                Quote(scriptPath),
                "-PayloadZip",
                Quote(payloadPath)
            };

            foreach (string arg in args)
            {
                if (arg == "--cpu")
                {
                    psArgs.Add("-Runtime");
                    psArgs.Add("cpu");
                }
                else if (arg == "--cuda")
                {
                    psArgs.Add("-Runtime");
                    psArgs.Add("cuda");
                }
                else if (arg == "--no-desktop-shortcut")
                {
                    psArgs.Add("-NoDesktopShortcut");
                }
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = string.Join(" ", psArgs),
                UseShellExecute = false
            };
            using (Process process = Process.Start(startInfo))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Local SRT setup failed:");
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
        finally
        {
            try
            {
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, true);
                }
            }
            catch
            {
            }
        }
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
"@

Set-Content -Encoding ASCII -Path $sourcePath -Value $csharp

$cscCandidates = @(
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$csc = $cscCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) {
    throw "Could not find the Windows C# compiler."
}

& $csc /nologo /target:exe /platform:x64 "/out:$exePath" $sourcePath
if ($LASTEXITCODE -ne 0) {
    throw "Could not build installer exe."
}

Remove-Item -Recurse -Force $buildDir
Write-Host "Created $exePath"
