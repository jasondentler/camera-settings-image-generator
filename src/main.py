# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os
import sys
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from functools import lru_cache
from fractions import Fraction

import aggdraw
import exiftool
import tomllib  # Built-in for Python 3.11+
from PIL import (
    Image,
    ImageChops,
    ImageColor,
    ImageDraw,
    ImageFilter,
    ImageFont,
    ExifTags,
)


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


def split_lens_extender(lens):
    """Splits lens metadata into lens and extender rows when EXIF combines them."""
    if not isinstance(lens, str):
        return lens, ""

    for pattern in EXTENDER_PATTERNS:
        match = pattern.search(lens)
        if match:
            return lens[: match.start()].strip(), match.group(1).strip()

    return lens, ""


def parse_svg_number_list(value):
    return [
        float(part)
        for part in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", value)
    ]


def parse_svg_color(value):
    if not value or value == "none":
        return None
    if value == "currentColor":
        return (0, 0, 0)

    rgb_match = re.fullmatch(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", value)
    if rgb_match:
        return tuple(int(part) for part in rgb_match.groups())

    return ImageColor.getrgb(value)[:3]


def local_svg_name(element):
    return element.tag.rsplit("}", 1)[-1]


def svg_arc_points(x1, y1, rx, ry, rotation, large_arc, sweep, x2, y2):
    if rx == 0 or ry == 0:
        return [(x2, y2)]

    phi = math.radians(rotation)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy
    rx = abs(rx)
    ry = abs(ry)

    radius_check = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if radius_check > 1:
        scale = math.sqrt(radius_check)
        rx *= scale
        ry *= scale

    numerator = max(
        0,
        rx * rx * ry * ry
        - rx * rx * y1p * y1p
        - ry * ry * x1p * x1p,
    )
    denominator = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    sign = -1 if large_arc == sweep else 1
    coef = sign * math.sqrt(numerator / denominator) if denominator else 0
    cxp = coef * (rx * y1p / ry)
    cyp = coef * (-ry * x1p / rx)
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2

    def vector_angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        if not length:
            return 0
        angle = math.acos(max(-1, min(1, dot / length)))
        return -angle if ux * vy - uy * vx < 0 else angle

    start_angle = vector_angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta_angle = vector_angle(
        (x1p - cxp) / rx,
        (y1p - cyp) / ry,
        (-x1p - cxp) / rx,
        (-y1p - cyp) / ry,
    )
    if not sweep and delta_angle > 0:
        delta_angle -= 2 * math.pi
    elif sweep and delta_angle < 0:
        delta_angle += 2 * math.pi

    steps = max(8, int(abs(delta_angle) / (math.pi / 12)))
    points = []
    for step in range(1, steps + 1):
        theta = start_angle + delta_angle * step / steps
        x = cx + cos_phi * rx * math.cos(theta) - sin_phi * ry * math.sin(theta)
        y = cy + sin_phi * rx * math.cos(theta) + cos_phi * ry * math.sin(theta)
        points.append((x, y))
    return points


def svg_path_to_aggdraw(d, scale_x, scale_y):
    tokens = re.findall(
        r"[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?",
        d,
    )
    path = aggdraw.Path()
    index = 0
    command = None
    x = y = start_x = start_y = 0
    last_control = None

    def is_command(token):
        return re.fullmatch(r"[AaCcHhLlMmQqSsTtVvZz]", token) is not None

    def number():
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    def point(px, py):
        return px * scale_x, py * scale_y

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1

        if command in ("M", "m"):
            first = True
            while index < len(tokens) and not is_command(tokens[index]):
                nx, ny = number(), number()
                if command == "m":
                    nx += x
                    ny += y
                if first:
                    path.moveto(*point(nx, ny))
                    start_x, start_y = nx, ny
                    first = False
                else:
                    path.lineto(*point(nx, ny))
                x, y = nx, ny
            last_control = None
            continue

        if command in ("L", "l"):
            while index < len(tokens) and not is_command(tokens[index]):
                nx, ny = number(), number()
                if command == "l":
                    nx += x
                    ny += y
                path.lineto(*point(nx, ny))
                x, y = nx, ny
            last_control = None
            continue

        if command in ("H", "h"):
            while index < len(tokens) and not is_command(tokens[index]):
                nx = number() + (x if command == "h" else 0)
                path.lineto(*point(nx, y))
                x = nx
            last_control = None
            continue

        if command in ("V", "v"):
            while index < len(tokens) and not is_command(tokens[index]):
                ny = number() + (y if command == "v" else 0)
                path.lineto(*point(x, ny))
                y = ny
            last_control = None
            continue

        if command in ("C", "c"):
            while index < len(tokens) and not is_command(tokens[index]):
                x1, y1, x2, y2, nx, ny = [number() for _ in range(6)]
                if command == "c":
                    x1, y1, x2, y2, nx, ny = (
                        x1 + x,
                        y1 + y,
                        x2 + x,
                        y2 + y,
                        nx + x,
                        ny + y,
                    )
                path.curveto(*point(x1, y1), *point(x2, y2), *point(nx, ny))
                x, y = nx, ny
                last_control = (x2, y2)
            continue

        if command in ("S", "s"):
            while index < len(tokens) and not is_command(tokens[index]):
                if last_control:
                    x1, y1 = 2 * x - last_control[0], 2 * y - last_control[1]
                else:
                    x1, y1 = x, y
                x2, y2, nx, ny = [number() for _ in range(4)]
                if command == "s":
                    x2, y2, nx, ny = x2 + x, y2 + y, nx + x, ny + y
                path.curveto(*point(x1, y1), *point(x2, y2), *point(nx, ny))
                x, y = nx, ny
                last_control = (x2, y2)
            continue

        if command in ("Q", "q"):
            while index < len(tokens) and not is_command(tokens[index]):
                qx, qy, nx, ny = [number() for _ in range(4)]
                if command == "q":
                    qx, qy, nx, ny = qx + x, qy + y, nx + x, ny + y
                c1x, c1y = x + 2 * (qx - x) / 3, y + 2 * (qy - y) / 3
                c2x, c2y = nx + 2 * (qx - nx) / 3, ny + 2 * (qy - ny) / 3
                path.curveto(*point(c1x, c1y), *point(c2x, c2y), *point(nx, ny))
                x, y = nx, ny
                last_control = (qx, qy)
            continue

        if command in ("A", "a"):
            while index < len(tokens) and not is_command(tokens[index]):
                rx, ry, rotation, large_arc, sweep, nx, ny = [
                    number() for _ in range(7)
                ]
                if command == "a":
                    nx += x
                    ny += y
                for px, py in svg_arc_points(
                    x, y, rx, ry, rotation, large_arc, sweep, nx, ny
                ):
                    path.lineto(*point(px, py))
                x, y = nx, ny
            last_control = None
            continue

        if command in ("Z", "z"):
            path.close()
            x, y = start_x, start_y
            last_control = None
            continue

        raise ValueError(f"Unsupported SVG path command: {command}")

    return path


def render_svg_to_image(icon_path, size):
    root = ET.parse(icon_path).getroot()
    view_box = root.get("viewBox")
    if view_box:
        min_x, min_y, width, height = parse_svg_number_list(view_box)
    else:
        width = float(root.get("width", size))
        height = float(root.get("height", size))
        min_x = min_y = 0

    scale_x = size / width
    scale_y = size / height
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    context = aggdraw.Draw(image)

    def style_for(element, parent_style):
        style = parent_style.copy()
        for key in ("fill", "stroke", "stroke-width"):
            if element.get(key) is not None:
                style[key] = element.get(key)
        return style

    def draw_element(element, parent_style):
        style = style_for(element, parent_style)
        name = local_svg_name(element)

        if name == "path" and element.get("d"):
            path = svg_path_to_aggdraw(element.get("d"), scale_x, scale_y)
            fill = parse_svg_color(style.get("fill"))
            stroke = parse_svg_color(style.get("stroke"))
            stroke_width = float(style.get("stroke-width", 1)) * (
                (scale_x + scale_y) / 2
            )
            brush = aggdraw.Brush(fill) if fill else None
            pen = aggdraw.Pen(stroke, stroke_width) if stroke else None
            context.path(path, pen, brush)
        elif name == "circle":
            cx = (float(element.get("cx", 0)) - min_x) * scale_x
            cy = (float(element.get("cy", 0)) - min_y) * scale_y
            rx = float(element.get("r", 0)) * scale_x
            ry = float(element.get("r", 0)) * scale_y
            fill = parse_svg_color(style.get("fill"))
            stroke = parse_svg_color(style.get("stroke"))
            stroke_width = float(style.get("stroke-width", 1)) * (
                (scale_x + scale_y) / 2
            )
            brush = aggdraw.Brush(fill) if fill else None
            pen = aggdraw.Pen(stroke, stroke_width) if stroke else None
            context.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), pen, brush)

        for child in element:
            if local_svg_name(child) not in ("title", "defs", "clipPath"):
                draw_element(child, style)

    draw_element(root, {"fill": "black", "stroke": None, "stroke-width": "1"})
    context.flush()
    return image


