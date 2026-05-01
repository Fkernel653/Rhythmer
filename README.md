# Rhythmer — TUI Audio Downloader

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()
[![TUI](https://img.shields.io/badge/TUI-textual-purple.svg)](https://github.com/Textualize/textual)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

A modern terminal-based audio downloader with interactive UI, built with Python and Textual. Download high-quality audio from YouTube and SoundCloud with automatic metadata embedding and thumbnail support.

![Screenshot](screenshot.png)

## ✨ Features

- **Interactive TUI** — Dropdown selectors, progress bar, cancel support
- **Multiple Formats** — M4A, MP3, FLAC, Opus
- **Configurable Quality** — 64–320 kbps
- **Metadata Embedding** — Title, artist, album tags + cover art
- **Thread-safe** — Responsive UI during downloads

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ & FFmpeg

### Installation

**uv** (recommended)
```bash
git clone https://github.com/Fkernel653/Rhythmer.git && cd Rhythmer
uv sync
```

**pip**
```bash
git clone https://github.com/Fkernel653/Rhythmer.git && cd Rhythmer
pip install .
```

**Poetry**
```bash
git clone https://github.com/Fkernel653/Rhythmer.git && cd Rhythmer
poetry install
```

**PDM**
```bash
git clone https://github.com/Fkernel653/Rhythmer.git && cd Rhythmer
pdm install
```

### Usage
```bash
# Set download directory (first time only)
python add_path.py

# Launch TUI
python main.py
```

## ⌨️ Controls

| Key | Action |
|-----|--------|
| `Tab` | Navigate |
| `Enter` | Select |
| `Esc` | Close dropdown |
| `Ctrl+C` | Exit |

## 📁 Structure

```
Rhythmer/
├── main.py           # TUI entry point
├── add_path.py       # Path config
├── style.tcss        # Tokyo Night theme
├── config.json       # User settings
└── modules/
    ├── download.py   # yt-dlp wrapper
    └── add_metadata.py
```

## 🔧 Requirements

| Package | Purpose |
|---------|---------|
| `textual` | TUI framework |
| `yt-dlp` | Audio extraction |
| `mutagen` | Metadata tagging |
| FFmpeg | Audio conversion |

## 📄 License

MIT License — see [LICENSE](LICENSE).

## 👤 Author

**Fkernel653** — [GitHub](https://github.com/Fkernel653)

## 🙏 Acknowledgments

- [Textual](https://github.com/Textualize/textual) – TUI framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) – YouTube download library
- [mutagen](https://github.com/quodlibet/mutagen) – Audio metadata handling

## ⚠️ Disclaimer

**For educational purposes only.** Users are responsible for complying with platform Terms of Service and applicable copyright laws. Download only content you have permission to download.
