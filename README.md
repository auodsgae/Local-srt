# Local SRT

Local SRT is a Windows-first desktop app for turning audio and video files into `.srt` subtitles.
The v1 target is Mandarin Chinese and English, with Traditional Chinese output by default.

## Design Goals

- Local-only transcription after model download.
- Qwen3-ASR-1.7B for transcription quality.
- Qwen3-ForcedAligner-0.6B for real word/character end times.
- Separate worker process per job so CUDA/PyTorch memory is released when a file finishes.
- Clear failure when NVIDIA CUDA is unavailable.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -e ".[dev]"
subtitle-app
```

If the CUDA wheel above does not match your driver, use the current Windows/NVIDIA command from
[pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/) before installing the app.

The app expects `ffmpeg.exe` to be on `PATH` or next to the packaged application under `ffmpeg\ffmpeg.exe`.

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

## Windows Build

Run this from a Windows PowerShell prompt after installing dependencies:

```powershell
.\scripts\build_windows.ps1
```

The script builds `LocalSRT.exe` and `subtitle-worker.exe` with PyInstaller. The Inno Setup script in
`packaging\local_srt.iss` can then produce a normal installer.
