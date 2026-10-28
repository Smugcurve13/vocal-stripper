from pathlib import Path
import unittest

from engine import device, output_path


class OutputPathTests(unittest.TestCase):
    def test_output_path_saves_vocals_in_downloads(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'vocals'),
            Path.home() / 'Downloads' / 'Ad Clip_vocals.wav',
        )

    def test_output_path_saves_instrumentals_in_downloads(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'instrumental'),
            Path.home() / 'Downloads' / 'Ad Clip_instrumental.wav',
        )

    def test_device_is_mps_or_cpu(self) -> None:
        self.assertIn(device(), {"mps", "cpu"})


if __name__ == '__main__':
    unittest.main()
