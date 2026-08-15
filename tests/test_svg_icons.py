import unittest
from pathlib import Path

from src.svg_icons import render_svg_icon


ICON_DIR = Path(__file__).resolve().parents[1] / "icons"


class SvgIconTests(unittest.TestCase):
    def test_requested_overlay_icons_render_nonblank_at_exact_height(self):
        for icon_name in [
            "aperture.svg",
            "shutter-speed.svg",
            "iso.svg",
            "focal-length.svg",
            "copyright.svg",
            "date-time.svg",
            "gps-coordinates.svg",
            "camera-isometric.svg",
            "lens-isometric.svg",
            "teleconverter.svg",
        ]:
            with self.subTest(icon_name=icon_name):
                icon = render_svg_icon(str(ICON_DIR / icon_name), 48, "white")

                self.assertEqual(icon.height, 48)
                self.assertGreater(icon.width, 0)
                self.assertIsNotNone(icon.getbbox())

    def test_gear_icons_have_comparable_rendered_weight(self):
        for icon_name in [
            "camera-isometric.svg",
            "lens-isometric.svg",
            "teleconverter.svg",
        ]:
            with self.subTest(icon_name=icon_name):
                icon = render_svg_icon(str(ICON_DIR / icon_name), 48, "white")
                alpha_histogram = icon.getchannel("A").histogram()
                pixel_count = icon.width * icon.height
                mean_alpha = sum(
                    alpha * count for alpha, count in enumerate(alpha_histogram)
                ) / pixel_count
                strong_pixels = sum(alpha_histogram[200:])

                self.assertGreaterEqual(mean_alpha, 40)
                self.assertLessEqual(mean_alpha, 65)
                self.assertGreater(strong_pixels, 100)


if __name__ == "__main__":
    unittest.main()
