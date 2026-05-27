# Local SRT Online Installer

This is the small release package for Local SRT.

Run `Install-LocalSRT.cmd` on a Windows computer. The installer downloads:

- a private Python runtime
- the Local SRT app source
- only the selected PyTorch runtime, CPU or NVIDIA GPU
- ffmpeg

The speech models are not included in the release package. They download later when the app transcribes for the first time.
