from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import API, page_url


class ApiTests(unittest.TestCase):
    def test_select_returns_the_chosen_media_name(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "voiceover.mp3"
            source.touch()
            self.assertEqual(API().select(str(source)), {"name": "voiceover.mp3"})
    def test_select_output_folder(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertEqual(API().select_output_folder(directory), {"path": directory})

    def test_page_url_is_a_filesystem_path_not_a_file_uri(self) -> None:
        self.assertFalse(page_url().startswith("file://"))
        self.assertTrue(Path(page_url()).is_file())


if __name__ == '__main__':
    unittest.main()
