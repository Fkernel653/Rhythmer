from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Input, ProgressBar, Select, Button, Footer

from modules.download import Download
import asyncio

# Available codec options for audio conversion
LINES_CODEC = """M4A
MP3
FLAC
Opus""".splitlines()

# Available bitrate options
LINES_KBPS = """64
128
256
320""".splitlines()

class Rhytmer(App):
    CSS = """
    #main_container {
        layout: vertical;
        align: center middle;
        padding: 1;
    }
    
    #url_input {
        layout: vertical;
        align: center top;
        width: 80;
        margin-top: 10;
        margin-bottom: 1;
    }

    .select_row {
        layout: horizontal;
        align: center top;
        width: 80;
        margin-top: 1;
        margin-bottom: 1;
    }

    Select {
        height: 3;
    }

    #codec_select {
        width: 40;
        margin-right: 1;
    }

    #kbps_select {
        width: 40;
    }

    .button_row {
        layout: horizontal;
        align: center top;
        width: 80;
        margin-top: 1;
        margin-bottom: 10;
    }

    Button {
        height: 3;
    }
    
    #accept_button {
        width: 20;
        margin-right: 3;
    }

    #accept_button:disabled {
        opacity: 0.5;
        border: none;
    }
    
    #cancel_button {
        width: 20;
    }

    #download_progress {
        width: 80;
        margin: 1 0;
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .notification {
        margin: 1;
        padding: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.theme = "tokyo-night"
        self.current_download = None  # Track active download task
        self.download_cancelled = False  # Flag for cancellation

        self.selected_codec = "m4a"  # Default codec
        self.selected_kbps = 256  # Default bitrate

    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        with Container(id="main_container"):
            yield Input(id="url_input", placeholder="Enter your URL", type="text")
            yield ProgressBar(id="download_progress", total=100, show_percentage=True)

            with Vertical(classes="select_row"):
                yield Select(((line, line) for line in LINES_CODEC), id="codec_select", prompt="Choose a codec")
                yield Select(((line, line) for line in LINES_KBPS), id="kbps_select", prompt="Select the number of kbps")

            with Horizontal(classes="button_row"):
                yield Button("Download", variant="success", id="accept_button")
                yield Button("Cancel", variant="error", id="cancel_button")
        yield Footer()

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        """Handle codec/bitrate selection changes"""
        match event.select.id:
            case "codec_select":
                self.selected_codec = str(event.value)
            case "kbps_select":
                self.selected_kbps = str(event.value)

    def update_progress(self, value: int) -> None:
        """Thread-safe progress update"""
        self.call_from_thread(self._update_progress_ui, value)

    def _update_progress_ui(self, value: int) -> None:
        """Update progress bar on UI thread"""
        try:
            progress = self.query_one("#download_progress", ProgressBar)
            progress.update(progress=value)
        except Exception:
            pass

    def action_progressbar_start(self) -> None:
        """Show and reset progress bar"""
        progress = self.query_one("#download_progress", ProgressBar)
        progress.update(total=100, progress=0)
        progress.styles.opacity = 1

    def action_progressbar_stop(self) -> None:
        """Hide progress bar"""
        progress = self.query_one("#download_progress", ProgressBar)
        progress.update(progress=0)
        progress.styles.opacity = 0

    async def download_with_progress(self, url: str) -> None:
        """Async download with progress tracking and cancellation support"""
        try:
            program = Download(
                url=url,
                codec=self.selected_codec,
                kbps=str(self.selected_kbps),
            )
            program.set_progress_callback(self.update_progress)
            
            # Run blocking download in thread pool
            task = asyncio.create_task(asyncio.to_thread(program.normal))
            
            # Monitor task for cancellation
            while not task.done():
                if self.download_cancelled:
                    task.cancel()
                    self.notify("Download cancelled", severity="warning")
                    break
                await asyncio.sleep(0.1)
                
            if not self.download_cancelled:
                self.notify("✓ Download completed!", severity="success")
                
        except asyncio.CancelledError:
            self.notify("Download cancelled", severity="warning")
        except Exception as e:
            error_msg = str(e)
            self.notify(f"✗ Error: {error_msg[:100]}", severity="error")
        finally:
            self.download_cancelled = False
            self.action_progressbar_stop()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button clicks"""
        match event.button.id:
            case "accept_button":
                asyncio.create_task(self.action_accept_url())
            case "cancel_button":
                if self.current_download:
                    self.download_cancelled = True  # Cancel active download
                else:
                    self.query_one("#url_input", Input).value = ""  # Clear input
                    self.action_progressbar_stop()

    async def action_accept_url(self) -> None:
        """Validate URL and start download"""
        url_input = self.query_one("#url_input", Input)
        accept_button = self.query_one("#accept_button", Button)

        url = url_input.value.strip()

        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            self.notify(
                "Please enter a valid URL (starting with http:// or https://)",
                severity="error",
            )
            return
        try:
            accept_button.disabled = True
            self.action_progressbar_start()
            await self.download_with_progress(url=url)
        finally:
            url_input.value = ""
            accept_button.disabled = False


if __name__ == "__main__":
    app = Rhytmer()
    app.run()