import base64
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .hos_engine import split_remark

BLANK_LOG_PATH = Path(__file__).resolve().parent.parent / "blank-paper-log.png"
DAY_MINUTES = 24 * 60
GRID_X0 = 225
GRID_X1 = 1212
REMARKS_BOTTOM_Y = 537
REMARKS_TOP_Y = 494
ROW_Y = {
    "driving": 337,
    "off_duty": 250,
    "on_duty_nd": 381,
    "sleeper": 294,
}
STROKE_COMPLIANT = (10, 10, 10, 255)
STROKE_NONCOMPLIANT = (10, 10, 10, 120)
STROKE_WIDTH = 8
TOTAL_HOURS_X = 1260
TOTAL_HOURS_Y = {
    "driving": 332,
    "off_duty": 248,
    "on_duty_nd": 376,
    "sleeper": 290,
}


def _minute_to_x(minute: int) -> int:
    clamped = max(0, min(DAY_MINUTES, minute))
    return int(round(GRID_X0 + (GRID_X1 - GRID_X0) * (clamped / DAY_MINUTES)))


def _load_font(size: int, bold=False):
    candidates = (
        (
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        )
        if bold
        else (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_thick_line(
    draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, width=STROKE_WIDTH
):
    if len(points) < 2:
        return
    draw.line(points, fill=fill, width=width, joint="curve")
    radius = max(1, width // 2)
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def _draw_dash(
    draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, width=STROKE_WIDTH
):
    for index in range(len(points) - 1):
        x0, y0 = points[index]
        x1, y1 = points[index + 1]
        if x0 == x1:
            y_start, y_end = sorted((y0, y1))
            y = y_start
            draw_on = True
            while y < y_end:
                segment_end = min(y + 8, y_end)
                if draw_on:
                    _draw_thick_line(
                        draw, [(x0, y), (x0, segment_end)], fill=fill, width=width
                    )
                draw_on = not draw_on
                y = segment_end
            continue
        x_start, x_end = sorted((x0, x1))
        x = x_start
        draw_on = True
        while x < x_end:
            segment_end = min(x + 9, x_end)
            if draw_on:
                _draw_thick_line(
                    draw, [(x, y0), (segment_end, y0)], fill=fill, width=width
                )
            draw_on = not draw_on
            x = segment_end


def _draw_bracket(draw: ImageDraw.ImageDraw, x0: int, x1: int, fill=STROKE_COMPLIANT):
    left = min(x0, x1)
    right = max(x0, x1)
    if right - left < 12:
        right = left + 12
    bottom = REMARKS_BOTTOM_Y
    top = bottom - 10
    draw.rectangle((left, top, right, bottom), outline=fill, width=3)


def _format_hours(minutes: int) -> str:
    hours = minutes / 60.0
    if abs(hours - round(hours)) < 0.01:
        return f"{int(round(hours))}"
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def _draw_total_hours(draw: ImageDraw.ImageDraw, day_segments: list[dict]):
    font = _load_font(18, bold=True)
    totals = {status: 0 for status in ROW_Y}
    for segment in day_segments:
        status = segment["status"]
        if status in totals:
            totals[status] += max(0, segment["end_minutes"] - segment["start_minutes"])
    for status, minutes in totals.items():
        label = _format_hours(minutes)
        x = TOTAL_HOURS_X
        y = TOTAL_HOURS_Y[status]
        bbox = font.getbbox(label)
        tw = bbox[2] - bbox[0]
        draw.text((x + (50 - tw) / 2, y), label, fill=STROKE_COMPLIANT, font=font)


def _rotated_text(text: str, fill) -> Image.Image:
    font = _load_font(15, bold=True)
    padding = 2
    width = int(font.getlength(text)) + padding * 2
    height = 20
    canvas = Image.new("RGBA", (max(width, 8), height), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((padding, 1), text, fill=fill, font=font)
    return canvas.rotate(45, expand=True, resample=Image.Resampling.BICUBIC)


def _absolute_start(segment: dict) -> int:
    return segment["day_index"] * DAY_MINUTES + segment["start_minutes"]


def _absolute_end(segment: dict) -> int:
    end = segment["end_minutes"]
    if end >= DAY_MINUTES:
        return segment["day_index"] * DAY_MINUTES + DAY_MINUTES
    return segment["day_index"] * DAY_MINUTES + end


def _is_drive_interrupt(segment: dict, timeline: list[dict]) -> bool:
    if segment.get("status") == "driving":
        return False
    start = _absolute_start(segment)
    end = _absolute_end(segment)
    drove_before = any(
        item.get("status") == "driving" and _absolute_end(item) <= start
        for item in timeline
    )
    drove_after = any(
        item.get("status") == "driving" and _absolute_start(item) >= end
        for item in timeline
    )
    return drove_before and drove_after


def _should_draw_hour_bar(segment: dict, timeline: list[dict]) -> bool:
    if not (segment.get("remark") or "").strip():
        return False
    if not _is_drive_interrupt(segment, timeline):
        return False
    status = segment.get("status")
    label = (segment.get("label") or "").lower()
    remark = (segment.get("remark") or "").lower()
    if status == "sleeper":
        return False
    if "10-hour reset" in label or "10-hr reset" in remark:
        return False
    if status == "on_duty_nd":
        return True
    if status == "off_duty" and "break" in label:
        return True
    return False


def _draw_diagonal_remark(
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    place: str,
    activity: str,
    fill,
    depth_index: int,
):
    origin_y = REMARKS_BOTTOM_Y
    length = 105 + (depth_index % 3) * 38
    angle = math.radians(45)
    dir_x = -math.cos(angle)
    dir_y = math.sin(angle)
    x_end = int(x + length * dir_x)
    y_end = int(origin_y + length * dir_y)
    draw.line([(x, origin_y), (x_end, y_end)], fill=fill, width=4)

    mid_x = (x + x_end) / 2
    mid_y = (origin_y + y_end) / 2
    norm_x = -dir_y
    norm_y = dir_x
    offset = 14

    if place:
        place_img = _rotated_text(place, fill)
        px = int(mid_x + norm_x * offset - place_img.width / 2)
        py = int(mid_y + norm_y * offset - place_img.height / 2)
        overlay.alpha_composite(place_img, (px, py))
    if activity:
        activity_img = _rotated_text(activity, fill)
        ax = int(mid_x - norm_x * offset - activity_img.width / 2)
        ay = int(mid_y - norm_y * offset - activity_img.height / 2)
        overlay.alpha_composite(activity_img, (ax, ay))


def _draw_remarks(
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    day_segments: list[dict],
    timeline: list[dict],
):
    remark_index = 0
    for segment in sorted(day_segments, key=lambda item: item["start_minutes"]):
        remark = (segment.get("remark") or "").strip()
        if not remark:
            continue
        x0 = _minute_to_x(segment["start_minutes"])
        x1 = _minute_to_x(segment["end_minutes"])
        fill = (
            STROKE_COMPLIANT if segment.get("compliant", True) else STROKE_NONCOMPLIANT
        )
        if _should_draw_hour_bar(segment, timeline):
            _draw_bracket(draw, x0, x1, fill=fill)
        place, activity = split_remark(remark)
        _draw_diagonal_remark(
            overlay,
            draw,
            x0,
            place,
            activity,
            fill,
            remark_index,
        )
        remark_index += 1


def _draw_duty_graph(draw: ImageDraw.ImageDraw, day_segments: list[dict]):
    ordered = sorted(day_segments, key=lambda segment: segment["start_minutes"])
    previous_status = None
    previous_end_x = None
    for segment in ordered:
        status = segment["status"]
        y = ROW_Y[status]
        x0 = _minute_to_x(segment["start_minutes"])
        x1 = _minute_to_x(segment["end_minutes"])
        if x1 <= x0:
            continue
        fill = (
            STROKE_COMPLIANT if segment.get("compliant", True) else STROKE_NONCOMPLIANT
        )
        points: list[tuple[int, int]] = []
        if (
            previous_status is not None
            and previous_end_x is not None
            and previous_status != status
        ):
            points.append((previous_end_x, ROW_Y[previous_status]))
            points.append((previous_end_x, y))
        points.append((x0, y))
        points.append((x1, y))
        if segment.get("compliant", True):
            _draw_thick_line(draw, points, fill=fill)
        else:
            _draw_dash(draw, points, fill=fill)
        previous_status = status
        previous_end_x = x1


def render_day_log(day_segments: list[dict], timeline: list[dict] | None = None) -> str:
    image = Image.open(BLANK_LOG_PATH).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_duty_graph(draw, day_segments)
    _draw_total_hours(draw, day_segments)
    _draw_remarks(overlay, draw, day_segments, timeline or day_segments)
    composed = Image.alpha_composite(image, overlay)
    buffer = io.BytesIO()
    composed.convert("RGB").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_logs(timeline: list[dict]) -> list[dict]:
    by_day: dict[int, list[dict]] = {}
    for segment in timeline:
        by_day.setdefault(segment["day_index"], []).append(segment)
    logs = []
    for day_index in sorted(by_day):
        logs.append(
            {
                "date_label": f"Day {day_index + 1}",
                "day_index": day_index,
                "image_base64": render_day_log(by_day[day_index], timeline),
            }
        )
    return logs
