# Local SRT

Local SRT is a Windows-first desktop app that turns audio and video files into `.srt` subtitle files. It runs speech recognition locally after the required runtime and model files have been downloaded.

Local SRT 是一個以 Windows 為優先的桌面應用程式，可以把音訊和影片檔轉成 `.srt` 字幕檔。下載必要的執行環境與模型後，語音辨識會在本機執行。

## Features

- Convert common audio and video files to `.srt` subtitles.
- Mandarin Chinese and English are the main v1 targets.
- Traditional Chinese output is the default.
- Uses Qwen3-ASR and Qwen3 ForcedAligner for transcription and alignment.
- Runs each transcription job in a separate worker process so PyTorch/CUDA memory can be released after a job finishes.
- Supports a portable folder install for GitHub releases.

## 功能

- 將常見音訊與影片檔轉換成 `.srt` 字幕。
- v1 主要支援中文普通話與英文。
- 預設輸出繁體中文。
- 使用 Qwen3-ASR 與 Qwen3 ForcedAligner 進行語音辨識與時間軸對齊。
- 每個轉錄工作會使用獨立 worker process，工作結束後可釋放 PyTorch/CUDA 記憶體。
- GitHub Release 支援可攜式資料夾安裝。

## Download and Install

Download the latest release from:

<https://github.com/auodsgae/Local-srt/releases/latest>

For most users, download `LocalSRT-OnlineInstaller-v0.1.1.zip`.

### Portable Install

1. Unzip `LocalSRT-OnlineInstaller-v0.1.1.zip` into the folder where you want Local SRT to live.
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

多數使用者請下載 `LocalSRT-OnlineInstaller-v0.1.1.zip`。

### 可攜式安裝

1. 將 `LocalSRT-OnlineInstaller-v0.1.1.zip` 解壓縮到你想放置 Local SRT 的資料夾。
2. 執行 `Install-LocalSRT-Portable.cmd`。
3. 選擇執行環境：
   - `1` 代表 CPU，下載較小，適用大多數 Windows 電腦。
   - `2` 代表 NVIDIA GPU/CUDA，下載較大，但在相容電腦上速度較快。
4. 安裝完成後，從同一個資料夾執行 `LocalSRT.cmd`。

可攜式模式會把應用程式資料與下載的語音模型放在本機 `data` 資料夾中。

### 一般使用者安裝

從 Release zip 執行 `Install-LocalSRT.cmd`。這會把 Local SRT 安裝到你的 Windows 使用者資料夾，並建立捷徑。

## Important Notes

- The release package is intentionally small.
- Python, PyTorch, ffmpeg, and speech models are not bundled in the GitHub release asset.
- The installer downloads the required runtime files during setup.
- Qwen speech models download later during first transcription.
- The NVIDIA GPU option requires a compatible NVIDIA GPU and driver.
- CPU mode is easier to install but can be much slower.

## 重要注意事項

- Release 套件刻意維持小檔案。
- GitHub Release 不內建 Python、PyTorch、ffmpeg 與語音模型。
- 安裝程式會在設定過程中下載必要的執行環境。
- Qwen 語音模型會在第一次轉錄時再下載。
- NVIDIA GPU 選項需要相容的 NVIDIA GPU 與驅動程式。
- CPU 模式較容易安裝，但速度可能慢很多。

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -e ".[dev]"
subtitle-app
```

If the CUDA wheel above does not match your driver, use the current Windows/NVIDIA command from:

<https://pytorch.org/get-started/locally/>

The app expects `ffmpeg.exe` to be on `PATH` or next to the packaged application under `ffmpeg\ffmpeg.exe`.

## 開發

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -e ".[dev]"
subtitle-app
```

如果上方 CUDA wheel 不符合你的驅動程式，請到 PyTorch 官方網站取得目前適合 Windows/NVIDIA 的安裝指令：

<https://pytorch.org/get-started/locally/>

應用程式需要 `ffmpeg.exe` 位於 `PATH`，或放在打包後應用程式旁的 `ffmpeg\ffmpeg.exe`。

## Worker CLI

```powershell
subtitle-worker transcribe --input "movie.mp4" --output "movie.srt" --language auto --model 1.7b --script traditional --caption-style natural
```

The worker writes JSON lines to stdout:

```json
{"type":"status","message":"Loading model"}
{"type":"progress","file":"movie.mp4","percent":42,"stage":"aligning"}
{"type":"result","srt_path":"movie.srt","duration_sec":123.4}
{"type":"error","message":"CUDA is unavailable","recoverable":true}
```

## Worker 命令列

```powershell
subtitle-worker transcribe --input "movie.mp4" --output "movie.srt" --language auto --model 1.7b --script traditional --caption-style natural
```

worker 會將 JSON lines 輸出到 stdout：

```json
{"type":"status","message":"Loading model"}
{"type":"progress","file":"movie.mp4","percent":42,"stage":"aligning"}
{"type":"result","srt_path":"movie.srt","duration_sec":123.4}
{"type":"error","message":"CUDA is unavailable","recoverable":true}
```

## Build

Build the PyInstaller app from a Windows PowerShell prompt after installing dependencies:

```powershell
.\scripts\build_windows.ps1
```

Build the small online/portable release zip:

```powershell
.\scripts\build_online_installer.ps1
```

Build the double-clickable setup executable:

```powershell
.\scripts\build_installer_exe.ps1
```

Tagged releases are built automatically by `.github\workflows\release-online-installer.yml`.

## 建置

安裝相依套件後，可從 Windows PowerShell 建置 PyInstaller 應用程式：

```powershell
.\scripts\build_windows.ps1
```

建置小型線上/可攜式 Release zip：

```powershell
.\scripts\build_online_installer.ps1
```

建置可雙擊執行的安裝程式：

```powershell
.\scripts\build_installer_exe.ps1
```

建立 tag 後，`.github\workflows\release-online-installer.yml` 會自動建置 Release。
