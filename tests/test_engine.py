from pathlib import Path
import unittest

from engine import device, output_path


class OutputPathTests(unittest.TestCase):
    def test_output_path_keeps_the_source_next_to_its_vocals_file(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'vocals'),
            Path('/music/Ad Clip_vocals.wav'),
        )

    def test_output_path_names_the_no_vocals_stem_as_instrumental(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'instrumental'),
            Path('/music/Ad Clip_instrumental.wav'),
        )

    def test_device_is_mps_or_cpu(self) -> None:
        self.assertIn(device(), {"mps", "cpu"})


if __name__ == '__main__':
    unittest.main()
