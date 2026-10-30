# VocalStripper

A minimal desktop app that extracts either the instrumental/no-vocals track or the vocal/spoken-word track from a local MP3, MP4, M4A, MOV, or WAV using Demucs.

Instrumental is the default and writes `<source>_instrumental.wav`; vocals writes `<source>_vocals.wav`. `~/Downloads` is the default output folder, and the app can change it before extraction. On first launch, the app requires an explicit HTDemucs model download; the model is stored locally and is not bundled in the app. Each run has a live in-app activity log, saves diagnostics under `~/Library/Application Support/VocalStripper/logs/`, and shows a completion panel with Reveal in Finder.

## Run from source

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

FFmpeg is bundled in the macOS app as an additional third-party dependency, so packaged builds can read MP3 and MP4 files without a separate FFmpeg installation. Source runs use the `ffmpeg` available on your PATH:

```bash
brew install ffmpeg
```

Read the in-app [Privacy & dependencies](privacy.html) page for the local-processing policy, model-download network use, and FFmpeg notice.

## Build a macOS app

First fetch the pinned Apple Silicon FFmpeg and FFprobe binaries, then build:

```bash
./scripts/fetch_ffmpeg_macos.sh
.venv/bin/python -m pip install pyinstaller
.venv/bin/pyinstaller --windowed --name VocalStripper --icon assets/VocalStripper.icns --add-data "index.html:." --add-data "privacy.html:." --add-data "assets/logo.svg:assets" --add-binary "assets/ffmpeg/macos/ffmpeg:assets/ffmpeg/macos" --add-binary "assets/ffmpeg/macos/ffprobe:assets/ffmpeg/macos" --hidden-import demucs.separate --collect-submodules demucs --collect-data demucs --collect-all torch --collect-all webview app.py
```

The app is created at `dist/VocalStripper.app`.
