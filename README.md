# Local SRT

Local SRT is a desktop app for Windows and macOS built with MyGO. It turns audio and video files into `.srt` subtitles on your device after downloading the runtime and speech models.

Local SRT 是一個使用 MyGO 開發的 Windows 和 macOS 桌面應用程式，可以把音訊和影片檔轉成 `.srt` 字幕檔。下載執行環境與模型後，語音辨識會在本機執行。

## Features

- Convert common audio and video files to `.srt` subtitles.
- Uses Qwen3-ASR and Qwen3 ForcedAligner for transcription and alignment.
- Supports a portable folder install for GitHub releases.

## 功能

- 將常見音訊與影片檔轉換成 `.srt` 字幕。
- 使用 Qwen3-ASR 與 Qwen3 ForcedAligner 進行語音辨識與時間軸對齊。
- GitHub Release 支援可攜式資料夾安裝。

## Download and Install

Download the latest release from:

<https://github.com/auodsgae/Local-srt/releases/latest>

On Windows x64, run `LocalSRT-Setup-v0.2.0.exe`. On macOS 14 or later with Apple Silicon, open `LocalSRT-v0.2.0-macOS-arm64.dmg` and drag Local SRT into Applications. The Mac app downloads its runtime on the first transcription and uses the CPU. The Mac build is ad hoc signed and has no Apple notarization.

### Portable Install

1. Unzip `LocalSRT-OnlineInstaller-v0.2.0.zip` into the folder where you want Local SRT to live.
2. Run `Install-LocalSRT-Portable.cmd`.
3. Choose the runtime:
   - `1` for CPU, smaller and works on most Windows computers.
   - `2` for NVIDIA GPU/CUDA, larger but faster on compatible computers.
4. After setup finishes, run `LocalSRT.cmd` from the same folder.

Portable mode keeps app data and downloaded speech models inside the local `data` folder.

### Normal Per-User Install

Run `Install-LocalSRT.cmd` from the release zip. This installs Local SRT under your Windows user profile and creates shortcuts.

## 下載與安裝

請從最新版 Release 下載：

<https://github.com/auodsgae/Local-srt/releases/latest>

Windows x64 請執行 `LocalSRT-Setup-v0.2.0.exe`。Apple Silicon Mac（macOS 14 以上）請開啟 `LocalSRT-v0.2.0-macOS-arm64.dmg`，並將 Local SRT 拖入「應用程式」。Mac 版使用 CPU，第一次轉錄時會下載執行環境。Mac 版採用 ad hoc 簽章，未經 Apple 公證。

### 可攜式安裝

1. 將 `LocalSRT-OnlineInstaller-v0.2.0.zip` 解壓縮到你想放置 Local SRT 的資料夾。
2. 執行 `Install-LocalSRT-Portable.cmd`。
3. 選擇執行環境：
   - `1` 代表 CPU，下載較小，適用大多數 Windows 電腦。
   - `2` 代表 NVIDIA GPU/CUDA，下載較大，但在相容電腦上速度較快。
4. 安裝完成後，從同一個資料夾執行 `LocalSRT.cmd`。

可攜式模式會把應用程式資料與下載的語音模型放在本機 `data` 資料夾中。

### 一般使用者安裝

從 Release zip 執行 `Install-LocalSRT.cmd`。這會把 Local SRT 安裝到你的 Windows 使用者資料夾，並建立捷徑。

## Important Notes

- The Windows installer downloads the required runtime files during setup.
- Qwen speech models download later during first transcription.
- The NVIDIA GPU option requires a compatible NVIDIA GPU and driver.

## 重要注意事項

- Windows 安裝程式會在設定過程中下載必要的執行環境。
- Qwen 語音模型會在第一次轉錄時再下載。
- NVIDIA GPU 選項需要相容的 NVIDIA GPU 與驅動程式。

## Build installers

Both builds require Go 1.27.3 or newer. Run these commands from the repository root.

- Windows x64 (PowerShell 7): `./scripts/build_installer_exe.ps1` and `./scripts/build_online_installer.ps1`.
- Apple Silicon Mac (with `uv` on PATH): `bash scripts/build_macos_installer.sh`.

The installers are written to `release/`. Pushing a version tag builds and publishes both platforms through GitHub Actions. For desktop development, set `LOCAL_SRT_PYTHON` to an absolute path to Python with the Local SRT package installed.
