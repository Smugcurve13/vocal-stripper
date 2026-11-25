"""GitHub release updates for the packaged macOS app."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import certifi
from packaging.version import InvalidVersion, Version

from version import __version__

REPO = "Smugcurve13/vocal-stripper"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
_HEADERS = {"User-Agent": f"VocalStripper/{__version__}", "Accept": "application/vnd.github+json"}
_CHUNK = 1 << 20
_TIMEOUT = 60
_STAGING_NAME = ".vocalstripper-update"
_FAILED_NAME = ".vocalstripper-update-failed"
_FREE_SPACE_FLOOR = 1_000_000_000
logger = logging.getLogger("vocalstripper")


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def app_root() -> Path | None:
    if not (getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")):
        return None
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None


def _is_newer(tag: str) -> bool:
    try:
        return Version(tag.lstrip("vV")) > Version(__version__)
    except InvalidVersion:
        logger.warning("Ignoring unparseable release tag: %s", tag)
        return False


def _pick_asset(assets: list[dict]) -> dict | None:
    for asset in assets:
        name = asset.get("name", "")
        if "macos-arm64" in name and name.endswith(".zip"):
            return asset
    return None


def check() -> dict | None:
    if app_root() is None:
        return None
    _sweep()
    try:
        request = urllib.request.Request(LATEST_URL, headers=_HEADERS)
        with urllib.request.urlopen(request, timeout=15, context=_ssl_context()) as response:
            release = json.load(response)
    except Exception as error:
        logger.warning("Update check failed: %s", error)
        return None
    tag = release.get("tag_name", "")
    asset = _pick_asset(release.get("assets", []))
    if not _is_newer(tag) or asset is None:
        return None
    return {"version": tag, "url": asset["browser_download_url"], "size": asset.get("size", 0), "notes_url": release.get("html_url", RELEASES_URL)}


def blocked_reason(needed_bytes: int = 0) -> str | None:
    app = app_root()
    if app is None:
        return "In-app updates only work in a released build."
    if "/AppTranslocation/" in str(app):
        return "Move VocalStripper to Applications, reopen it, then update."
    probe = app.parent / f".vocalstripper-update-probe-{os.getpid()}"
    try:
        probe.mkdir()
        probe.rmdir()
    except OSError:
        return f"VocalStripper cannot write to {app.parent}. Move it somewhere you own, or update manually."
    try:
        free = shutil.disk_usage(app.parent).free
    except OSError:
        free = _FREE_SPACE_FLOOR
    if free < max(_FREE_SPACE_FLOOR, needed_bytes * 4):
        return "Not enough free disk space to install the update."
    return None


def _sweep() -> None:
    app = app_root()
    if app is None:
        return
    shutil.rmtree(Path(f"{app}.old"), ignore_errors=True)
    shutil.rmtree(app.parent / _STAGING_NAME, ignore_errors=True)


def download(url: str, destination: Path, progress_callback=None, is_cancelled=None) -> bool:
    request = urllib.request.Request(url, headers={**_HEADERS, "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT, context=_ssl_context()) as response:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        with destination.open("wb") as output:
            while chunk := response.read(_CHUNK):
                if is_cancelled and is_cancelled():
                    output.close()
                    destination.unlink(missing_ok=True)
                    return False
                output.write(chunk)
                read += len(chunk)
                if progress_callback:
                    progress_callback(read, total)
    with zipfile.ZipFile(destination) as archive:
        top_level = {name.split("/", 1)[0] for name in archive.namelist()} - {"", "__MACOSX"}
    if len(top_level) != 1:
        destination.unlink(missing_ok=True)
        raise OSError("Downloaded update has an unexpected archive layout.")
    return True


def consume_failure() -> bool:
    app = app_root()
    if app is None:
        return False
    marker = app.parent / _FAILED_NAME
    if not marker.exists():
        return False
    marker.unlink(missing_ok=True)
    return True


_MACOS_HELPER = r'''#!/bin/sh
PID="$1"; APP="$2"; NEW="$3"; STAGING="$4"; FAILED="$5"
while kill -0 "$PID" 2>/dev/null; do sleep 0.2; done
OLD="$APP.old"
rm -rf "$OLD"
mv "$APP" "$OLD" 2>/dev/null || { : > "$FAILED"; open -n "$APP"; rm -f "$0"; exit 1; }
if mv "$NEW" "$APP"; then
  xattr -dr com.apple.quarantine "$APP" 2>/dev/null
  open -n "$APP"
  rm -rf "$OLD" "$STAGING"
else
  mv "$OLD" "$APP"
  : > "$FAILED"
  open -n "$APP"
fi
rm -f "$0"
'''


def apply(zip_path: Path) -> None:
    app = app_root()
    if app is None:
        raise RuntimeError("In-app updates only work in a released build.")
    staging = app.parent / _STAGING_NAME
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    subprocess.run(["/usr/bin/ditto", "-x", "-k", "--noqtn", str(zip_path), str(staging)], check=True, capture_output=True)
    entries = [entry for entry in staging.iterdir() if not entry.name.startswith((".", "__MACOSX"))]
    if len(entries) != 1 or entries[0].suffix != ".app":
        raise RuntimeError("Downloaded update has an unexpected app bundle.")
    failed = app.parent / _FAILED_NAME
    failed.unlink(missing_ok=True)
    fd, script = tempfile.mkstemp(prefix="vocalstripper-update-", suffix=".sh")
    with os.fdopen(fd, "w") as handle:
        handle.write(_MACOS_HELPER)
    os.chmod(script, 0o755)
    subprocess.Popen(["/bin/sh", script, str(os.getpid()), str(app), str(entries[0]), str(staging), str(failed)], start_new_session=True, cwd=tempfile.gettempdir(), close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    assert _is_newer("v0.0.6")
    assert not _is_newer("v0.0.5")
    assert _pick_asset([{"name": "VocalStripper-macos-arm64-v0.0.6.zip"}]) is not None
    assert _pick_asset([{"name": "VocalStripper-windows-v0.0.6.zip"}]) is None
    assert app_root() is None
    assert check() is None
