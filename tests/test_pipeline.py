from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt import pipeline
from local_srt.captions import SimpleAlignmentItem


class FakeBackend:
    instances = []

    def __init__(self, **kwargs):
        self.loaded = False
        self.calls = 0
        FakeBackend.instances.append(self)

    def load(self):
        self.loaded = True

    def transcribe_chunk(self, chunk, *, language=None):
        self.calls += 1
        assert self.loaded
        return SimpleNamespace(
            text="Hello.",
            alignment_items=[
                SimpleAlignmentItem("Hello", 0.0, 0.2),
            ],
        )


class PipelineTests(unittest.TestCase):
    def test_progress_reports_intermediate_steps(self):
        original_decode = pipeline.decode_to_pcm16k
        original_chunk = pipeline.chunk_audio
        original_backend = pipeline.QwenBackend
        try:
            pipeline.decode_to_pcm16k = lambda _path: (np.zeros(32_000, dtype=np.float32), 2.0)
            pipeline.chunk_audio = lambda _audio, _seconds: [
                (0.0, np.zeros(16_000, dtype=np.float32)),
                (1.0, np.zeros(16_000, dtype=np.float32)),
            ]
            pipeline.QwenBackend = FakeBackend
            FakeBackend.instances = []
            events = []
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "output.srt"
                pipeline.transcribe_file(
                    Path(tmpdir) / "input.wav",
                    output_path,
                    device="cpu",
                    progress=events.append,
                )
                content = output_path.read_text(encoding="utf-8")
                self.assertEqual(content.count("Hello\n"), 2)
                self.assertNotIn("Hello.", content)
            percents = [event["percent"] for event in events if event.get("type") == "progress"]
            self.assertEqual(percents[0], 1)
            self.assertEqual(percents[-1], 100)
            self.assertIn(8, percents)
            self.assertIn(15, percents)
            self.assertIn(98, percents)
            self.assertTrue(any(15 < percent < 95 for percent in percents))
            self.assertEqual(percents, sorted(percents))
            self.assertEqual(FakeBackend.instances[0].calls, 2)
        finally:
            pipeline.decode_to_pcm16k = original_decode
            pipeline.chunk_audio = original_chunk
            pipeline.QwenBackend = original_backend


if __name__ == "__main__":
    unittest.main()
