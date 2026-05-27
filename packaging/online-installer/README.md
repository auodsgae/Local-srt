# Local SRT Online Installer

This is the small release package for Local SRT.

For a portable install, unzip this folder where you want Local SRT to live, then run
`Install-LocalSRT-Portable.cmd`. It downloads everything into this same folder and later creates
`LocalSRT.cmd`, which launches the app. App data and speech models stay in the local `data` folder.

For a normal per-user install, run `Install-LocalSRT.cmd`.

This package includes a small copy of the Local SRT source. The portable installer downloads:

- an embeddable Python runtime
- only the selected PyTorch runtime, CPU or NVIDIA GPU
- ffmpeg

The speech models are not included in the release package. They download later when the app transcribes for the first time.
