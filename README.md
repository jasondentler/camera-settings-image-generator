# Camera Settings Image Generator

A Python command-line application that takes a JPEG image, extracts its EXIF metadata, and generates a heavily blurred copy with the camera settings beautifully overlayed on top.

## 🚀 Features
* Extracts camera model, lens, and date directly from image metadata
* Dynamically calculates image brightness to select a high-contrast font color
* Applies heavy Gaussian blur for a modern, abstract background aesthetic

## 📦 Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/jasondentler/camera-settings-image-generator
   cd camera-settings-image-generator
   ```

2. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   ```

3. Activate the environment:
   * **macOS/Linux:** `source .venv/bin/activate`
   * **Windows:** `.venv\Scripts\activate`

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ Usage
Run the script from the project root and pass the path to your JPEG file:

```bash
python3 src/main.py path/to/your/photo.jpg
```

This will output a new file named `[original_filename]_blurred.jpg` in the same directory. It will also output `[original_filename].txt` containing important exif data for writing a social media post.

## ⚖️ License

Copyright 2026 Jason Dentler

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

See the `LICENSE` file for details.
