import shutil
import tempfile
from pathlib import Path
from typing import Callable

SUPPORTED_SUFFIXES = {".mp3", ".mp4", ".m4a", ".mov", ".wav"}


def device() -> str:
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def output_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}_vocals.wav")


def separate(source: Path, status: Callable[[str], None] = print) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("Choose an MP3, MP4, M4A, MOV, or WAV file.")

    from demucs.separate import main

    status("Separating vocals. The first run downloads Demucs's model.")
    with tempfile.TemporaryDirectory(prefix="vocal-stripper-") as temp_dir:
        main(["--two-stems", "vocals", "--device", device(), "--out", temp_dir, str(source)])
        vocals = next(Path(temp_dir).rglob("vocals.wav"), None)
        if vocals is None:
            raise RuntimeError("Demucs finished without producing a vocals file.")
        target = output_path(source)
        shutil.copy2(vocals, target)
    return target
