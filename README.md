# VocalStripper

A minimal desktop app that extracts either the instrumental/no-vocals track or the vocal/spoken-word track from a local MP3, MP4, M4A, MOV, or WAV using Demucs.

Instrumental is the default and writes `<source>_instrumental.wav`; vocals writes `<source>_vocals.wav`. Both save to `~/Downloads`. The first extraction downloads the Demucs model.

## Run from source

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

FFmpeg must be available on your PATH for MP3/MP4 input. On macOS:

```bash
brew install ffmpeg
```

## Build a macOS app

```bash
.venv/bin/python -m pip install pyinstaller
.venv/bin/pyinstaller --windowed --name VocalStripper --add-data "index.html:." --hidden-import demucs.separate --collect-all demucs --collect-all torch --collect-all webview app.py
```

The app is created at `dist/VocalStripper.app`.
