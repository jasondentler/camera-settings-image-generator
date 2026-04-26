# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os
import sys
from datetime import datetime
import exiftool
import tomllib  # Built-in for Python 3.11+
from fractions import Fraction
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ExifTags


DEFAULT_APP_NAME = "Camera Settings Image Generator"
DEFAULT_APP_VERSION = "0.1.0"


def get_project_metadata():
    """Reads app name and version from pyproject.toml."""
    # Looks one level up from src/main.py
    toml_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
            project = data.get("project", {})
            name = project.get("name", DEFAULT_APP_NAME)
            version = project.get("version", DEFAULT_APP_VERSION)
            return name, version
    except Exception:
        return DEFAULT_APP_NAME, DEFAULT_APP_VERSION


APP_NAME, APP_VERSION = get_project_metadata()
APP_STRING = f"{APP_NAME} v{APP_VERSION}"


def get_text_color(image):
    """Calculates image brightness to select a high-contrast font color."""
    small_img = image.resize((1, 1))
    r, g, b = small_img.getpixel((0, 0))[:3]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 127 else "white"


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
        # %-I removes the leading zero for 12-hour format
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
        # Split the string and convert to floats
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
        # Generate clean Google Maps URL
        maps_link = f"https://google.com/maps?q={lat_float},{lon_float}"

        return dms_string, maps_link
    except:
        return gps_raw, ""


def format_shutter(val):
    """Converts decimal shutter speeds like 0.0005 to '1/2000'."""
    try:
        f_val = float(val)
        if f_val >= 1:
            return f"{round(f_val, 1)}"
        # Convert to fraction and limit denominator to common camera settings
        frac = Fraction(f_val).limit_denominator(8000)
        return f"{frac.numerator}/{frac.denominator}"
    except (ValueError, TypeError):
        return str(val)


def get_optimized_font(draw, text, img_w, img_h, font_path, spacing_ratio):
    """
    Increases font size from a minimum until the text block exceeds 90%
    of either the image width or height, then backs off to the last safe size.
    """
    current_size = 20  # Starting point
    max_w = img_w * 0.9
    max_h = img_h * 0.9
    last_safe_font = ImageFont.load_default()
    last_safe_size = current_size

    # Loop upwards to find the maximum possible fit
    while current_size < 500:  # Safety cap
        font = ImageFont.truetype(font_path, size=current_size)
        spacing = int(current_size * spacing_ratio)

        # Measure the full bounding box
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # If it exceeds bounds, return the previous size
        if text_w > max_w or text_h > max_h:
            return last_safe_font, last_safe_size

        # Store this size as safe and increment
        last_safe_font = font
        last_safe_size = current_size
        current_size += 2

    return last_safe_font, last_safe_size


