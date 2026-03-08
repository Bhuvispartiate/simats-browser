# SIMATS Browser

**Version 4.0** — A secure exam browser built with PySide6 and Python.

## Features
- Loads SIMATS exam portal in a locked-down browser window
- Copy/Paste unlock: `Ctrl+Shift+C`
- Always on Top: `Ctrl+Shift+T`
- Always Active (visibility spoof): `Ctrl+Shift+A`
- History tracking (30-day retention)

## Download
Pre-built Windows executable is available in the [`dist/simats/`](dist/simats/) folder.

## Build from Source
```bash
pip install PySide6 PyInstaller Pillow
python -m PyInstaller simats.spec --clean
```

## Requirements
- Windows 10/11
- No Python installation required (EXE is self-contained)
