import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine import configure_ffmpeg_path, device, ffmpeg_directory, output_path


class OutputPathTests(unittest.TestCase):
    def test_output_path_saves_vocals_in_downloads(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'vocals'),
            Path.home() / 'Downloads' / 'Ad Clip_vocals.wav',
        )

    def test_output_path_uses_the_selected_folder(self) -> None:
        self.assertEqual(
            output_path(Path('/music/Ad Clip.mp4'), 'instrumental', Path('/output')),
            Path('/output/Ad Clip_instrumental.wav'),
        )

    def test_device_is_mps_or_cpu(self) -> None:
        self.assertIn(device(), {"mps", "cpu"})

    def test_bundled_ffmpeg_directory_requires_both_binaries(self) -> None:
        with TemporaryDirectory() as directory:
            base = Path(directory)
            ffmpeg_dir = base / "assets" / "ffmpeg" / "macos"
            ffmpeg_dir.mkdir(parents=True)
            (ffmpeg_dir / "ffmpeg").touch()
            self.assertIsNone(ffmpeg_directory(base))
            (ffmpeg_dir / "ffprobe").touch()
            self.assertEqual(ffmpeg_directory(base), ffmpeg_dir)

    def test_bundled_ffmpeg_is_added_to_path_first(self) -> None:
        with TemporaryDirectory() as directory:
            base = Path(directory)
            ffmpeg_dir = base / "assets" / "ffmpeg" / "macos"
            ffmpeg_dir.mkdir(parents=True)
            for name in ("ffmpeg", "ffprobe"):
                (ffmpeg_dir / name).touch()
            original_path = os.environ.get("PATH")
            try:
                os.environ["PATH"] = "/usr/bin"
                self.assertEqual(configure_ffmpeg_path(base), ffmpeg_dir)
                self.assertEqual(os.environ["PATH"].split(os.pathsep)[0], str(ffmpeg_dir))
            finally:
                if original_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = original_path


if __name__ == '__main__':
    unittest.main()