def process_photo(input_path):
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        return

    base_name, _ = os.path.splitext(input_path)

    try:
        # 1. Extract ALL metadata formats natively using ExifTool
        try:
            with exiftool.ExifToolHelper() as et:
                metadata = et.get_metadata(input_path)[0]
        except Exception as e:
            print(f"Failed to read metadata via ExifTool: {e}")
            return

        default_camera = "Unknown Camera"
        default_lens = "Unknown Lens"
        default_raw_shutter = "N/A"
        default_aperture = "Unknown"
        default_focal = "Unknown"
        default_iso = "Unknown"
        default_raw_date = "Unknown"
        default_raw_gps = "Unknown"
        default_alt_text = "No alt text"
        default_caption = "No caption"
        default_title = "No title"

        # Extract all your highly-specific requested fields safely
        camera = metadata.get("EXIF:Model", default_camera)
        lens = metadata.get("EXIF:LensId", metadata.get("EXIF:LensModel", default_lens))
        raw_shutter = metadata.get("EXIF:ExposureTime", default_raw_shutter)
        shutter = format_shutter(raw_shutter)
        aperture = metadata.get("EXIF:FNumber", default_aperture)
        focal = metadata.get("EXIF:FocalLength", default_focal)
        iso = metadata.get("EXIF:ISO", metadata.get("EXIF:BaseISO", default_iso))
        raw_date = metadata.get("EXIF:DateTimeOriginal", default_raw_date)
        raw_gps = metadata.get("Composite:GPSPosition", default_raw_gps)

        clean_date, clean_time = format_date_time(raw_date)
        gps_display, maps_url = format_gps(raw_gps)

        # Target standard XMP and IPTC fields missed by Pillow
        alt_text = metadata.get("XMP:AltTextAccessibility", default_alt_text)
        caption = metadata.get(
            "XMP:Caption-Abstract",
            metadata.get("EXIF:ImageDescription", default_caption),
        )
        title = metadata.get("XMP:Title", default_title)

        software_used = metadata.get("EXIF:Software", "")
        if APP_NAME in software_used:
            print(f"⏭️  Skipping: {input_path} (Already processed by {APP_NAME})")
            return

        # Build lines dynamically
        lines = []

        if camera and camera != default_camera:
            lines.append(f"📷 {camera}")

        if lens and lens != default_lens:
            lines.append(f"🔍 {lens}")

        settings = []

        if shutter and raw_shutter and raw_shutter != default_raw_shutter:
            settings.append(f"{shutter}s")

        if aperture and aperture != default_aperture:
            settings.append(f"ƒ/{aperture}")

        if iso and iso != default_iso:
            settings.append(f"ISO {iso}")

        if settings and settings != []:
            all_settings = " ".join(settings)
            lines.append(f"💡 {all_settings}")

        if focal and focal != default_focal:
            lines.append(f"📏 {focal}mm")

        if clean_date and raw_date and raw_date != default_raw_date:
            lines.append(f"📅 {clean_date}")

        if clean_time and raw_date and raw_date != default_raw_date:
            lines.append(f"🕐 {clean_time}")

        if gps_display and raw_gps and raw_gps != default_raw_gps:
            lines.append(f"📍 {gps_display}")

        # Join with newlines
        display_text = "\n".join(lines)

        img = Image.open(input_path)
        img_w, img_h = img.size
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=40))
        draw = ImageDraw.Draw(blurred_img)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "OpenSansEmoji.ttf")

        # 1. Dynamic Font Scaling
        line_spacing_ratio = 0.7

        font, final_size = get_optimized_font(
            draw, display_text, img_w, img_h, font_path, line_spacing_ratio
        )

        # 2. Centered Alignment Calculation
        # Get total bounding box of multiline text
        spacing = int(final_size * line_spacing_ratio)
        text_bbox = draw.multiline_textbbox(
            (0, 0), display_text, font=font, spacing=spacing
        )
        left, top, right, bottom = text_bbox
        text_w = right - left
        text_h = bottom - top

        # Offset the starting position by subtracting the 'top' padding
        x = (img_w - text_w) // 2 - left
        y = (img_h - text_h) // 2 - top

        font_color = get_text_color(blurred_img)
        draw.multiline_text(
            (x, y),
            display_text,
            fill=font_color,
            font=font,
            spacing=int(final_size * line_spacing_ratio),
            align="left",
        )

        output_image = f"{base_name}_blurred.jpg"
        blurred_img.save(output_image)

        # Sync original metadata and apply app branding
        with exiftool.ExifToolHelper() as et:
            et.execute(
                "-tagsFromFile",
                input_path,
                "-all:all",
                "--ThumbnailImage",  # EXCLUDE the original thumbnail
                f"-CreatorTool={APP_STRING}",
                f"-Software={APP_STRING}",
                "-overwrite_original",
                output_image,
            )

        # Save companion text file for social media
        output_txt = f"{base_name}.txt"
        with open(output_txt, "w") as f:
            f.write(f"Title: {title}\n")
            f.write(f"📸 Camera: {camera}\n")
            f.write(f"🔍 Lens: {lens}\n")
            f.write(f"⏱️ Shutter Speed: {shutter}s\n")
            f.write(f"  Aperture: ƒ/{aperture}\n")
            f.write(f"💡 ISO {iso}\n")
            f.write(f"📏 Focal Length: {focal}mm\n")
            f.write(f"📅 Date: {clean_date}\n")
            f.write(f"🕐 Time: {clean_time}\n")
            f.write(f"📍 Location: {gps_display}\n")
            if maps_url:
                f.write(f"🗺️ View on Map: {maps_url}\n")
            f.write("\n")
            f.write(f"Caption:\n{caption}\n")
            f.write("\n")
            f.write(f"Alt Text:\n{alt_text}\n")

        print(f"✅ Generated: {output_image}")
        print(f"✅ Generated: {output_txt}")

    except Exception as e:
        print(f"Error processing image: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 src/main.py path/to/your/photo.jpg")
    else:
        process_photo(sys.argv[1])
