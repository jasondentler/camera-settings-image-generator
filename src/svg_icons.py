# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import math
import re
import xml.etree.ElementTree as ET
from functools import lru_cache

import aggdraw
from PIL import Image, ImageChops, ImageColor


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
