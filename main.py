from threading import Thread

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, ProgressBar, Select

from modules.download import Download, DownloadCancelledError, DownloadError

LINES_CODEC = ["M4A", "MP3", "FLAC", "Opus"]
LINES_KBPS = ["320", "256", "128", "64"]


class Rhythmer(App):
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        self.theme = "tokyo-night"
        self.codec = "opus"
        self.kbps = 256
        self.download_thread = None
        self.downloading = False
        self.cancelled = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            yield Input(id="url_input", placeholder="Enter your URL", type="text")
            yield ProgressBar(id="download_progress", total=100, show_percentage=True)

            with Vertical(classes="select_row"):
                yield Select(
                    ((codec, codec.lower()) for codec in LINES_CODEC),
                    id="codec_select",
                    prompt="Choose a codec",
                    value="opus",
                )
                yield Select(
                    ((kbps, kbps) for kbps in LINES_KBPS),
                    id="kbps_select",
                    prompt="Select the number of kbps",
                    value="256",
                )

            with Horizontal(classes="button_row"):
                yield Button("Download", variant="success", id="accept_button")
                yield Button(
                    "Cancel", variant="error", id="cancel_button", disabled=True
                )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#download_progress", ProgressBar).styles.opacity = 0

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "codec_select":
            self.codec = str(event.value).lower()
        elif event.select.id == "kbps_select":
            self.kbps = int(event.value)

    def update_progress(self, value: int) -> None:
        if not self.cancelled:
            self.call_from_thread(self._update_progress_ui, value)

    def _update_progress_ui(self, value: int) -> None:
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=value)
        except Exception:
            pass

    def check_cancelled(self) -> bool:
        return self.cancelled

    def _start_download(self, url: str) -> None:
        try:
            downloader = Download(url=url, codec=self.codec, kbps=self.kbps)
            downloader.set_progress_callback(self.update_progress)
            downloader.set_cancel_check(self.check_cancelled)

            success = downloader.download()

            if success:
                self.call_from_thread(
                    self._download_complete, True, "Download completed!"
                )
            else:
                self.call_from_thread(self._download_complete, False, "Download failed")

        except DownloadCancelledError:
            self.call_from_thread(self._download_complete, False, "Download cancelled")
        except DownloadError as e:
            self.call_from_thread(self._download_complete, False, str(e))
        except Exception as e:
            self.call_from_thread(self._download_complete, False, f"Error: {e}")

    def _download_complete(self, success: bool, message: str) -> None:
        self.downloading = False
        self.download_thread = None
        self.cancelled = False

        accept_button = self.query_one("#accept_button", Button)
        cancel_button = self.query_one("#cancel_button", Button)
        url_input = self.query_one("#url_input", Input)

        accept_button.disabled = False
        cancel_button.disabled = True
        url_input.disabled = False
        url_input.value = ""
        url_input.focus()

        emoji = "✅" if success else "❌"
        self.notify(
            f"{emoji} {message}", severity="information" if success else "error"
        )

        self.set_timer(3, self._hide_progress)

    def _hide_progress(self) -> None:
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=0)
            progress.styles.opacity = 0
        except Exception:
            pass

    @on(Button.Pressed, "#accept_button")
    def action_download(self) -> None:
        url_input = self.query_one("#url_input", Input)
        url = url_input.value.strip()

        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        if not url.startswith(("http://", "https://")):
            self.notify("Invalid URL", severity="error")
            return

        self.cancelled = False
        self.downloading = True
        self.query_one("#accept_button", Button).disabled = True
        self.query_one("#cancel_button", Button).disabled = False
        url_input.disabled = True

        progress = self.query_one("#download_progress", ProgressBar)
        progress.update(total=100, progress=0)
        progress.styles.opacity = 1

        self.notify(f"Downloading {self.codec.upper()} @ {self.kbps}kbps...")

        self.download_thread = Thread(
            target=self._start_download, args=(url,), daemon=True
        )
        self.download_thread.start()

    @on(Button.Pressed, "#cancel_button")
    def action_cancel(self) -> None:
        if self.downloading:
            self.cancelled = True
            self.notify("Cancelling...", severity="warning")
        else:
            self._download_complete(True, "Nothing to cancel")

    def on_unmount(self) -> None:
        self.cancelled = True


if __name__ == "__main__":
    Rhythmer().run()
