from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import sleep
import subprocess
import sys
import unittest

import app
from app import API, claim_instance, page_url


class ApiTests(unittest.TestCase):
    def test_select_returns_the_chosen_media_name(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "voiceover.mp3"
            source.touch()
            self.assertEqual(API().select(str(source)), {"name": "voiceover.mp3"})
    def test_select_output_folder(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertEqual(API().select_output_folder(directory), {"path": directory})

    def test_claim_instance_blocks_a_second_process(self) -> None:
        with TemporaryDirectory() as directory:
            lock = Path(directory) / "VocalStripper.lock"
            self.assertTrue(claim_instance(lock))
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from app import claim_instance; from pathlib import Path; import sys; sys.exit(0 if claim_instance(Path(sys.argv[1])) else 1)",
                        str(lock),
                    ],
                    cwd=Path(__file__).parents[1],
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
            finally:
                app._instance_lock.close()
                app._instance_lock = None

    def test_model_download_marks_the_app_ready(self) -> None:
        downloaded = Event()

        def downloader(status) -> None:
            status("Downloading HTDemucs model.")
            downloaded.set()

        with TemporaryDirectory() as directory:
            marker = Path(directory) / "model-ready"
            api = API(model_downloader=downloader, model_marker=marker)
            self.assertEqual(api.model_status()["state"], "missing")
            self.assertEqual(api.start_model_download(), {"state": "downloading"})
            self.assertTrue(downloaded.wait(1))
            for _ in range(20):
                model = api.model_status()
                if model["state"] != "downloading":
                    break
                sleep(0.01)
            self.assertEqual(model["state"], "ready")
            self.assertTrue(marker.is_file())
            self.assertEqual(model["events"][-1]["message"], "Model ready on this Mac.")

    def test_start_extract_requires_a_downloaded_model(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "voiceover.mp3"
            source.touch()
            api = API(model_marker=Path(directory) / "missing-model")
            api.select(str(source))
            with self.assertRaisesRegex(RuntimeError, "Download the HTDemucs model"):
                api.start_extract()

    def test_start_extract_records_completion_and_rejects_a_second_job(self) -> None:
        started = Event()
        finish = Event()

        def runner(source: Path, mode: str, status, output_dir: Path) -> Path:
            status(f"Separating {mode}.")
            started.set()
            finish.wait(2)
            target = output_dir / f"{source.stem}_{mode}.wav"
            target.touch()
            return target

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "voiceover.mp3"
            output = root / "output"
            source.touch()
            output.mkdir()
            marker = root / "model-ready"
            marker.touch()
            api = API(runner=runner, model_marker=marker)
            api.select(str(source))
            api.select_output_folder(str(output))
            self.assertEqual(api.start_extract(), {"state": "running"})
            self.assertTrue(started.wait(1))
            with self.assertRaisesRegex(RuntimeError, "already running"):
                api.start_extract()
            finish.set()
            for _ in range(20):
                job = api.job_status()
                if job["state"] == "done":
                    break
                sleep(0.01)
            self.assertEqual(job["state"], "done")
            self.assertEqual(job["path"], str(output / "voiceover_instrumental.wav"))
            self.assertIn("Saved voiceover_instrumental.wav.", job["events"][-1]["message"])

    def test_page_url_is_a_filesystem_path_not_a_file_uri(self) -> None:
        self.assertFalse(page_url().startswith("file://"))
        self.assertTrue(Path(page_url()).is_file())


if __name__ == '__main__':
    unittest.main()
