import fcntl
import logging
import multiprocessing
import subprocess
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

import webview

from engine import SUPPORTED_SUFFIXES, download_model, separate

APP_DATA = Path.home() / "Library" / "Application Support" / "VocalStripper"
LOG_DIR = APP_DATA / "logs"
LOG_PATH = LOG_DIR / "vocalstripper.log"
MODEL_MARKER = APP_DATA / "htdemucs-ready"
LOCK_PATH = APP_DATA / "VocalStripper.lock"
_instance_lock = None


def claim_instance(lock_path: Path = LOCK_PATH) -> bool:
    global _instance_lock
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return False
    # ponytail: one app-wide lock; add multi-window support only if intentional.
    _instance_lock = handle
    return True


def app_logger() -> logging.Logger:
    logger = logging.getLogger("vocalstripper")
    if logger.handlers:
        return logger
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


logger = app_logger()


class API:
    def __init__(
        self,
        runner: Callable = separate,
        model_downloader: Callable = download_model,
        model_marker: Path = MODEL_MARKER,
    ) -> None:
        self.source: Path | None = None
        self.output_dir = Path.home() / "Downloads"
        self.window: webview.Window | None = None
        self.runner = runner
        self.model_downloader = model_downloader
        self.model_marker = model_marker
        self.model_lock = Lock()
        self.model = {
            "state": "ready" if model_marker.is_file() else "missing",
            "events": [],
            "error": None,
        }
        self.job_lock = Lock()
        self.job = {"state": "idle", "events": [], "path": None, "error": None}

    def _event(self, message: str) -> None:
        event = {"time": datetime.now().strftime("%H:%M:%S"), "message": message}
        with self.job_lock:
            self.job["events"].append(event)
        logger.info(message)

    def _model_event(self, message: str) -> None:
        event = {"time": datetime.now().strftime("%H:%M:%S"), "message": message}
        with self.model_lock:
            self.model["events"].append(event)
        logger.info(message)

    def model_status(self) -> dict:
        with self.model_lock:
            return {
                "state": self.model["state"],
                "events": list(self.model["events"]),
                "error": self.model["error"],
            }

    def start_model_download(self) -> dict[str, str]:
        with self.model_lock:
            if self.model["state"] == "ready":
                return {"state": "ready"}
            if self.model["state"] == "downloading":
                raise RuntimeError("The HTDemucs model is already downloading.")
            self.model = {"state": "downloading", "events": [], "error": None}
        self._model_event("Preparing HTDemucs model download.")
        Thread(target=self._download_model, daemon=True).start()
        return {"state": "downloading"}

    def _download_model(self) -> None:
        try:
            self.model_downloader(status=self._model_event)
        except Exception as error:
            logger.exception("Model download failed")
            self._model_event(f"Model download failed: {error}")
            with self.model_lock:
                self.model["state"] = "error"
                self.model["error"] = str(error)
            return
        self.model_marker.parent.mkdir(parents=True, exist_ok=True)
        self.model_marker.touch()
        self._model_event("Model ready on this Mac.")
        with self.model_lock:
            self.model["state"] = "ready"

    def select(self, filename: str) -> dict[str, str]:
        source = Path(filename)
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError("Choose an MP3, MP4, M4A, MOV, or WAV file.")
        self.source = source
        return {"name": source.name}

    def choose_file(self) -> dict[str, str] | None:
        if self.window is None:
            raise RuntimeError("Window is not ready.")
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Media files (*.mp3;*.mp4;*.m4a;*.mov;*.wav)",),
        )
        return self.select(files[0]) if files else None

    def select_output_folder(self, folder: str) -> dict[str, str]:
        output_dir = Path(folder).expanduser()
        if not output_dir.is_dir():
            raise ValueError("Choose an existing output folder.")
        self.output_dir = output_dir
        return {"path": str(output_dir)}

    def choose_output_folder(self) -> dict[str, str] | None:
        if self.window is None:
            raise RuntimeError("Window is not ready.")
        folders = self.window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=str(self.output_dir),
        )
        return self.select_output_folder(folders[0]) if folders else None

    def start_extract(self, mode: str = "instrumental") -> dict[str, str]:
        if not self.model_marker.is_file():
            raise RuntimeError("Download the HTDemucs model before separating audio.")
        if self.source is None:
            raise ValueError("Choose a file first.")
        with self.job_lock:
            if self.job["state"] == "running":
                raise RuntimeError("A separation is already running.")
            self.job = {"state": "running", "events": [], "path": None, "error": None}
        source, output_dir = self.source, self.output_dir
        self._event(f"Queued {source.name} for {mode} separation.")
        Thread(target=self._run, args=(source, output_dir, mode), daemon=True).start()
        return {"state": "running"}

    def _run(self, source: Path, output_dir: Path, mode: str) -> None:
        try:
            target = self.runner(source, mode, status=self._event, output_dir=output_dir)
        except Exception as error:
            logger.exception("Separation failed")
            self._event(f"Failed: {error}")
            with self.job_lock:
                self.job["state"] = "error"
                self.job["error"] = str(error)
            return
        self._event(f"Saved {target.name}.")
        with self.job_lock:
            self.job["state"] = "done"
            self.job["path"] = str(target)

    def job_status(self) -> dict:
        with self.job_lock:
            return {
                "state": self.job["state"],
                "events": list(self.job["events"]),
                "path": self.job["path"],
                "error": self.job["error"],
            }

    def reveal_output(self) -> None:
        with self.job_lock:
            path = self.job["path"]
        if not path:
            raise ValueError("No completed output yet.")
        subprocess.Popen(["open", "-R", path])

    def reveal_logs(self) -> None:
        subprocess.Popen(["open", str(LOG_DIR)])


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / name


def page_url() -> str:
    return str(resource_path("index.html"))


def main() -> None:
    if not claim_instance():
        return
    api = API()
    window = webview.create_window(
        "VocalStripper",
        page_url(),
        js_api=api,
        width=632,
        height=732,
        resizable=False,
        background_color="#171717",
    )
    api.window = window
    webview.start()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
