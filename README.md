# Local SRT

Local SRT is a Windows desktop app that turns audio and video files into `.srt` subtitle files. It runs speech recognition locally after the required runtime and model files have been downloaded.

Local SRT 是一個Windows系統的桌面應用程式，可以把音訊和影片檔轉成 `.srt` 字幕檔。下載必要的執行環境與模型後，語音辨識會在本機執行。

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

For most users, download `LocalSRT-OnlineInstaller-v0.1.3.zip`.

### Portable Install

1. Unzip `LocalSRT-OnlineInstaller-v0.1.3.zip` into the folder where you want Local SRT to live.
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

多數使用者請下載 `LocalSRT-OnlineInstaller-v0.1.3.zip`。

### 可攜式安裝

1. 將 `LocalSRT-OnlineInstaller-v0.1.3.zip` 解壓縮到你想放置 Local SRT 的資料夾。
2. 執行 `Install-LocalSRT-Portable.cmd`。
3. 選擇執行環境：
   - `1` 代表 CPU，下載較小，適用大多數 Windows 電腦。
   - `2` 代表 NVIDIA GPU/CUDA，下載較大，但在相容電腦上速度較快。
4. 安裝完成後，從同一個資料夾執行 `LocalSRT.cmd`。

可攜式模式會把應用程式資料與下載的語音模型放在本機 `data` 資料夾中。

### 一般使用者安裝

從 Release zip 執行 `Install-LocalSRT.cmd`。這會把 Local SRT 安裝到你的 Windows 使用者資料夾，並建立捷徑。

## Important Notes

- Python, PyTorch, ffmpeg, and speech models are not bundled in the GitHub release asset.
- The installer downloads the required runtime files during setup.
- Qwen speech models download later during first transcription.
- The NVIDIA GPU option requires a compatible NVIDIA GPU and driver.

## 重要注意事項

- GitHub Release 不內建 Python、PyTorch、ffmpeg 與語音模型。
- 安裝程式會在設定過程中下載必要的執行環境。
- Qwen 語音模型會在第一次轉錄時再下載。
- NVIDIA GPU 選項需要相容的 NVIDIA GPU 與驅動程式。
