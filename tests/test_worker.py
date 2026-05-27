from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt.worker import build_parser, default_output_path


class WorkerTests(unittest.TestCase):
    def test_default_output_path(self):
        self.assertEqual(default_output_path(Path("clip.mp4")), Path("clip.srt"))

    def test_transcribe_arguments(self):
        args = build_parser().parse_args(
            [
                "transcribe",
                "--input",
                "clip.mp4",
                "--output",
                "clip.srt",
                "--language",
                "auto",
                "--model",
                "1.7b",
                "--device",
                "cpu",
                "--script",
                "traditional",
                "--caption-style",
                "natural",
            ]
        )
        self.assertEqual(args.command, "transcribe")
        self.assertEqual(args.model, "1.7b")
        self.assertEqual(args.device, "cpu")


if __name__ == "__main__":
    unittest.main()
