# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.processor import process_photo  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 src/main.py path/to/your/photo.jpg")
        return

    process_photo(sys.argv[1])


if __name__ == "__main__":
    main()