@lru_cache(maxsize=128)
def render_svg_icon(icon_path, height, color):
    """Renders an SVG icon with visible artwork scaled to the requested height."""
    render_size = max(height * 4, 64)
    icon = render_svg_to_image(icon_path, render_size)

    alpha = icon.getchannel("A")
    luminance = icon.convert("L")
    shape_alpha = luminance.point(lambda px: 0 if px > 245 else 255 - px)
    shape_alpha = ImageChops.multiply(shape_alpha, alpha)

    rgb = ImageColor.getrgb(color)[:3]
    tinted = Image.new("RGBA", icon.size, (*rgb, 0))
    tinted.putalpha(shape_alpha)

    bbox = tinted.getbbox()
    if not bbox:
        return Image.new("RGBA", (height, height), (*rgb, 0))

    tinted = tinted.crop(bbox)
    width = max(1, round(tinted.width * (height / tinted.height)))
    return tinted.resize((width, height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=32)
def get_icon_aspect(icon_path):
    icon = render_svg_icon(icon_path, 256, "black")
    return icon.width / icon.height


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
    current_size = 20  # Starting point
    max_w = img_w * 0.9
    max_h = img_h * 0.9
    last_safe_font = ImageFont.load_default()
    last_safe_size = current_size
    last_safe_layout = {"width": 0, "height": 0, "metrics": [], "row_gap": 0}

    # Loop upwards to find the maximum possible fit
    while current_size < 500:  # Safety cap
        font = ImageFont.truetype(font_path, size=current_size)
        layout = measure_overlay_rows(draw, rows, font, current_size, icon_dir)

        # If it exceeds bounds, return the previous size
        if layout["width"] > max_w or layout["height"] > max_h:
            return last_safe_font, last_safe_size, last_safe_layout

        # Store this size as safe and increment
        last_safe_font = font
        last_safe_size = current_size
        last_safe_layout = layout
        current_size += 2

    return last_safe_font, last_safe_size, last_safe_layout


def draw_overlay_rows(image, draw, rows, layout, x, y, font, font_color, icon_dir):
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
        date_time = " ".join(part for part in [clean_time, clean_date] if part)
        if date_time:
            info_rows.append({"icon": "date-time.svg", "text": date_time})

    if gps_display and raw_gps and raw_gps != defaults["raw_gps"]:
        info_rows.append({"icon": "gps-coordinates.svg", "text": gps_display})

    if raw_camera and raw_camera != defaults["camera"]:
        info_rows.append({"icon": "camera-isometric.svg", "text": camera})

    if lens and lens != defaults["lens"]:
        lens_name, extender = split_lens_extender(lens)
        info_rows.append({"icon": "lens-isometric.svg", "text": lens_name})
        if extender:
            info_rows.append({"icon": "lens-isometric.svg", "text": extender})

    rows = [*settings_rows]
    if settings_rows and info_rows:
        rows.append({"divider": True})
    rows.extend(info_rows)
    return rows


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

        defaults = {
            "camera": default_camera,
            "lens": default_lens,
            "raw_shutter": default_raw_shutter,
            "aperture": default_aperture,
            "focal": default_focal,
            "iso": default_iso,
            "raw_date": default_raw_date,
            "raw_gps": default_raw_gps,
        }

        # Extract all your highly-specific requested fields safely
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

        img = Image.open(input_path)
        img_w, img_h = img.size
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=40))
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
