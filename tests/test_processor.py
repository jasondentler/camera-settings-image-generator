import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.processor import process_photo


class FakeExifToolHelper:
    instances = []

    def __init__(self):
        self.execute_args = None
        FakeExifToolHelper.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def get_metadata(self, input_path):
        return [
            {
                "EXIF:Model": "ILCE-7M5",
                "EXIF:LensId": "FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter",
                "EXIF:ExposureTime": "0.0004",
                "EXIF:FNumber": "9",
                "EXIF:FocalLength": "840",
                "EXIF:ISO": "12800",
                "EXIF:DateTimeOriginal": "2026:07:27 15:42:00",
                "Composite:GPSPosition": "Unknown",
                "EXIF:Software": "",
            }
        ]

    def execute(self, *args):
        self.execute_args = args


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        FakeExifToolHelper.instances = []

    @patch("src.processor.exiftool.ExifToolHelper", FakeExifToolHelper)
    def test_process_photo_writes_outputs_and_preserves_raw_companion_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sony.jpg"
            Image.new("RGB", (1080, 1440), (180, 200, 210)).save(input_path)

            with contextlib.redirect_stdout(io.StringIO()):
                process_photo(str(input_path))

            output_image = Path(temp_dir) / "sony_blurred.jpg"
            output_text = Path(temp_dir) / "sony.txt"
            output_text_content = output_text.read_text()

            self.assertTrue(output_image.exists())
            self.assertTrue(output_text.exists())
            self.assertIn("📸 Camera: ILCE-7M5", output_text_content)
            self.assertIn(
                "🔍 Lens: FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter",
                output_text_content,
            )
            self.assertEqual(len(FakeExifToolHelper.instances), 2)
            self.assertIn(str(output_image), FakeExifToolHelper.instances[1].execute_args)


if __name__ == "__main__":
    unittest.main()
