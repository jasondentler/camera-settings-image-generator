# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from src.formatters import format_gear_display_name, split_lens_extender
from src.svg_icons import get_icon_aspect, render_svg_icon


BACKDROP_MAX_ALPHA = 210
BACKDROP_ALPHA_MULTIPLIER = 0.95


def get_text_color(image):
    """Calculates image brightness to select a high-contrast font color."""
    small_img = image.resize((1, 1))
    r, g, b = small_img.getpixel((0, 0))[:3]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 127 else "white"


def measure_overlay_rows(draw, rows, font, font_size, icon_dir):
    icon_gap = max(8, int(font_size * 0.35))
    row_gap = max(10, int(font_size * 0.38))
    divider_margin = max(10, int(font_size * 0.45))
    divider_height = max(1, int(font_size * 0.06))
    ascent, descent = font.getmetrics()
    row_height = max(1, ascent + descent)
    text_metrics = []

    for row in rows:
        if row.get("divider"):
            continue

        text_bbox = draw.textbbox((0, 0), row["text"], font=font)
        text_metrics.append(
            {
                "row": row,
                "bbox": text_bbox,
                "text_width": text_bbox[2] - text_bbox[0],
                "visual_text_height": max(1, text_bbox[3] - text_bbox[1]),
            }
        )

    icon_height = min(row_height, max(1, font_size))
    icon_widths = {
        metric["row"]["icon"]: max(
            1,
            round(
                icon_height
                * get_icon_aspect(os.path.join(icon_dir, metric["row"]["icon"]))
            ),
        )
        for metric in text_metrics
    }
    icon_column_width = max(icon_widths.values(), default=0)
    text_by_id = {id(metric["row"]): metric for metric in text_metrics}
    metrics = []
    width = 0
    height = 0

    for row in rows:
        if metrics:
            height += row_gap

        if row.get("divider"):
            metric = {
                "type": "divider",
                "height": divider_margin * 2 + divider_height,
                "line_height": divider_height,
                "margin": divider_margin,
            }
        else:
            text_metric = text_by_id[id(row)]
            icon_w = icon_widths[row["icon"]]
            row_w = icon_column_width + icon_gap + text_metric["text_width"]
            width = max(width, row_w)
            metric = {
                "type": "row",
                "row": row,
                "bbox": text_metric["bbox"],
                "height": row_height,
                "visual_text_height": text_metric["visual_text_height"],
                "icon_height": icon_height,
                "icon_width": icon_w,
                "icon_column_width": icon_column_width,
                "icon_gap": icon_gap,
            }

        metrics.append(metric)
        height += metric["height"]

    return {"width": width, "height": height, "metrics": metrics, "row_gap": row_gap}


def get_optimized_overlay_font(draw, rows, img_w, img_h, font_path, icon_dir):
    """
    Increases font size from a minimum until the overlay exceeds 90%
    of either the image width or height, then backs off to the last safe size.
    """
    current_size = 20
    max_w = img_w * 0.9
    max_h = img_h * 0.9
    last_safe_font = ImageFont.load_default()
    last_safe_size = current_size
    last_safe_layout = {"width": 0, "height": 0, "metrics": [], "row_gap": 0}

    while current_size < 500:
        font = ImageFont.truetype(font_path, size=current_size)
        layout = measure_overlay_rows(draw, rows, font, current_size, icon_dir)

        if layout["width"] > max_w or layout["height"] > max_h:
            return last_safe_font, last_safe_size, last_safe_layout

        last_safe_font = font
        last_safe_size = current_size
        last_safe_layout = layout
        current_size += 2

    return last_safe_font, last_safe_size, last_safe_layout


def get_backdrop_color(font_color):
    if ImageColor.getrgb(font_color)[:3] == (0, 0, 0):
        return (255, 255, 255)

    return (0, 0, 0)


def get_backdrop_alpha(mask_alpha):
    return min(BACKDROP_MAX_ALPHA, int(mask_alpha * BACKDROP_ALPHA_MULTIPLIER))


