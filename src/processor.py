# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import glob
import math
import os
import shutil

import exiftool
from PIL import Image, ImageDraw, ImageFilter, ImageOps

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


TARGET_PORTRAIT_RATIO = 4 / 5
PANORAMA_RATIO = 2
MAX_POST_WIDTH = 3840
MAX_INPUT_PIXELS = 200_000_000

Image.MAX_IMAGE_PIXELS = MAX_INPUT_PIXELS


def classify_aspect_ratio(width, height):
    if width == height:
        return "square"
    if width > height:
        return "landscape"
    return "portrait"


def needs_post_image(width, height):
    category = classify_aspect_ratio(width, height)
    return category in ("square", "landscape") or width / height <= TARGET_PORTRAIT_RATIO


def is_exact_4_5_portrait(width, height):
    return width < height and width * 5 == height * 4


def make_4_5_portrait_image(image):
    image = image.convert("RGB")
    width, height = image.size
    if width > MAX_POST_WIDTH:
        target_height = round(height * MAX_POST_WIDTH / width)
        image = image.resize((MAX_POST_WIDTH, target_height), Image.Resampling.LANCZOS)
        width, height = image.size

    if width / height > TARGET_PORTRAIT_RATIO:
        canvas_size = (width, math.ceil(width / TARGET_PORTRAIT_RATIO))
    else:
        canvas_size = (math.ceil(height * TARGET_PORTRAIT_RATIO), height)

    background = ImageOps.fit(image, canvas_size, method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=40)).convert("RGB")

    output = background.copy()
    x = (canvas_size[0] - width) // 2
    y = (canvas_size[1] - height) // 2
    output.paste(image.convert("RGB"), (x, y))
    return output


def get_landscape_split_count(width, height):
    if width / height < PANORAMA_RATIO:
        return 2

    target_split_width = height * TARGET_PORTRAIT_RATIO
    return max(2, round(width / target_split_width))


def split_landscape_image(image):
    image = image.convert("RGB")
    width, height = image.size
    split_count = get_landscape_split_count(width, height)
    target_split_width = round(height * TARGET_PORTRAIT_RATIO)

    if width / split_count < target_split_width:
        virtual_width = split_count * target_split_width
        original_x = (virtual_width - width) / 2
        splits = []

        for index in range(split_count):
            slice_left = index * target_split_width
            slice_right = slice_left + target_split_width
            content_left = max(slice_left, original_x)
            content_right = min(slice_right, original_x + width)
            crop_left = round(content_left - original_x)
            crop_right = round(content_right - original_x)

            split_image = ImageOps.fit(
                image,
                (target_split_width, height),
                method=Image.Resampling.LANCZOS,
            )
            if crop_right > crop_left:
                crop = image.crop((crop_left, 0, crop_right, height))
                paste_x = round(content_left - slice_left)
                split_image.paste(crop, (paste_x, 0))
            splits.append(split_image)

        return splits

    splits = []
    for index in range(split_count):
        left = round(index * width / split_count)
        right = round((index + 1) * width / split_count)
        splits.append(image.crop((left, 0, right, height)))

    return [
        make_4_5_portrait_image(split_image)
        for split_image in splits
    ]


def copy_metadata(source_path, output_path):
    with exiftool.ExifToolHelper() as et:
        et.execute(
            "-tagsFromFile",
            source_path,
            "-all:all",
            "--ThumbnailImage",
            f"-CreatorTool={APP_STRING}",
            f"-Software={APP_STRING}",
            "-overwrite_original",
            output_path,
        )


def save_jpeg(image, output_path):
    image.convert("RGB").save(output_path)


def generate_metadata_image(
    source_image,
    output_path,
    metadata_source_path,
    overlay_rows,
    font_path,
    icon_dir,
):
    img_w, img_h = source_image.size
    blurred_img = source_image.filter(ImageFilter.GaussianBlur(radius=40)).convert(
        "RGBA"
    )
    draw = ImageDraw.Draw(blurred_img)

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

    save_jpeg(blurred_img, output_path)
    copy_metadata(metadata_source_path, output_path)


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

        with Image.open(input_path) as source_image:
            img = source_image.convert("RGB")
        category = classify_aspect_ratio(*img.size)
        metadata_image = img
        generated_images = []
        post_image_path = None
        split_image_paths = []

        if needs_post_image(*img.size):
            post_image_path = f"{base_name}_post.jpg"
            if is_exact_4_5_portrait(*img.size):
                shutil.copyfile(input_path, post_image_path)
                post_image = img
            else:
                post_image = make_4_5_portrait_image(img)
                save_jpeg(post_image, post_image_path)
                copy_metadata(input_path, post_image_path)
            generated_images.append(post_image_path)
            metadata_image = post_image

        if category == "landscape":
            for stale_split_path in glob.glob(f"{base_name}_split_*.jpg"):
                os.remove(stale_split_path)

            for index, split_image in enumerate(split_landscape_image(img), start=1):
                split_image_path = f"{base_name}_split_{index}.jpg"
                save_jpeg(split_image, split_image_path)
                copy_metadata(input_path, split_image_path)
                generated_images.append(split_image_path)
                split_image_paths.append(split_image_path)

        output_image = f"{base_name}_settings.jpg"
        generate_metadata_image(
            metadata_image,
            output_image,
            input_path,
            overlay_rows,
            font_path,
            icon_dir,
        )
        generated_images.append(output_image)

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
            f.write("\n")
            f.write(f"Original Image: {os.path.basename(input_path)}\n")
            if post_image_path:
                f.write(f"Hero: {os.path.basename(post_image_path)}\n")
            f.write(f"Settings: {os.path.basename(output_image)}\n")
            if split_image_paths:
                f.write("Splits:\n")
                for split_image_path in split_image_paths:
                    f.write(f"{os.path.basename(split_image_path)}\n")

        for generated_image in generated_images:
            print(f"✅ Generated: {generated_image}")
        print(f"✅ Generated: {output_txt}")

    except Exception as e:
        print(f"Error processing image: {e}")
