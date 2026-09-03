# Egale Wipe

<div align="center">

![Egale Wipe](assets/EgaleWipe_header.png)
<h1>EgaleWipe</h1>
**A modern, lightweight Windows desktop utility engineered by EgaleCoders to safely and instantly clean folder contents while preserving root directory structures.**

[![Release](https://img.shields.io/github/v/release/EgaleCoder/EgaleWipe?style=flat-square&color=22c55e)](https://github.com/EgaleCoder/EgaleWipe/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?style=flat-square&logo=windows)](https://github.com/EgaleCoder/EgaleWipe/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python)](https://www.python.org/)

[**📥 Download Latest Executable (.exe)**](https://github.com/EgaleCoder/EgaleWipe/releases/latest) • [**Report Bug**](https://github.com/EgaleCoder/EgaleWipe/issues) • [**Request Feature**](https://github.com/EgaleCoder/EgaleWipe/issues)

</div>

---

## Key Highlights

- **Direct Download & Run**: Fully self-contained portable Windows `.exe`—no Python installation or dependencies required for end users.
- **Dynamic System Target Detection**: Automatically resolves active user temp (`%LOCALAPPDATA%\Temp`) and Windows temp (`%WINDIR%\Temp`) directories.
- **Interactive Checkmark Selection**: Custom vector checkmarks (✓) and folder row selection with quick add/remove folder capabilities.
- **Real-Time Progress Modal**: Non-blocking modal with current scanning paths, animated green progress bar, and instant cancellation support.
- **Graceful File-Lock Handling**: Detects read-only, locked, or system-in-use files and prompts the user to skip or safely abort.
- **High-DPI & Modern Styling**: Tailored Tkinter interface styled with custom colors, clean typography, embedded company branding, and native Windows taskbar icons.
- **Multi-threaded Safety**: All I/O operations execute on an isolated worker thread with synchronized UI dispatch to ensure zero freezing.

---

## Project Structure

```
EgaleWipe/
├── .github/
│   └── workflows/
│       └── release.yml        # CI/CD pipeline for automated Windows releases
├── assets/
│   ├── EgaleWipe.ico          # Application executable & taskbar icon
│   ├── EgaleWipe.png          # High-resolution original logo
│   ├── EgaleWipe_header.png   # Optimized UI header banner
│   ├── app_icon.png           # Window canvas icon
│   └── company_logo_22.png    # EgaleCoders branding badge
├── cleaner.py                 # Core file/folder discovery & deletion engine
├── worker.py                  # Threading abstraction & thread-safe UI dispatcher
├── main.py                    # Tkinter desktop GUI & lifecycle management
├── pyproject.toml             # Standard Python packaging specification
├── requirements.txt           # Build and runtime requirements
├── LICENSE                    # MIT Open Source License
└── README.md                  # Project documentation
```

---

## Quick Start (For Users)

1. Head over to the [**Releases**](https://github.com/EgaleCoder/EgaleWipe/releases) page.
2. Download `EgaleWipe.exe`.
3. Double-click to launch—no installation needed!

---

## Development & Local Execution

### Prerequisites
- Windows 10 or 11
- Python 3.8+ (with Tkinter included by default)

### Running from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/EgaleCoder/EgaleWipe.git
   cd EgaleWipe
   ```

2. Run directly with Python:
   ```bash
   python main.py
   ```

---

## Building Standalone Windows Executable

To compile a single-file executable with embedded assets and the application icon:

```powershell
# 1. Install PyInstaller
pip install pyinstaller

# 2. Build single-file GUI binary
pyinstaller --noconfirm --clean --onefile --windowed --icon=assets/EgaleWipe.ico --add-data "assets;assets" --name "EgaleWipe" main.py
```

The standalone executable will be generated inside the `dist/` directory:
```
dist/EgaleWipe.exe
```

---

## Automated Releases (CI/CD)

This repository includes a GitHub Actions workflow that automatically compiles and attaches the Windows executable to GitHub Releases whenever a semantic version tag (e.g. `v1.0.0`, `v1.0.1`) is pushed:

```bash
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

<div align="center">
  <sub>Engineered with ❤️ by <b>EgaleCoders</b> (2026).</sub>
</div>
