import base64
import io
import math
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .hos_engine import short_place, split_remark

BLANK_LOG_PATH = Path(__file__).resolve().parent.parent / "blank-paper-log.png"
DAY_MINUTES = 24 * 60
DATE_FIELDS = (
    (675, 821),
    (837, 996),
    (1012, 1157),
)
DATE_Y = 42
FROM_MAX_X = 950
FROM_X = 400
FROM_Y = 142
GRID_X0 = 255
GRID_X1 = 1811
MILES_BOXES = (
    (209, 545),
    (559, 868),
)
MILES_Y = 278
REMARKS_BOTTOM_Y = 1100
ROW_Y = {
    "driving": 906,
    "off_duty": 770,
    "on_duty_nd": 975,
    "sleeper": 837,
}
STROKE_COMPLIANT = (45, 212, 191, 255)
STROKE_NONCOMPLIANT = (45, 212, 191, 120)
STROKE_WIDTH = 11
TO_MAX_X = 1720
TO_X = 1120
TO_Y = 142
TOTAL_HOURS_X = 1869
TOTAL_HOURS_WIDTH = 98
TOTAL_HOURS_Y = {
    "driving": 901,
    "off_duty": 765,
    "on_duty_nd": 970,
    "sleeper": 832,
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
                segment_end = min(y + 10, y_end)
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
            segment_end = min(x + 11, x_end)
            if draw_on:
                _draw_thick_line(
                    draw, [(x, y0), (segment_end, y0)], fill=fill, width=width
                )
            draw_on = not draw_on
            x = segment_end


def _draw_bracket(draw: ImageDraw.ImageDraw, x0: int, x1: int, fill=STROKE_COMPLIANT):
    left = min(x0, x1)
    right = max(x0, x1)
    if right - left < 16:
        right = left + 16
    bottom = REMARKS_BOTTOM_Y
    top = bottom - 14
    draw.rectangle((left, top, right, bottom), outline=fill, width=4)


def _format_hours(minutes: int) -> str:
    hours = minutes / 60.0
    if abs(hours - round(hours)) < 0.01:
        return f"{int(round(hours))}"
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def _format_miles(miles: float) -> str:
    if abs(miles - round(miles)) < 0.05:
        return str(int(round(miles)))
    return f"{miles:.1f}"


def _fit_text(text: str, font, max_width: float) -> str:
    if font.getlength(text) <= max_width:
        return text
    ellipsis = "…"
    if font.getlength(ellipsis) > max_width:
        return ""
    clipped = text
    while clipped and font.getlength(clipped + ellipsis) > max_width:
        clipped = clipped[:-1]
    return clipped + ellipsis if clipped else ellipsis


def _segment_place(segment: dict) -> str:
    location = short_place(segment.get("location") or "")
    if location:
        return location
    place, _activity = split_remark(segment.get("remark") or "")
    return place


def _day_miles(day_segments: list[dict], trip_meta: dict) -> float:
    drive_minutes = sum(
        max(0, segment["end_minutes"] - segment["start_minutes"])
        for segment in day_segments
        if segment.get("status") == "driving"
    )
    total_drive_hours = float(trip_meta.get("total_drive_hours") or 0)
    total_miles = float(trip_meta.get("total_miles") or 0)
    total_drive_minutes = total_drive_hours * 60.0
    if total_drive_minutes <= 0 or total_miles <= 0:
        return 0.0
    return round(drive_minutes / total_drive_minutes * total_miles, 1)


def _day_from_to(
    day_index: int, day_segments: list[dict], timeline: list[dict], trip_meta: dict
) -> tuple[str, str]:
    current = short_place(trip_meta.get("current_location") or "")
    dropoff = short_place(trip_meta.get("dropoff_location") or "")
    places = []
    for segment in sorted(day_segments, key=lambda item: item["start_minutes"]):
        place = _segment_place(segment)
        if place and (not places or places[-1] != place):
            places.append(place)
    from_place = places[0] if places else current
    to_place = places[-1] if places else dropoff
    if day_index == 0 and current:
        from_place = current
    last_day = max((segment["day_index"] for segment in timeline), default=day_index)
    if day_index == last_day and dropoff:
        to_place = dropoff
    return from_place, to_place


def _draw_header(
    draw: ImageDraw.ImageDraw,
    day_index: int,
    day_segments: list[dict],
    timeline: list[dict],
    trip_meta: dict,
):
    date_font = _load_font(36, bold=True)
    miles_font = _load_font(42, bold=True)
    place_font = _load_font(28, bold=True)
    log_date = date.today() + timedelta(days=day_index)
    for value, (x0, x1) in zip(
        (f"{log_date.month:02d}", f"{log_date.day:02d}", f"{log_date.year % 100:02d}"),
        DATE_FIELDS,
        strict=True,
    ):
        text_width = date_font.getlength(value)
        draw.text(
            (x0 + (x1 - x0 - text_width) / 2, DATE_Y),
            value,
            fill=STROKE_COMPLIANT,
            font=date_font,
        )
    from_place, to_place = _day_from_to(day_index, day_segments, timeline, trip_meta)
    if from_place:
        draw.text(
            (FROM_X, FROM_Y),
            _fit_text(from_place, place_font, FROM_MAX_X - FROM_X),
            fill=STROKE_COMPLIANT,
            font=place_font,
        )
    if to_place:
        draw.text(
            (TO_X, TO_Y),
            _fit_text(to_place, place_font, TO_MAX_X - TO_X),
            fill=STROKE_COMPLIANT,
            font=place_font,
        )
    miles_label = _format_miles(_day_miles(day_segments, trip_meta))
    for x0, x1 in MILES_BOXES:
        text_width = miles_font.getlength(miles_label)
        draw.text(
            (x0 + (x1 - x0 - text_width) / 2, MILES_Y),
            miles_label,
            fill=STROKE_COMPLIANT,
            font=miles_font,
        )


def _draw_total_hours(draw: ImageDraw.ImageDraw, day_segments: list[dict]):
    font = _load_font(26, bold=True)
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
        draw.text(
            (x + (TOTAL_HOURS_WIDTH - tw) / 2, y),
            label,
            fill=STROKE_COMPLIANT,
            font=font,
        )


def _rotated_text(text: str, fill) -> Image.Image:
    font = _load_font(22, bold=True)
    padding = 2
    width = int(font.getlength(text)) + padding * 2
    height = 28
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
    length = 160 + (depth_index % 3) * 55
    angle = math.radians(45)
    dir_x = -math.cos(angle)
    dir_y = math.sin(angle)
    x_end = int(x + length * dir_x)
    y_end = int(origin_y + length * dir_y)
    draw.line([(x, origin_y), (x_end, y_end)], fill=fill, width=5)

    mid_x = (x + x_end) / 2
    mid_y = (origin_y + y_end) / 2
    norm_x = -dir_y
    norm_y = dir_x
    offset = 18

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


def render_day_log(
    day_segments: list[dict],
    timeline: list[dict] | None = None,
    trip_meta: dict | None = None,
    day_index: int = 0,
) -> str:
    image = Image.open(BLANK_LOG_PATH).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    full_timeline = timeline or day_segments
    meta = trip_meta or {}
    _draw_header(draw, day_index, day_segments, full_timeline, meta)
    _draw_duty_graph(draw, day_segments)
    _draw_total_hours(draw, day_segments)
    _draw_remarks(overlay, draw, day_segments, full_timeline)
    composed = Image.alpha_composite(image, overlay)
    buffer = io.BytesIO()
    composed.convert("RGB").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_logs(timeline: list[dict], trip_meta: dict | None = None) -> list[dict]:
    by_day: dict[int, list[dict]] = {}
    for segment in timeline:
        by_day.setdefault(segment["day_index"], []).append(segment)
    logs = []
    meta = trip_meta or {}
    for day_index in sorted(by_day):
        log_date = date.today() + timedelta(days=day_index)
        logs.append(
            {
                "date_label": log_date.strftime("%b %d, %Y"),
                "day_index": day_index,
                "image_base64": render_day_log(
                    by_day[day_index], timeline, meta, day_index
                ),
            }
        )
    return logs
