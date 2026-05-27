from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt.config import app_data_dir


class ConfigTests(unittest.TestCase):
    def test_app_data_dir_uses_portable_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"LOCAL_SRT_APP_DATA": tmpdir}):
                self.assertEqual(app_data_dir(), Path(tmpdir))


if __name__ == "__main__":
    unittest.main()
