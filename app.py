import sys
from pathlib import Path

import webview

from engine import SUPPORTED_SUFFIXES, separate


class API:
    def __init__(self) -> None:
        self.source: Path | None = None
        self.window: webview.Window | None = None

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

    def extract(self) -> dict[str, str]:
        if self.source is None:
            raise ValueError("Choose a file first.")
        target = separate(self.source)
        return {"path": str(target), "name": target.name}


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / name


def page_url() -> str:
    return str(resource_path("index.html"))


def main() -> None:
    api = API()
    window = webview.create_window(
        "VocalStripper",
        page_url(),
        js_api=api,
        width=560,
        height=430,
        min_size=(460, 360),
        background_color="#171717",
    )
    api.window = window
    webview.start()


if __name__ == "__main__":
    main()
