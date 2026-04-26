# Camera Settings Image Generator

A Python command-line application that takes a JPEG image, extracts its EXIF metadata, and generates a heavily blurred copy with the camera settings beautifully overlayed on top.

## 🚀 Features
* Extracts camera model, lens, and date directly from image metadata
* Dynamically calculates image brightness to select a high-contrast font color
* Applies heavy Gaussian blur for a modern, abstract background aesthetic
* Finds the best font size to fit most image sizes and aspect ratios

## Samples

<img src="./samples/20260106-IMG_3724.jpg" width="45%" />
<img src="./samples/20260106-IMG_3724_blurred.jpg"  width="45%" />

```
Title: Cottontail on a Rock
📸 Camera: Canon EOS R50
🔍 Lens: RF100-400mm F5.6-8 IS USM + EXTENDER RF1.4x
⏱️ Shutter Speed: 1/125s
  Aperture: ƒ/10
💡 ISO 10000
📏 Focal Length: 198mm
📅 Date: Tue, 06 Jan 2026
🕐 Time: 5:07 PM
📍 Location: 29° 46' 16.99" N, 95° 34' 11.49" W
🗺️ View on Map: https://google.com/maps?q=29.771387445,-95.56985714

Caption:
A peaceful afternoon in the Houston Audubon Nature Sanctuary. This Eastern Cottontail (Sylvilagus floridanus) pauses on a rock to rub its nose. The wooded area is blanketed in fallen leaves, creating a tranquil scene.

Alt Text:
A rabbit sits on a rock in a wooded area covered in fallen leaves. The rabbit has brown fur with a white underbelly and long ears.
```

<img src="./samples/20260403-IMG_0022.jpg"  width="45%" />
<img src="./samples/20260403-IMG_0022_blurred.jpg"  width="45%" />

```
Title: Cardinal on Railing
📸 Camera: Canon EOS R50
🔍 Lens: RF100-400mm F5.6-8 IS USM + EXTENDER RF1.4x
⏱️ Shutter Speed: 1/2000s
  Aperture: ƒ/13
💡 ISO 8000
📏 Focal Length: 560mm
📅 Date: Fri, 03 Apr 2026
🕐 Time: 10:05 AM
📍 Location: 29° 34' 25.06" N, 94° 23' 24.92" W
🗺️ View on Map: https://google.com/maps?q=29.57362742,-94.39025578

Caption:
A vibrant male Northern Cardinal perches on a wooden railing, showcasing its striking red plumage. The bird appears alert and watchful, surveying its surroundings. This beautiful cardinal is a common sight in the region.

Alt Text:
A male Northern Cardinal stands on a wooden railing against a blurred green background.
```

<img src="./samples/20260416-DA8A2396.jpg"  width="45%" />
<img src="./samples/20260416-DA8A2396_blurred.jpg"  width="45%" />

```
Title: No title
📸 Camera: Canon EOS R6 Mark III
🔍 Lens: RF200-800mm F6.3-9 IS USM
⏱️ Shutter Speed: 1/2000s
  Aperture: ƒ/9
💡 ISO 8000
📏 Focal Length: 800mm
📅 Date: Thu, 16 Apr 2026
🕐 Time: 5:03 PM
📍 Location: Unknown

Caption:
No caption

Alt Text:
No alt text
```

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

To run it on an entire folder:

```bash
for f in path/to/folder/*.[jJ][pP][gG]; do python3 src/main.py "$f"; done
```

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

The sample images and metadata (contents of the `samples` folder) are excluded from the Apache 2.0 license. They are licensed for the development and demonstration of the Camera Settings Image Generator software application. You may not print, reproduce, or distribute the sample images or metadata in any form without the Camera Settings Image Generator software application. Use for any other purpose requires prior written authorization from the copyright owner.