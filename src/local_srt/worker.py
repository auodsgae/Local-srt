from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".srt")


def transcribe_command(args: argparse.Namespace) -> int:
    from .pipeline import transcribe_file

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(input_path)
    try:
        srt_path, elapsed = transcribe_file(
            input_path,
            output_path,
            language=args.language,
            model_size=args.model,
            device=args.device,
            script=args.script,
            caption_style=args.caption_style,
            progress=emit,
        )
    except Exception as exc:
        if args.debug:
            message = "".join(traceback.format_exception(exc))
        else:
            message = str(exc)
        emit({"type": "error", "message": message, "recoverable": True})
        return 1
    emit({"type": "result", "srt_path": str(srt_path), "duration_sec": round(elapsed, 3)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle-worker")
    sub = parser.add_subparsers(dest="command", required=True)
    transcribe = sub.add_parser("transcribe")
    transcribe.add_argument("--input", required=True)
    transcribe.add_argument("--output")
    transcribe.add_argument("--language", default="auto")
    transcribe.add_argument("--model", choices=["1.7b", "0.6b"], default="1.7b")
    transcribe.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    transcribe.add_argument("--script", choices=["traditional", "simplified", "preserve"], default="traditional")
    transcribe.add_argument("--caption-style", choices=["natural"], default="natural")
    transcribe.add_argument("--debug", action="store_true")
    transcribe.set_defaults(func=transcribe_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
