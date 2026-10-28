from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import API


class ApiTests(unittest.TestCase):
    def test_select_returns_the_chosen_media_name(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "voiceover.mp3"
            source.touch()
            self.assertEqual(API().select(str(source)), {"name": "voiceover.mp3"})


if __name__ == '__main__':
    unittest.main()
