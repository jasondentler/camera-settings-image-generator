import unittest

from src.formatters import (
    format_camera_model,
    format_date_time,
    format_gear_display_name,
    format_gps,
    format_shutter,
    split_lens_extender,
)


class FormatterTests(unittest.TestCase):
    def test_formats_sony_camera_model_display_name(self):
        self.assertEqual(format_camera_model("ILCE-7M5"), "Sony α7 V")
        self.assertEqual(format_camera_model(" ILCE-7M5 "), "Sony α7 V")
        self.assertEqual(format_camera_model("Canon EOS R50"), "Canon EOS R50")

    def test_formats_date_and_time(self):
        self.assertEqual(
            format_date_time("2026:04:03 10:05:53"),
            ("Fri, 03 Apr 2026", "10:05 AM"),
        )
        self.assertEqual(format_date_time("Unknown"), ("Unknown", ""))
        self.assertEqual(format_date_time("not a date"), ("not a date", ""))

    def test_formats_gps(self):
        gps_display, maps_url = format_gps("29.57362742 -94.39025578")

        self.assertEqual(gps_display, '29° 34\' 25.06" N, 94° 23\' 24.92" W')
        self.assertEqual(maps_url, "https://google.com/maps?q=29.57362742,-94.39025578")
        self.assertEqual(format_gps("Unknown"), ("Unknown", ""))

    def test_formats_shutter_speed(self):
        self.assertEqual(format_shutter("0.0005"), "1/2000")
        self.assertEqual(format_shutter("2"), "2.0")
        self.assertEqual(format_shutter("N/A"), "N/A")

    def test_splits_canon_lens_extender(self):
        lens, extender = split_lens_extender(
            "RF100-400mm F5.6-8 IS USM + EXTENDER RF1.4x"
        )

        self.assertEqual(lens, "RF100-400mm F5.6-8 IS USM")
        self.assertEqual(extender, "EXTENDER RF1.4x")

    def test_splits_sony_lens_teleconverter(self):
        lens, extender = split_lens_extender(
            "FE 200-600mm F5.6-6.3 G OSS + 1.4X Teleconverter"
        )

        self.assertEqual(lens, "FE 200-600mm F5.6-6.3 G OSS")
        self.assertEqual(extender, "1.4X Teleconverter")

    def test_leaves_lens_without_extender_unsplit(self):
        self.assertEqual(
            split_lens_extender("RF200-800mm F6.3-9 IS USM"),
            ("RF200-800mm F6.3-9 IS USM", ""),
        )

    def test_formats_gear_display_names(self):
        self.assertEqual(
            format_gear_display_name("RF100-400mm F5.6-8 IS USM"),
            "RF 100-400mm ƒ/5.6-8 IS USM",
        )
        self.assertEqual(
            format_gear_display_name("RF200-800mm F6.3-9 IS USM"),
            "RF 200-800mm ƒ/6.3-9 IS USM",
        )
        self.assertEqual(
            format_gear_display_name("FE 200-600mm F/5.6-6.3 G OSS"),
            "FE 200-600mm ƒ/5.6-6.3 G OSS",
        )
        self.assertEqual(
            format_gear_display_name("FE 200-600mm f/5.6-6.3 G OSS"),
            "FE 200-600mm ƒ/5.6-6.3 G OSS",
        )
        self.assertEqual(
            format_gear_display_name("EXTENDER RF1.4x"),
            "Extender RF 1.4x",
        )
        self.assertEqual(
            format_gear_display_name("1.4X Teleconverter"),
            "1.4x Teleconverter",
        )
        self.assertEqual(
            format_gear_display_name("super TELEPHOTO lens"),
            "Super Telephoto Lens",
        )


if __name__ == "__main__":
    unittest.main()
