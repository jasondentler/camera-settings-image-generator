# Contributing

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

You also need ExifTool available on your PATH.

## Checks

Run the source compile check before committing:

```bash
make check
```

Regenerate sample outputs after changing overlay, metadata, formatting, or rendering behavior:

```bash
make samples
```

## Project Layout

- `src/main.py`: CLI entry point
- `src/processor.py`: end-to-end photo processing
- `src/overlay.py`: overlay rows, layout, and drawing
- `src/svg_icons.py`: SVG icon rendering
- `src/formatters.py`: metadata formatting helpers
- `src/app_metadata.py`: app name and version metadata

## Sample Assets

Sample images and generated sample metadata are excluded from the Apache 2.0 license. See the license note in `README.md` before adding, reusing, or distributing sample files.
