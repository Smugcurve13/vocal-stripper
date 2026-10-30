import shutil
import tempfile
from pathlib import Path
from typing import Callable

SUPPORTED_SUFFIXES = {".mp3", ".mp4", ".m4a", ".mov", ".wav"}


def device() -> str:
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def output_path(source: Path, mode: str, output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = Path.home() / "Downloads"
        output_dir.mkdir(exist_ok=True)
    return output_dir.expanduser() / f"{source.stem}_{mode}.wav"


def separate(
    source: Path,
    mode: str = "instrumental",
    status: Callable[[str], None] = print,
    output_dir: Path | None = None,
) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("Choose an MP3, MP4, M4A, MOV, or WAV file.")

    if mode not in {"instrumental", "vocals"}:
        raise ValueError("Choose instrumental or vocals.")

    from demucs.separate import main

    stem = "no_vocals" if mode == "instrumental" else "vocals"
    status(f"Loading model for {mode} separation.")
    with tempfile.TemporaryDirectory(prefix="vocal-stripper-") as temp_dir:
        status(f"Separating {mode} stem.")
        main(["--two-stems", "vocals", "--device", device(), "--out", temp_dir, str(source)])
        output = next(Path(temp_dir).rglob(f"{stem}.wav"), None)
        if output is None:
            raise RuntimeError(f"Demucs finished without producing {mode}.")
        status("Writing output file.")
        target = output_path(source, mode, output_dir)
        shutil.copy2(output, target)
    return target
