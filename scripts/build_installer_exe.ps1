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
Get-ChildItem -Path $payloadDir -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $payloadDir -Recurse -File |
    Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
    Remove-Item -Force
Copy-Item -Force (Join-Path $root "pyproject.toml") (Join-Path $payloadDir "pyproject.toml")
Copy-Item -Force (Join-Path $root "README.md") (Join-Path $payloadDir "README.md")
& (Join-Path $PSScriptRoot "build_mygo_windows.ps1") -Output (Join-Path $payloadDir "LocalSRT-MyGO.exe")
Compress-Archive -Path (Join-Path $payloadDir "*") -DestinationPath $payloadZip -CompressionLevel Optimal

Copy-Item -Force (Join-Path $root "packaging\online-installer\Install-LocalSRT.ps1") $installerScript
$installerText = Get-Content -Raw -Path $installerScript
$installerText = $installerText.Replace('[string]$SourceRef = "main"', "[string]`$SourceRef = `"$SourceRef`"")
Set-Content -Encoding ASCII -Path $installerScript -Value $installerText

$csharp = @"
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;

internal static class LocalSrtInstaller
{
    private const string Version = "$version";

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
            ExtractResource("Install-LocalSRT.ps1", scriptPath);
            ExtractResource("LocalSRT-source.zip", payloadPath);

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
                if (process.ExitCode != 0)
                {
                    PauseForError();
                }
                return process.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Local SRT setup failed:");
            Console.Error.WriteLine(ex.Message);
            PauseForError();
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

    private static void ExtractResource(string name, string path)
    {
        using (Stream source = typeof(LocalSrtInstaller).Assembly.GetManifestResourceStream(name))
        using (FileStream destination = File.Create(path))
        {
            if (source == null)
                throw new InvalidOperationException("Installer resource missing: " + name);
            source.CopyTo(destination);
        }
    }

    private static void PauseForError()
    {
        if (!Console.IsInputRedirected)
        {
            Console.WriteLine();
            Console.WriteLine("Setup did not finish. Press any key to close this window.");
            Console.ReadKey(true);
        }
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

& $csc /nologo /target:exe /platform:x64 "/out:$exePath" "/resource:$installerScript,Install-LocalSRT.ps1" "/resource:$payloadZip,LocalSRT-source.zip" $sourcePath
if ($LASTEXITCODE -ne 0) {
    throw "Could not build installer exe."
}

Remove-Item -Recurse -Force $buildDir
Write-Host "Created $exePath"
