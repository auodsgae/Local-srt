from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt.app import Job, format_job_row


class AppTests(unittest.TestCase):
    def test_job_row_keeps_last_completed_percentage_while_working(self):
        job = Job(Path("input.mp4"), Path("input.srt"), status="transcribing", percent=0)
        self.assertEqual(format_job_row(job), "input.mp4 -> input.srt    [0% transcribing]")

    def test_measured_job_row_shows_percentage(self):
        job = Job(Path("input.mp4"), Path("input.srt"), status="processed chunk 1/2", percent=50)
        self.assertEqual(format_job_row(job), "input.mp4 -> input.srt    [50% processed chunk 1/2]")


if __name__ == "__main__":
    unittest.main()
