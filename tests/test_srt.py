from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt.srt import Subtitle, format_timestamp, render_srt


class SrtTests(unittest.TestCase):
    def test_timestamp_format(self):
        self.assertEqual(format_timestamp(3723.456), "01:02:03,456")

    def test_render_srt_normalizes_overlap(self):
        content = render_srt(
            [
                Subtitle(0.0, 1.0, "Hello"),
                Subtitle(0.5, 1.5, "World"),
            ]
        )
        self.assertIn("00:00:00,000 --> 00:00:01,000", content)
        self.assertIn("00:00:01,000 --> 00:00:01,500", content)


if __name__ == "__main__":
    unittest.main()

