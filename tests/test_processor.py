import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.processor import (
    classify_aspect_ratio,
    get_landscape_split_count,
    make_4_5_portrait_image,
    needs_post_image,
    process_photo,
    split_landscape_image,
)


def image_size(path):
    with Image.open(path) as image:
        return image.size


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
                "EXIF:Copyright": "© 2026 Jason Dentler, All Rights Reserved",
                "EXIF:Software": "",
            }
        ]

    def execute(self, *args):
        self.execute_args = args


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        FakeExifToolHelper.instances = []

    def test_classifies_aspect_ratios(self):
        self.assertEqual(classify_aspect_ratio(1080, 1440), "portrait")
        self.assertEqual(classify_aspect_ratio(1200, 1200), "square")
        self.assertEqual(classify_aspect_ratio(1920, 1080), "landscape")

    def test_post_image_is_needed_for_square_landscape_and_4_5_portrait(self):
        self.assertTrue(needs_post_image(800, 1000))
        self.assertTrue(needs_post_image(900, 1600))
        self.assertTrue(needs_post_image(1200, 1200))
        self.assertTrue(needs_post_image(1600, 1000))

    def test_4_5_post_image_caps_extreme_landscape_width(self):
        image = Image.new("RGB", (4000, 1000), (180, 200, 210))

        post_image = make_4_5_portrait_image(image)

        self.assertEqual(post_image.size, (3840, 4800))

    def test_wide_panorama_split_creates_multiple_4_5_portraits(self):
        image = Image.new("RGB", (4000, 1000), (180, 200, 210))

        splits = split_landscape_image(image)

        self.assertEqual(get_landscape_split_count(1600, 1000), 2)
        self.assertEqual(get_landscape_split_count(4000, 1000), 5)
        self.assertEqual(get_landscape_split_count(26571, 4712), 7)
        self.assertEqual([split.size for split in splits], [(800, 1000)] * 5)

    def test_landscape_split_uses_outer_side_padding_only_when_needed(self):
        image = Image.new("RGB", (1500, 1000), (180, 200, 210))

        splits = split_landscape_image(image)

        self.assertEqual([split.size for split in splits], [(800, 1000)] * 2)

    @patch("src.processor.exiftool.ExifToolHelper", FakeExifToolHelper)
    def test_process_photo_copies_exact_4_5_portrait_post_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sony.jpg"
            Image.new("RGB", (800, 1000), (180, 200, 210)).save(input_path)
            input_content = input_path.read_bytes()

            with contextlib.redirect_stdout(io.StringIO()):
                process_photo(str(input_path))

            post_image = Path(temp_dir) / "sony_post.jpg"
            output_image = Path(temp_dir) / "sony_settings.jpg"
            output_text = Path(temp_dir) / "sony.txt"
            output_text_content = output_text.read_text()

            self.assertTrue(post_image.exists())
            self.assertTrue(output_image.exists())
            self.assertFalse((Path(temp_dir) / "sony_blurred.jpg").exists())
            self.assertEqual(post_image.read_bytes(), input_content)
            self.assertEqual(image_size(post_image), (800, 1000))
            self.assertEqual(image_size(output_image), (800, 1000))
            self.assertTrue(output_text.exists())
            self.assertIn("📸 Camera: ILCE-7M5", output_text_content)
            self.assertIn(
                "🔍 Lens: FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter",
                output_text_content,
            )
            self.assertNotIn("Copyright", output_text_content)
            self.assertTrue(
                any(
                    str(output_image) in instance.execute_args
                    for instance in FakeExifToolHelper.instances
                    if instance.execute_args
                )
            )

    @patch("src.processor.exiftool.ExifToolHelper", FakeExifToolHelper)
    def test_process_photo_pads_skinny_portrait_before_metadata_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "skinny.jpg"
            Image.new("RGB", (900, 1600), (180, 200, 210)).save(input_path)

            with contextlib.redirect_stdout(io.StringIO()):
                process_photo(str(input_path))

            post_image = Path(temp_dir) / "skinny_post.jpg"
            metadata_image = Path(temp_dir) / "skinny_settings.jpg"

            self.assertTrue(post_image.exists())
            self.assertTrue(metadata_image.exists())
            self.assertFalse((Path(temp_dir) / "skinny_blurred.jpg").exists())
            self.assertEqual(image_size(post_image), (1280, 1600))
            self.assertEqual(image_size(metadata_image), (1280, 1600))

    @patch("src.processor.exiftool.ExifToolHelper", FakeExifToolHelper)
    def test_process_photo_pads_square_image_before_metadata_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "square.jpg"
            Image.new("RGB", (800, 800), (180, 200, 210)).save(input_path)

            with contextlib.redirect_stdout(io.StringIO()):
                process_photo(str(input_path))

            post_image = Path(temp_dir) / "square_post.jpg"
            metadata_image = Path(temp_dir) / "square_settings.jpg"

            self.assertTrue(post_image.exists())
            self.assertTrue(metadata_image.exists())
            self.assertFalse((Path(temp_dir) / "square_blurred.jpg").exists())
            self.assertEqual(image_size(post_image), (800, 1000))
            self.assertEqual(image_size(metadata_image), (800, 1000))

    @patch("src.processor.exiftool.ExifToolHelper", FakeExifToolHelper)
    def test_process_photo_pads_and_splits_landscape_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "landscape.jpg"
            Image.new("RGB", (1600, 1000), (180, 200, 210)).save(input_path)

            with contextlib.redirect_stdout(io.StringIO()):
                process_photo(str(input_path))

            post_image = Path(temp_dir) / "landscape_post.jpg"
            metadata_image = Path(temp_dir) / "landscape_settings.jpg"
            split_1 = Path(temp_dir) / "landscape_split_1.jpg"
            split_2 = Path(temp_dir) / "landscape_split_2.jpg"

            self.assertTrue(post_image.exists())
            self.assertTrue(metadata_image.exists())
            self.assertTrue(split_1.exists())
            self.assertTrue(split_2.exists())
            self.assertFalse((Path(temp_dir) / "landscape_blurred.jpg").exists())
            self.assertEqual(image_size(post_image), (1600, 2000))
            self.assertEqual(image_size(metadata_image), (1600, 2000))
            self.assertEqual(image_size(split_1), (800, 1000))
            self.assertEqual(image_size(split_2), (800, 1000))


if __name__ == "__main__":
    unittest.main()
