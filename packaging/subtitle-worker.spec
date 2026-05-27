# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import nagisa
from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH).parent
nagisa_root = Path(nagisa.__file__).parent

a = Analysis(
    [str(project_root / "packaging" / "worker_entry.py")],
    pathex=[str(project_root / "src"), str(nagisa_root)],
    binaries=[],
    datas=(
        collect_data_files("jieba")
        + collect_data_files("nagisa")
        + collect_data_files("qwen_asr")
        + collect_data_files("wordfreq")
    ),
    hiddenimports=[
        "jieba",
        "mecab_system_eval",
        "model",
        "nagisa",
        "nagisa_utils",
        "prepro",
        "qwen_asr",
        "tagger",
        "torch",
        "opencc",
        "wordfreq",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="subtitle-worker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
