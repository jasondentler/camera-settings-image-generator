# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os

import exiftool
from PIL import Image, ImageDraw, ImageFilter

from src.app_metadata import APP_NAME, APP_STRING
from src.formatters import (
    format_camera_model,
    format_date_time,
    format_gps,
    format_shutter,
)
from src.overlay import (
    build_overlay_rows,
    draw_overlay_rows,
    get_optimized_overlay_font,
    get_text_color,
)


def process_photo(input_path):
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        return

    base_name, _ = os.path.splitext(input_path)

    try:
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
        default_copyright = "Unknown Copyright"
        default_alt_text = "No alt text"
        default_caption = "No caption"
        default_title = "No title"

        defaults = {
            "camera": default_camera,
            "lens": default_lens,
            "raw_shutter": default_raw_shutter,
            "aperture": default_aperture,
            "focal": default_focal,
            "iso": default_iso,
            "raw_date": default_raw_date,
            "raw_gps": default_raw_gps,
            "copyright": default_copyright,
        }

        camera = metadata.get("EXIF:Model", default_camera)
        display_camera = format_camera_model(camera)
        lens = metadata.get("EXIF:LensId", metadata.get("EXIF:LensModel", default_lens))
        raw_shutter = metadata.get("EXIF:ExposureTime", default_raw_shutter)
        shutter = format_shutter(raw_shutter)
        aperture = metadata.get("EXIF:FNumber", default_aperture)
        focal = metadata.get("EXIF:FocalLength", default_focal)
        iso = metadata.get("EXIF:ISO", metadata.get("EXIF:BaseISO", default_iso))
        raw_date = metadata.get("EXIF:DateTimeOriginal", default_raw_date)
        raw_gps = metadata.get("Composite:GPSPosition", default_raw_gps)
        copyright_notice = metadata.get(
            "EXIF:Copyright",
            metadata.get(
                "XMP:Rights",
                metadata.get("IPTC:CopyrightNotice", default_copyright),
            ),
        )

        clean_date, clean_time = format_date_time(raw_date)
        gps_display, maps_url = format_gps(raw_gps)

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

        img = Image.open(input_path)
        img_w, img_h = img.size
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=40)).convert("RGBA")
        draw = ImageDraw.Draw(blurred_img)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "OpenSansEmoji.ttf")
        icon_dir = os.path.join(script_dir, "..", "icons")

        overlay_rows = build_overlay_rows(
            camera,
            display_camera,
            lens,
            raw_shutter,
            shutter,
            aperture,
            focal,
            iso,
            raw_date,
            clean_date,
            clean_time,
            raw_gps,
            gps_display,
            copyright_notice,
            defaults,
        )

        font_color = get_text_color(blurred_img)
        if overlay_rows:
            font, _final_size, layout = get_optimized_overlay_font(
                draw, overlay_rows, img_w, img_h, font_path, icon_dir
            )
            x = (img_w - layout["width"]) // 2
            y = (img_h - layout["height"]) // 2
            draw_overlay_rows(
                blurred_img,
                draw,
                overlay_rows,
                layout,
                x,
                y,
                font,
                font_color,
                icon_dir,
            )

        output_image = f"{base_name}_blurred.jpg"
        blurred_img.convert("RGB").save(output_image)

        with exiftool.ExifToolHelper() as et:
            et.execute(
                "-tagsFromFile",
                input_path,
                "-all:all",
                "--ThumbnailImage",
                f"-CreatorTool={APP_STRING}",
                f"-Software={APP_STRING}",
                "-overwrite_original",
                output_image,
            )

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
