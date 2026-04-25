from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Input, ProgressBar, Select, Button, Footer
from modules.download import Download, DownloadError, DownloadCancelledError
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json

LINES_CODEC = "M4A\nMP3\nFLAC\nOpus".splitlines()
LINES_KBPS = "320\n256\n128\n64".splitlines()
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, PermissionError, OSError):
        return {}


class Rhythmer(App):
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.theme = "tokyo-night"
        self.current_download_task = None
        self.download_cancelled = False
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.selected_codec = "opus"
        self.selected_kbps = 256

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            yield Input(id="url_input", placeholder="Enter your URL", type="text")
            yield ProgressBar(id="download_progress", total=100, show_percentage=True)

            with Vertical(classes="select_row"):
                yield Select(
                    ((line, line.lower()) for line in LINES_CODEC),
                    id="codec_select",
                    prompt="Choose a codec",
                    value=self.selected_codec,
                )
                yield Select(
                    ((line, str(line)) for line in LINES_KBPS),
                    id="kbps_select",
                    prompt="Select the number of kbps",
                    value=str(self.selected_kbps),
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
            self.selected_codec = str(event.value).lower()
        elif event.select.id == "kbps_select":
            try:
                self.selected_kbps = int(event.value)
            except (ValueError, TypeError):
                self.selected_kbps = 256
                self.notify(
                    "Invalid bitrate, using default 256kbps", severity="warning"
                )

    def update_progress(self, value: int) -> None:
        if not self.download_cancelled:
            self.call_from_thread(self._update_progress_ui, value)

    def _update_progress_ui(self, value: int) -> None:
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=min(value, 100))
            if value >= 100:
                self._handle_download_complete(True)
        except Exception:
            pass

    def _handle_download_complete(self, success: bool, message: str = "") -> None:
        self.download_cancelled = False
        self.current_download_task = None
        self._reset_ui_after_download()

        if success:
            self.notify("✅ Download completed!", severity="information", timeout=5)
            self.set_timer(2, self._hide_progress)
        else:
            self.notify(
                f"❌ {message}" if message else "❌ Download failed",
                severity="error",
                timeout=5,
            )
            self._hide_progress()

    def _reset_ui_after_download(self) -> None:
        try:
            self.query_one("#accept_button", Button).disabled = False
            self.query_one("#cancel_button", Button).disabled = True
            url_input = self.query_one("#url_input", Input)
            url_input.disabled = False
            url_input.focus()
        except Exception:
            pass

    def _show_progress(self) -> None:
        progress = self.query_one("#download_progress", ProgressBar)
        progress.update(total=100, progress=0)
        progress.styles.opacity = 1

    def _hide_progress(self) -> None:
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=0)
            progress.styles.opacity = 0
        except Exception:
            pass

    async def download_with_progress(self, url: str) -> None:
        def check_cancelled():
            return self.download_cancelled

        try:
            program = Download(
                url=url, codec=self.selected_codec, kbps=self.selected_kbps
            )
            program.set_progress_callback(self.update_progress)
            program.set_cancel_check(check_cancelled)

            loop = asyncio.get_event_loop()
            download_task = loop.run_in_executor(self.executor, program.download)

            while not download_task.done():
                if self.download_cancelled:
                    program.cancel()
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(download_task), timeout=2.0
                        )
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        download_task.cancel()
                    self.call_from_thread(
                        self._handle_download_complete, False, "Download cancelled"
                    )
                    return
                await asyncio.sleep(0.1)

            if not self.download_cancelled:
                try:
                    if download_task.result():
                        self.call_from_thread(self._handle_download_complete, True)
                    else:
                        self.call_from_thread(
                            self._handle_download_complete, False, "Download failed"
                        )
                except DownloadCancelledError:
                    self.call_from_thread(
                        self._handle_download_complete, False, "Download cancelled"
                    )
                except DownloadError as e:
                    self.call_from_thread(self._handle_download_complete, False, str(e))
                except Exception as e:
                    self.call_from_thread(
                        self._handle_download_complete, False, f"Error: {e}"
                    )

        except DownloadCancelledError:
            self.call_from_thread(
                self._handle_download_complete, False, "Download cancelled"
            )
        except DownloadError as e:
            self.call_from_thread(self._handle_download_complete, False, str(e))
        except Exception as e:
            self.call_from_thread(self._handle_download_complete, False, f"Error: {e}")

    @on(Button.Pressed, "#accept_button")
    async def action_accept_url(self) -> None:
        if not CONFIG_PATH.exists():
            self.notify("Config not found! Run: python add_path.py", severity="error")
            return

        url_input = self.query_one("#url_input", Input)
        url = url_input.value.strip()

        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        if not url.startswith(("http://", "https://")):
            self.notify("Invalid URL", severity="error")
            return

        try:
            self.query_one("#accept_button", Button).disabled = True
            self.query_one("#cancel_button", Button).disabled = False
            url_input.disabled = True

            self._show_progress()
            self.notify(
                f"Downloading {self.selected_codec.upper()} @ {self.selected_kbps}kbps..."
            )
            self.download_cancelled = False
            self.current_download_task = asyncio.create_task(
                self.download_with_progress(url=url)
            )

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self._reset_ui_after_download()

    @on(Button.Pressed, "#cancel_button")
    async def action_cancel_download(self) -> None:
        if self.current_download_task and not self.current_download_task.done():
            self.download_cancelled = True
            self.notify("Cancelling...", severity="warning")
            try:
                await asyncio.wait_for(self.current_download_task, timeout=3.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        else:
            self._reset_ui_after_download()
            self.query_one("#url_input", Input).value = ""
            self._hide_progress()

    def on_unmount(self) -> None:
        if self.current_download_task and not self.current_download_task.done():
            self.download_cancelled = True
            self.current_download_task.cancel()
        self.executor.shutdown(wait=True, cancel_futures=True)


if __name__ == "__main__":
    Rhythmer().run()