def draw_overlay_backdrop(image, rows, layout, x, y, font, font_color, icon_dir):
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    current_y = y

    for i, metric in enumerate(layout["metrics"]):
        if i > 0:
            current_y += layout["row_gap"]

        if metric["type"] == "divider":
            line_y = current_y + metric["margin"]
            mask_draw.line(
                (x, line_y, x + layout["width"], line_y),
                fill=160,
                width=metric["line_height"],
            )
            current_y += metric["height"]
            continue

        row = metric["row"]
        icon_path = os.path.join(icon_dir, row["icon"])
        icon = render_svg_icon(icon_path, metric["icon_height"], "white")
        icon_x = x + (metric["icon_column_width"] - icon.width) // 2
        icon_y = current_y + (metric["height"] - icon.height) // 2
        mask.paste(icon.getchannel("A"), (icon_x, icon_y), icon.getchannel("A"))

        text_x = x + metric["icon_column_width"] + metric["icon_gap"]
        text_y = (
            current_y
            + (metric["height"] - metric["visual_text_height"]) // 2
            - metric["bbox"][1]
        )
        mask_draw.text((text_x, text_y), row["text"], fill=255, font=font)
        current_y += metric["height"]

    blur_radius = max(4, int(layout["row_gap"] * 0.45))
    blurred_mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    backdrop = Image.new("RGBA", image.size, (*get_backdrop_color(font_color), 0))
    backdrop.putalpha(blurred_mask.point(get_backdrop_alpha))
    image.alpha_composite(backdrop)


def draw_overlay_rows(image, draw, rows, layout, x, y, font, font_color, icon_dir):
    draw_overlay_backdrop(image, rows, layout, x, y, font, font_color, icon_dir)
    current_y = y

    for i, metric in enumerate(layout["metrics"]):
        if i > 0:
            current_y += layout["row_gap"]

        if metric["type"] == "divider":
            line_y = current_y + metric["margin"]
            draw.line(
                (x, line_y, x + layout["width"], line_y),
                fill=font_color,
                width=metric["line_height"],
            )
            current_y += metric["height"]
            continue

        row = metric["row"]
        icon_path = os.path.join(icon_dir, row["icon"])
        icon = render_svg_icon(icon_path, metric["icon_height"], font_color)
        icon_x = x + (metric["icon_column_width"] - icon.width) // 2
        icon_y = current_y + (metric["height"] - icon.height) // 2
        image.paste(icon, (icon_x, icon_y), icon)

        text_x = x + metric["icon_column_width"] + metric["icon_gap"]
        text_y = (
            current_y
            + (metric["height"] - metric["visual_text_height"]) // 2
            - metric["bbox"][1]
        )
        draw.text((text_x, text_y), row["text"], fill=font_color, font=font)
        current_y += metric["height"]


def build_overlay_rows(
    raw_camera,
    camera,
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
    defaults,
):
    settings_rows = []
    info_rows = []

    if aperture and aperture != defaults["aperture"]:
        settings_rows.append({"icon": "aperture.svg", "text": f"ƒ/{aperture}"})

    if shutter and raw_shutter and raw_shutter != defaults["raw_shutter"]:
        settings_rows.append({"icon": "shutter-speed.svg", "text": f"{shutter}s"})

    if iso and iso != defaults["iso"]:
        settings_rows.append({"icon": "iso.svg", "text": str(iso)})

    if focal and focal != defaults["focal"]:
        settings_rows.append({"icon": "focal-length.svg", "text": f"{focal}mm"})

    if raw_date and raw_date != defaults["raw_date"]:
        date_time = " ".join(part for part in [clean_date, clean_time] if part)
        if date_time:
            info_rows.append({"icon": "date-time.svg", "text": date_time})

    if gps_display and raw_gps and raw_gps != defaults["raw_gps"]:
        info_rows.append({"icon": "gps-coordinates.svg", "text": gps_display})

    if raw_camera and raw_camera != defaults["camera"]:
        info_rows.append({"icon": "camera-isometric.svg", "text": camera})

    if lens and lens != defaults["lens"]:
        lens_name, extender = split_lens_extender(lens)
        info_rows.append(
            {"icon": "lens-isometric.svg", "text": format_gear_display_name(lens_name)}
        )
        if extender:
            info_rows.append(
                {
                    "icon": "teleconverter.svg",
                    "text": format_gear_display_name(extender),
                }
            )

    rows = [*settings_rows]
    if settings_rows and info_rows:
        rows.append({"divider": True})
    rows.extend(info_rows)
    return rows
