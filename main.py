from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Input, ProgressBar, Select, Button, Footer
from textual.message import Message

from modules.download import Download, DownloadError, DownloadCancelledError
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Available codec options for audio conversion
LINES_CODEC = """M4A
MP3
FLAC
Opus""".splitlines()

# Available bitrate options
LINES_KBPS = """320
256
128
64""".splitlines()


class DownloadComplete(Message):
    """Message sent when download completes"""

    def __init__(self, success: bool, message: str = ""):
        super().__init__()
        self.success = success
        self.message = message


class Rhythmer(App):
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        self.theme = "tokyo-night"

        # Async task tracking
        self.current_download_task = None
        self.download_cancelled = False
        # Thread pool for blocking download operations
        self.executor = ThreadPoolExecutor(max_workers=1)

        # Default conversion settings
        self.selected_codec = "opus"
        self.selected_kbps = 256

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        with Container(id="main_container"):
            yield Input(id="url_input", placeholder="Enter your URL", type="text")
            yield ProgressBar(id="download_progress", total=100, show_percentage=True)

            with Vertical(classes="select_row"):
                yield Select(
                    ((line, line.lower()) for line in LINES_CODEC),
                    id="codec_select",
                    prompt="Choose a codec",
                )
                yield Select(
                    ((line, str(line)) for line in LINES_KBPS),
                    id="kbps_select",
                    prompt="Select the number of kbps",
                )

            with Horizontal(classes="button_row"):
                yield Button("Download", variant="success", id="accept_button")
                yield Button(
                    "Cancel", variant="error", id="cancel_button", disabled=True
                )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize UI state"""
        # Hide progress bar initially
        self.query_one("#download_progress", ProgressBar).styles.opacity = 0

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        """Handle codec/bitrate selection changes"""
        match event.select.id:
            case "codec_select":
                self.selected_codec = str(event.value).lower()
            case "kbps_select":
                try:
                    self.selected_kbps = int(event.value)
                except (ValueError, TypeError):
                    self.selected_kbps = 256  # Fallback to default
                    self.notify(
                        "Invalid bitrate selected, using default 256kbps",
                        severity="warning",
                    )

    def update_progress(self, value: int) -> None:
        """Thread-safe progress update called from download thread"""
        if not self.download_cancelled:
            self.call_from_thread(self._update_progress_ui, value)

    def _update_progress_ui(self, value: int) -> None:
        """Update progress bar on UI thread"""
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=min(value, 100))

            # Auto-handle completion when reaching 100%
            if value >= 100:
                self._handle_download_complete(True, "")
        except Exception:
            pass

    def _handle_download_complete(self, success: bool, message: str = "") -> None:
        """Handle download completion or failure"""
        self.download_cancelled = False
        self.current_download_task = None

        self._reset_ui_after_download()

        if success:
            self.notify(
                "✅ Download completed successfully!", severity="information", timeout=5
            )
            self.set_timer(2, self.action_progressbar_stop)  # Hide bar after delay
        else:
            error_msg = (
                f"❌ Download failed: {message}" if message else "❌ Download failed"
            )
            self.notify(error_msg, severity="error", timeout=5)
            self.action_progressbar_stop()

    def _reset_ui_after_download(self) -> None:
        """Reset UI state after download/cancel"""
        try:
            accept_button = self.query_one("#accept_button", Button)
            cancel_button = self.query_one("#cancel_button", Button)
            url_input = self.query_one("#url_input", Input)

            accept_button.disabled = False
            cancel_button.disabled = True
            url_input.disabled = False
            url_input.focus()
        except Exception as e:
            print(f"Error resetting UI: {e}")

    def action_progressbar_start(self) -> None:
        """Show and reset progress bar"""
        progress = self.query_one("#download_progress", ProgressBar)
        progress.update(total=100, progress=0)
        progress.styles.opacity = 1

    def action_progressbar_stop(self) -> None:
        """Hide progress bar"""
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=0)
            progress.styles.opacity = 0
        except Exception:
            pass

    async def download_with_progress(self, url: str) -> None:
        """Async download wrapper with progress tracking and cancellation support"""

        def check_cancelled():
            """Callback for download module to check cancellation flag"""
            return self.download_cancelled

        program = None
        download_task = None

        try:
            # Initialize download handler
            program = Download(
                url=url,
                codec=self.selected_codec,
                kbps=self.selected_kbps,
            )
            program.set_progress_callback(self.update_progress)
            program.set_cancel_check(check_cancelled)

            loop = asyncio.get_event_loop()
            # Run blocking download in thread pool
            download_task = loop.run_in_executor(self.executor, program.download)

            # Monitor task with cancellation support
            while not download_task.done():
                if self.download_cancelled:
                    program.cancel()

                    # Graceful shutdown with timeout
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(download_task), timeout=2.0
                        )
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        download_task.cancel()
                        await asyncio.sleep(0.1)  # Allow cancellation to propagate

                    self.call_from_thread(
                        self._handle_download_complete, False, "Download cancelled"
                    )
                    return

                await asyncio.sleep(0.1)

            # Download completed normally
            if not self.download_cancelled:
                try:
                    result = (
                        download_task.result()
                    )  # Re-raise any exceptions from download
                    if result:
                        self.call_from_thread(self._handle_download_complete, True, "")
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
                        self._handle_download_complete, False, f"Error: {str(e)}"
                    )

        except DownloadCancelledError:
            self.call_from_thread(
                self._handle_download_complete, False, "Download cancelled"
            )
        except DownloadError as e:
            self.call_from_thread(self._handle_download_complete, False, str(e))
        except Exception as e:
            self.call_from_thread(
                self._handle_download_complete, False, f"Error: {str(e)}"
            )

    @on(Button.Pressed, "#accept_button")
    async def action_accept_url(self) -> None:
        """Validate URL and start download"""
        url_input = self.query_one("#url_input", Input)
        accept_button = self.query_one("#accept_button", Button)
        cancel_button = self.query_one("#cancel_button", Button)

        url = url_input.value.strip()

        # Input validation
        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            self.notify(
                "Please enter a valid URL (starting with http:// or https://)",
                severity="error",
            )
            return

        if not self.selected_kbps:
            self.notify("Please select a bitrate", severity="warning")
            return

        if not self.selected_codec:
            self.notify("Please select a codec", severity="warning")
            return

        try:
            # Update UI for download state
            accept_button.disabled = True
            cancel_button.disabled = False
            url_input.disabled = True

            self.action_progressbar_start()
            self.notify(
                f"Starting download with {self.selected_codec.upper()} @ {self.selected_kbps}kbps..."
            )

            self.download_cancelled = False

            # Launch download task
            self.current_download_task = asyncio.create_task(
                self.download_with_progress(url=url)
            )

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self._reset_ui_after_download()

    @on(Button.Pressed, "#cancel_button")
    async def action_cancel_download(self) -> None:
        """Cancel active download"""
        if self.current_download_task and not self.current_download_task.done():
            self.download_cancelled = True
            self.notify("Cancelling download...", severity="warning")

            # Wait for task to finish or timeout
            try:
                await asyncio.wait_for(self.current_download_task, timeout=3.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        else:
            # No active download, just reset UI
            self._reset_ui_after_download()
            self.query_one("#url_input", Input).value = ""
            self.action_progressbar_stop()

    def on_unmount(self) -> None:
        """Clean up resources when app closes"""
        if self.current_download_task and not self.current_download_task.done():
            self.download_cancelled = True
            self.current_download_task.cancel()

        self.executor.shutdown(wait=True, timeout=5.0)


if __name__ == "__main__":
    app = Rhythmer()
    app.run()
