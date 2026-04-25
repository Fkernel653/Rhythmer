from yt_dlp import YoutubeDL
from modules.add_metadata import add_metadata
from dataclasses import dataclass, field
from typing import Optional, Callable
from pathlib import Path
import json
import threading


class DownloadError(Exception):
    pass


class DownloadCancelledError(DownloadError):
    pass


@dataclass
class Download:
    url: str
    codec: Optional[str]
    kbps: Optional[int]
    progress_callback: Optional[Callable] = field(default=None, repr=False)
    cancel_check_callback: Optional[Callable] = field(default=None, repr=False)

    _config_path: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "config.json",
        init=False,
        repr=False,
    )
    _ydl: Optional[YoutubeDL] = field(default=None, init=False, repr=False)
    _cancelled: bool = field(default=False, init=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def _get_download_path(self) -> Path:
        if not self._config_path.exists():
            raise DownloadError(
                f"Config file not found at {self._config_path}\n"
                "Please run 'config' command first to set download path."
            )

        with open(self._config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data.get("path"):
            raise DownloadError("Config file missing 'path' key")

        path = Path(data["path"])
        path.mkdir(parents=True, exist_ok=True)
        return path

    def set_progress_callback(self, callback: Callable) -> None:
        self.progress_callback = callback

    def set_cancel_check(self, callback: Callable) -> None:
        self.cancel_check_callback = callback

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    def _check_cancelled(self) -> None:
        if self._cancelled or (
            self.cancel_check_callback and self.cancel_check_callback()
        ):
            self._cancelled = True
            raise DownloadCancelledError("Download cancelled by user")

    def progress_hook(self, d: dict) -> None:
        try:
            self._check_cancelled()
        except DownloadCancelledError:
            raise Exception("Download cancelled")

        if self.progress_callback:
            percent = 0
            if d["status"] == "downloading":
                percent_str = d.get("_percent_str", "0%").rstrip("%")
                try:
                    percent = float(percent_str)
                except ValueError:
                    pass

                if percent == 0 and d.get("total_bytes") and d["total_bytes"] > 0:
                    percent = (d.get("downloaded_bytes", 0) / d["total_bytes"]) * 100
                elif (
                    percent == 0
                    and d.get("total_bytes_estimate")
                    and d["total_bytes_estimate"] > 0
                ):
                    percent = (
                        d.get("downloaded_bytes", 0) / d["total_bytes_estimate"]
                    ) * 100

                if percent > 0:
                    self.progress_callback(int(min(percent, 99)))
            elif d["status"] == "processing":
                self.progress_callback(99)
            elif d["status"] == "finished":
                self.progress_callback(100)

    def download(self) -> bool:
        self._check_cancelled()
        download_path = self._get_download_path()

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(download_path / "%(title)s.%(ext)s"),
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.codec,
                    "preferredquality": str(self.kbps),
                },
                {"key": "EmbedThumbnail"},
            ],
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
            "nooverwrites": True,
        }

        try:
            with YoutubeDL(opts) as ydl:
                self._ydl = ydl
                self._check_cancelled()

                info = ydl.extract_info(self.url, download=False)
                filename = ydl.prepare_filename(info)
                file_path = (
                    None
                    if "%" in filename
                    else Path(filename).with_suffix(f".{self.codec}")
                )

                ydl.process_info(info)

                if file_path is None:
                    file_path = Path(
                        info.get("requested_downloads", [{}])[0].get("filepath", "")
                    )
                    if not file_path or not file_path.exists():
                        raise DownloadError("Could not determine downloaded file path")

                title = info.get("title", "")
                artist = info.get("uploader") or info.get("channel") or ""
                album = info.get("album") or info.get("channel") or ""

                self._check_cancelled()

            result = add_metadata(
                file=file_path,
                codec=self.codec,
                title=title,
                artist=artist,
                album=album,
            )

            if self.progress_callback:
                self.progress_callback(100)

            return result

        except DownloadCancelledError:
            raise
        except Exception as e:
            if self._cancelled:
                raise DownloadCancelledError("Download cancelled by user")

            error_msg = str(e)
            errors = {
                "HTTP Error 403": "Access forbidden (403). The site may be blocking the request.",
                "HTTP Error 404": "Video not found (404). Please check the URL.",
                "Unsupported URL": f"Unsupported URL: {self.url}",
                "This video is not available": "This video is not available or is private.",
                "Sign in to confirm your age": "This video requires age verification.",
            }

            for key, msg in errors.items():
                if key in error_msg:
                    raise DownloadError(msg)

            raise DownloadError(f"Download failed: {e}")
        finally:
            self._ydl = None
