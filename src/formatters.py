# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import re
from datetime import datetime
from fractions import Fraction


CAMERA_MODEL_DISPLAY_NAMES = {
    "ILCE-7M5": "Sony α7 V",
}

EXTENDER_PATTERNS = [
    re.compile(r"\s+\+\s+(EXTENDER\s+RF[0-9.]+x)\s*$", re.IGNORECASE),
    re.compile(r"\s+\+\s+([0-9.]+X\s+Teleconverter)\s*$", re.IGNORECASE),
]


def format_camera_model(camera):
    """Returns the user-facing camera model name."""
    if not isinstance(camera, str):
        return camera

    return CAMERA_MODEL_DISPLAY_NAMES.get(camera.strip(), camera)


def format_date_time(raw_date):
    """
    Converts '2026:04:03 10:05:53' into ('Fri, 03 Apr 2026', '10:05 AM').
    Returns original string and empty string if formatting fails.
    """
    if not raw_date or raw_date in ["N/A", "Unknown", "Unknown Date"]:
        return raw_date, ""

    try:
        dt = datetime.strptime(raw_date, "%Y:%m:%d %H:%M:%S")
        date_str = dt.strftime("%a, %d %b %Y")
        time_str = dt.strftime("%-I:%M %p")

        return date_str, time_str
    except (ValueError, TypeError):
        return raw_date, ""


def format_gps(gps_raw):
    """
    Converts '29.57362742 -94.39025578' to DMS format
    and generates a Google Maps link.
    """
    if not gps_raw or gps_raw == "No GPS Data":
        return gps_raw, ""

    try:
        parts = gps_raw.split()
        lat_float = float(parts[0])
        lon_float = float(parts[1])

        def to_dms(deg, pos, neg):
            direction = pos if deg >= 0 else neg
            deg = abs(deg)
            d = int(deg)
            m = int((deg - d) * 60)
            s = round((deg - d - m / 60) * 3600, 2)
            return f"{d}° {m}' {s}\" {direction}"

        dms_lat = to_dms(lat_float, "N", "S")
        dms_lon = to_dms(lon_float, "E", "W")

        dms_string = f"{dms_lat}, {dms_lon}"
        maps_link = f"https://google.com/maps?q={lat_float},{lon_float}"

        return dms_string, maps_link
    except Exception:
        return gps_raw, ""


def format_shutter(val):
    """Converts decimal shutter speeds like 0.0005 to '1/2000'."""
    try:
        f_val = float(val)
        if f_val >= 1:
            return f"{round(f_val, 1)}"
        frac = Fraction(f_val).limit_denominator(8000)
        return f"{frac.numerator}/{frac.denominator}"
    except (ValueError, TypeError):
        return str(val)


def split_lens_extender(lens):
    """Splits lens metadata into lens and extender rows when EXIF combines them."""
    if not isinstance(lens, str):
        return lens, ""

    for pattern in EXTENDER_PATTERNS:
        match = pattern.search(lens)
        if match:
            return lens[: match.start()].strip(), match.group(1).strip()

    return lens, ""


def format_gear_display_name(name):
    """Formats lens/extender names for the image overlay."""
    if not isinstance(name, str):
        return name

    name = re.sub(r"\bRF(?=\d)", "RF ", name)
    name = re.sub(
        r"\b[Ff]/?(?=\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)", "ƒ/", name
    )
    name = re.sub(r"\b(\d+(?:\.\d+)?)X(?=\s+Teleconverter\b)", r"\1x", name)

    def pascal_case_long_word(match):
        word = match.group(0)
        return word[0].upper() + word[1:].lower()

    return re.sub(r"\b[A-Za-z]{4,}\b", pascal_case_long_word, name)
