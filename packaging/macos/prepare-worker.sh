#!/bin/sh
set -eu

resources=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data=$1
version=$2
venv="$data/runtime/$version"

export UV_PYTHON_INSTALL_DIR="$data/python"
export UV_NO_PROGRESS=1

"$resources/uv" --no-config venv --managed-python --allow-existing --python 3.12 "$venv"
"$resources/uv" --no-config pip install --no-cache --python "$venv/bin/python3" "$resources/worker"
"$venv/bin/python3" -c 'from qwen_asr import Qwen3ASRModel; from local_srt.media import find_ffmpeg; assert find_ffmpeg() is not None'
touch "$venv/.worker-ready"
