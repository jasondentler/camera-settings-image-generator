import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.overlay import (
    build_overlay_rows,
    get_backdrop_alpha,
    get_backdrop_color,
    measure_overlay_rows,
)


ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "src" / "OpenSansEmoji.ttf"
ICON_DIR = ROOT / "icons"

DEFAULTS = {
    "camera": "Unknown Camera",
    "lens": "Unknown Lens",
    "raw_shutter": "N/A",
    "aperture": "Unknown",
    "focal": "Unknown",
    "iso": "Unknown",
    "raw_date": "Unknown",
    "raw_gps": "Unknown",
}


class OverlayTests(unittest.TestCase):
    def test_builds_overlay_rows_in_requested_order(self):
        rows = build_overlay_rows(
            "Canon EOS R50",
            "Canon EOS R50",
            "RF100-400mm F5.6-8 IS USM + EXTENDER RF1.4x",
            "0.0005",
            "1/2000",
            "13",
            "560",
            "8000",
            "2026:04:03 10:05:53",
            "Fri, 03 Apr 2026",
            "10:05 AM",
            "29.57362742 -94.39025578",
            '29° 34\' 25.06" N, 94° 23\' 24.92" W',
            DEFAULTS,
        )

        self.assertEqual(
            [row.get("icon", "divider") for row in rows],
            [
                "aperture.svg",
                "shutter-speed.svg",
                "iso.svg",
                "focal-length.svg",
                "divider",
                "date-time.svg",
                "gps-coordinates.svg",
                "camera-isometric.svg",
                "lens-isometric.svg",
                "teleconverter.svg",
            ],
        )
        self.assertEqual(rows[5]["text"], "Fri, 03 Apr 2026 10:05 AM")
        self.assertEqual(rows[8]["text"], "RF 100-400mm ƒ/5.6-8 IS USM")
        self.assertEqual(rows[9]["text"], "Extender RF 1.4x")

    def test_builds_sony_teleconverter_rows(self):
        rows = build_overlay_rows(
            "ILCE-7M5",
            "Sony α7 V",
            "FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter",
            "0.0004",
            "1/2500",
            "9",
            "840",
            "12800",
            "2026:07:27 15:42:00",
            "Mon, 27 Jul 2026",
            "3:42 PM",
            "Unknown",
            "Unknown",
            DEFAULTS,
        )

        self.assertEqual(rows[5]["text"], "Mon, 27 Jul 2026 3:42 PM")
        self.assertEqual(rows[6]["text"], "Sony α7 V")
        self.assertEqual(rows[8]["icon"], "teleconverter.svg")
        self.assertEqual(rows[7]["text"], "FE 200-600mm ƒ/5.6-6.3 G OSS")
        self.assertEqual(rows[8]["text"], "1.4x Teleconverter")

    def test_omits_default_values_and_divider_when_only_settings_exist(self):
        rows = build_overlay_rows(
            "Unknown Camera",
            "Unknown Camera",
            "Unknown Lens",
            "0.01",
            "1/100",
            "8",
            "Unknown",
            "Unknown",
            "Unknown",
            "Unknown",
            "",
            "Unknown",
            "Unknown",
            DEFAULTS,
        )

        self.assertEqual(
            rows,
            [
                {"icon": "aperture.svg", "text": "ƒ/8"},
                {"icon": "shutter-speed.svg", "text": "1/100s"},
            ],
        )

    def test_layout_uses_equal_row_heights_and_fixed_icon_column(self):
        rows = build_overlay_rows(
            "ILCE-7M5",
            "Sony α7 V",
            "FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter",
            "0.0004",
            "1/2500",
            "9",
            "840",
            "12800",
            "2026:07:27 15:42:00",
            "Mon, 27 Jul 2026",
            "3:42 PM",
            "Unknown",
            "Unknown",
            DEFAULTS,
        )
        image = Image.new("RGB", (1080, 1440), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(str(FONT_PATH), size=60)
        layout = measure_overlay_rows(draw, rows, font, 60, str(ICON_DIR))
        row_metrics = [metric for metric in layout["metrics"] if metric["type"] == "row"]

        self.assertEqual(len({metric["height"] for metric in row_metrics}), 1)
        self.assertEqual(len({metric["icon_height"] for metric in row_metrics}), 1)
        self.assertEqual(len({metric["icon_column_width"] for metric in row_metrics}), 1)
        self.assertTrue(all(metric["icon_width"] <= metric["icon_column_width"] for metric in row_metrics))

    def test_backdrop_color_flips_for_text_color(self):
        self.assertEqual(get_backdrop_color("black"), (255, 255, 255))
        self.assertEqual(get_backdrop_color("white"), (0, 0, 0))

    def test_backdrop_alpha_uses_effective_mask_opacity(self):
        self.assertEqual(get_backdrop_alpha(0), 0)
        self.assertEqual(get_backdrop_alpha(100), 95)
        self.assertEqual(get_backdrop_alpha(255), 210)


if __name__ == "__main__":
    unittest.main()
