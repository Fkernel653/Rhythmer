"""
Simple YouTube audio downloader with progress tracking for Textual.
"""

import json
import threading
from pathlib import Path
from shutil import which
from typing import Any, Callable, Dict, Optional

from yt_dlp import YoutubeDL


class DownloadError(Exception):
    pass


class DownloadCancelledError(DownloadError):
    pass


class Download:
    """Simple YouTube audio downloader with progress tracking."""

    def __init__(self, url: str, codec: str = "opus", kbps: int = 256):
        self.url = url
        self.codec = codec
        self.kbps = kbps
        self._progress_callback: Optional[Callable[[int], None]] = None
        self._cancel_callback: Optional[Callable[[], bool]] = None
        self._cancelled = False
        self._lock = threading.Lock()
        self._last_progress = 0

        # Validate requirements
        if which("ffmpeg") is None:
            raise DownloadError("FFmpeg not found in PATH!")

        config_file = Path(__file__).parent.parent / "config.json"
        if not config_file.exists():
            raise DownloadError("Config not found!")

        try:
            data = json.loads(config_file.read_text("utf-8"))
            self._download_path = data["path"]
        except (json.JSONDecodeError, KeyError) as e:
            raise DownloadError(f"Invalid config: {e}")

    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for progress updates (0-100)."""
        self._progress_callback = callback

    def set_cancel_check(self, callback: Callable[[], bool]) -> None:
        """Set callback to check if download should be cancelled."""
        self._cancel_callback = callback

    def cancel(self) -> None:
        """Cancel the current download."""
        with self._lock:
            self._cancelled = True

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Progress hook for yt-dlp."""
        if self._cancelled or (self._cancel_callback and self._cancel_callback()):
            raise DownloadCancelledError("Download cancelled")

        if not self._progress_callback:
            return

        status = d.get("status", "")

        if status == "downloading":
            percent_str = d.get("_percent_str", "0%")
            if percent_str and percent_str != "N/A":
                try:
                    percent = float(percent_str.rstrip("%"))
                except ValueError, AttributeError:
                    percent = 0
            else:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                percent = (downloaded / total * 100) if total > 0 else 0

            progress = int(min(percent, 99))
            if progress > self._last_progress:
                self._last_progress = progress
                self._progress_callback(progress)

        elif status == "processing":
            if self._last_progress < 99:
                self._last_progress = 99
                self._progress_callback(99)

        elif status == "finished":
            if self._last_progress < 100:
                self._last_progress = 100
                self._progress_callback(100)

    def download(self) -> bool:
        """Download audio from URL. Returns True if successful."""
        self._cancelled = False
        self._last_progress = 0

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(Path(self._download_path) / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "nooverwrites": True,
            "writethumbnail": True,
            "progress_hooks": [self._progress_hook],
            "noprogress": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.codec,
                    "preferredquality": str(self.kbps),
                },
                {"key": "EmbedThumbnail"},
            ],
        }

        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([self.url])

            if self._progress_callback:
                self._progress_callback(100)
            return True

        except DownloadCancelledError:
            raise
        except Exception as e:
            if self._cancelled:
                raise DownloadCancelledError("Download cancelled")
            raise DownloadError(f"Download failed: {e}")
