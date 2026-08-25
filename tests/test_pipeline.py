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
    def test_progress_only_reports_measured_percentages(self):
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
            progress_events = [event for event in events if event.get("type") == "progress"]
            busy_events = [event for event in progress_events if event.get("mode") == "indeterminate"]
            measured_events = [event for event in progress_events if event.get("mode") == "determinate"]
            self.assertTrue(busy_events)
            self.assertTrue(all("percent" not in event for event in busy_events))
            measured_percents = [event["percent"] for event in measured_events]
            self.assertEqual(measured_percents, sorted(measured_percents))
            self.assertEqual(sorted(set(measured_percents)), [0, 50, 100])
            first_completed_chunk = next(event for event in measured_events if event["percent"] == 50)
            self.assertEqual(first_completed_chunk["completed_audio_seconds"], 1.0)
            self.assertEqual(first_completed_chunk["total_audio_seconds"], 2.0)
            self.assertTrue(any(event["stage"] == "decoding media" for event in busy_events))
            self.assertTrue(any(event["stage"] == "loading transcription model" for event in busy_events))
            self.assertTrue(any(event["stage"] == "writing SRT" for event in measured_events))
            self.assertEqual(FakeBackend.instances[0].calls, 2)
        finally:
            pipeline.decode_to_pcm16k = original_decode
            pipeline.chunk_audio = original_chunk
            pipeline.QwenBackend = original_backend

    def test_single_chunk_stays_indeterminate_until_audio_is_finished(self):
        original_decode = pipeline.decode_to_pcm16k
        original_chunk = pipeline.chunk_audio
        original_backend = pipeline.QwenBackend
        try:
            audio = np.zeros(16_000, dtype=np.float32)
            pipeline.decode_to_pcm16k = lambda _path: (audio, 1.0)
            pipeline.chunk_audio = lambda _audio, _seconds: [(0.0, audio)]
            pipeline.QwenBackend = FakeBackend
            events = []
            with tempfile.TemporaryDirectory() as tmpdir:
                pipeline.transcribe_file(
                    Path(tmpdir) / "input.wav",
                    Path(tmpdir) / "output.srt",
                    device="cpu",
                    progress=events.append,
                )

            progress_events = [event for event in events if event.get("type") == "progress"]
            first_measured = next(index for index, event in enumerate(progress_events) if "percent" in event)
            self.assertTrue(all(event["mode"] == "indeterminate" for event in progress_events[:first_measured]))
            self.assertTrue(all(event["percent"] == 100 for event in progress_events[first_measured:]))
        finally:
            pipeline.decode_to_pcm16k = original_decode
            pipeline.chunk_audio = original_chunk
            pipeline.QwenBackend = original_backend


if __name__ == "__main__":
    unittest.main()
