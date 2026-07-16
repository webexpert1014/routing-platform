from dataclasses import asdict, dataclass, field

BREAK_AFTER_DRIVE_MIN = 8 * 60
BREAK_DURATION_MIN = 30
DAY_MINUTES = 24 * 60
DROPOFF_MIN = 60
FUEL_EVERY_MILES = 1000
FUEL_MIN = 30
MAX_DRIVE_MIN = 11 * 60
MAX_WINDOW_MIN = 14 * 60
PICKUP_MIN = 60
RESET_OFF_DUTY_MIN = 90
RESET_SLEEPER_MIN = 10 * 60 - RESET_OFF_DUTY_MIN
START_AT_MIN = 6 * 60
STATUS_DRIVING = "driving"
STATUS_OFF_DUTY = "off_duty"
STATUS_ON_DUTY_ND = "on_duty_nd"
STATUS_SLEEPER = "sleeper"


STATE_ABBREV = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


def short_place(location: str) -> str:
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if not parts:
        return ""
    city = parts[0]
    if len(parts) == 1:
        return city
    region = parts[1]
    if len(region) == 2 and region.isalpha():
        return f"{city}, {region.upper()}"
    abbrev = STATE_ABBREV.get(region.lower())
    if abbrev:
        return f"{city}, {abbrev}"
    return f"{city}, {region}"


def remark_text(place: str, activity: str) -> str:
    if place and activity:
        return f"{place}|{activity}"
    return activity or place


def split_remark(remark: str) -> tuple[str, str]:
    if "|" in remark:
        place, activity = remark.split("|", 1)
        return place.strip(), activity.strip()
    if " - " in remark:
        place, activity = remark.split(" - ", 1)
        return place.strip(), activity.strip()
    return "", remark.strip()


@dataclass
class DutySegment:
    compliant: bool
    day_index: int
    end_minutes: int
    label: str
    location: str
    remark: str
    show_bracket: bool
    start_minutes: int
    status: str


@dataclass
class MapMarker:
    cumulative_miles: float
    day_index: int
    label: str
    lat: float
    lng: float
    location: str
    type: str


@dataclass
class PlanResult:
    available_cycle_hours: float
    cycle_exceeded: bool
    cycle_exceeded_at_mile: float | None
    cycle_warning: str | None
    markers: list[MapMarker] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    timeline: list[DutySegment] = field(default_factory=list)


class HosPlanner:
    def __init__(self, available_cycle_hours: float):
        self.available_cycle_min = max(0.0, available_cycle_hours * 60.0)
        self.clock = START_AT_MIN
        self.cycle_exceeded = False
        self.cycle_exceeded_at_mile = None
        self.cycle_used_min = 0.0
        self.drive_in_window = 0
        self.drive_since_break = 0
        self.last_place = ""
        self.markers: list[MapMarker] = []
        self.miles_driven = 0.0
        self.next_fuel_at = float(FUEL_EVERY_MILES)
        self.segments: list[DutySegment] = []
        self.window_start = None

    def build(
        self,
        *,
        coordinates: list[list[float]],
        current: dict,
        dropoff: dict,
        legs: list[dict],
        pickup: dict,
    ) -> PlanResult:
        self.last_place = short_place(current["label"])
        self._pad_off_duty(0, START_AT_MIN)
        self._add_marker(
            "current",
            current["lat"],
            current["lng"],
            "Current location",
            0.0,
            location=current["label"],
        )
        to_pickup = legs[0]
        self._drive_leg(
            coordinates=coordinates,
            duration_min=to_pickup["duration_minutes"],
            label=f"Drive to pickup ({pickup['label']})",
            miles=to_pickup["distance_miles"],
            route_mile_offset=0.0,
            start_remark=remark_text(self.last_place, "Begin trip"),
        )
        self.last_place = short_place(pickup["label"])
        self._on_duty(
            PICKUP_MIN,
            "Pickup",
            pickup["label"],
            pickup["lat"],
            pickup["lng"],
            "pickup",
            remark=remark_text(self.last_place, "Pickup"),
            show_bracket=True,
        )
        to_dropoff = legs[1]
        self._drive_leg(
            coordinates=coordinates,
            duration_min=to_dropoff["duration_minutes"],
            label=f"Drive to dropoff ({dropoff['label']})",
            miles=to_dropoff["distance_miles"],
            route_mile_offset=to_pickup["distance_miles"],
        )
        self.last_place = short_place(dropoff["label"])
        self._on_duty(
            DROPOFF_MIN,
            "Dropoff",
            dropoff["label"],
            dropoff["lat"],
            dropoff["lng"],
            "dropoff",
            remark=remark_text(self.last_place, "Dropoff"),
            show_bracket=True,
        )
        self._fill_day_remainder()
        warning = None
        if self.cycle_exceeded:
            warning = (
                "Trip exceeds available 70-hour cycle hours. "
                "Remaining route and log lines after cycle exhaustion are shown dotted / low opacity."
            )
        drive_minutes = sum(
            segment.end_minutes - segment.start_minutes
            for segment in self.segments
            if segment.status == STATUS_DRIVING
        )
        total_miles = sum(leg["distance_miles"] for leg in legs)
        last_day = self.segments[-1].day_index if self.segments else 0
        return PlanResult(
            available_cycle_hours=self.available_cycle_min / 60.0,
            cycle_exceeded=self.cycle_exceeded,
            cycle_exceeded_at_mile=self.cycle_exceeded_at_mile,
            cycle_warning=warning,
            markers=self.markers,
            summary={
                "days_count": last_day + 1,
                "total_drive_hours": round(drive_minutes / 60.0, 2),
                "total_miles": round(total_miles, 1),
            },
            timeline=self.segments,
        )

    def _add_marker(self, marker_type, lat, lng, label, cumulative_miles, location=""):
        self.markers.append(
            MapMarker(
                cumulative_miles=round(cumulative_miles, 1),
                day_index=self.clock // DAY_MINUTES,
                label=label,
                lat=lat,
                lng=lng,
                location=location,
                type=marker_type,
            )
        )

    def _compliant_now(self) -> bool:
        return self.cycle_used_min < self.available_cycle_min

    def _note_cycle(self):
        if not self._compliant_now() and not self.cycle_exceeded:
            self.cycle_exceeded = True
            self.cycle_exceeded_at_mile = round(self.miles_driven, 1)

    def _append_chunk(
        self,
        status,
        absolute_start,
        absolute_end,
        label,
        location,
        compliant,
        remark="",
        show_bracket=False,
    ):
        if absolute_end <= absolute_start:
            return
        day_index = absolute_start // DAY_MINUTES
        start_minutes = absolute_start % DAY_MINUTES
        end_minutes = absolute_end % DAY_MINUTES
        if end_minutes == 0:
            end_minutes = DAY_MINUTES
        self.segments.append(
            DutySegment(
                compliant=compliant,
                day_index=day_index,
                end_minutes=end_minutes,
                label=label,
                location=location,
                remark=remark,
                show_bracket=show_bracket,
                start_minutes=start_minutes,
                status=status,
            )
        )

    def _add_time(
        self,
        status,
        duration_min,
        label,
        location,
        counts_toward_cycle=False,
        remark="",
        show_bracket=False,
    ):
        duration = int(round(duration_min))
        if duration <= 0:
            return
        compliant = self._compliant_now()
        self._note_cycle()
        activity_start = self.clock
        remaining = duration
        cursor = self.clock
        is_first = True
        while remaining > 0:
            day_end = (cursor // DAY_MINUTES + 1) * DAY_MINUTES
            chunk = min(remaining, day_end - cursor)
            self._append_chunk(
                status,
                cursor,
                cursor + chunk,
                label,
                location,
                compliant,
                remark=remark if is_first else "",
                show_bracket=show_bracket and is_first,
            )
            is_first = False
            cursor += chunk
            remaining -= chunk
        self.clock = cursor
        if counts_toward_cycle:
            self.cycle_used_min += duration
            self._note_cycle()
        if status in (STATUS_DRIVING, STATUS_ON_DUTY_ND) and self.window_start is None:
            self.window_start = activity_start
        if status == STATUS_DRIVING:
            self.drive_in_window += duration
            self.drive_since_break += duration

    def _pad_off_duty(self, start_min, end_min):
        if end_min <= start_min:
            return
        self.clock = start_min
        self._add_time(STATUS_OFF_DUTY, end_min - start_min, "Off duty", "")

    def _fill_day_remainder(self):
        day_end = (self.clock // DAY_MINUTES + 1) * DAY_MINUTES
        remaining = day_end - self.clock
        if remaining > 0:
            self._add_time(STATUS_OFF_DUTY, remaining, "Off duty", "")

    def _reset_10(self, lat, lng):
        place = self.last_place or "En route"
        self._add_marker(
            "reset_10",
            lat,
            lng,
            "10-hour reset",
            self.miles_driven,
            location=place,
        )
        self._add_time(
            STATUS_OFF_DUTY,
            RESET_OFF_DUTY_MIN,
            "10-hour reset (off duty)",
            place,
            remark=remark_text(place, "10-hr reset"),
            show_bracket=True,
        )
        self._add_time(
            STATUS_SLEEPER,
            RESET_SLEEPER_MIN,
            "10-hour reset (sleeper)",
            place,
        )
        self.window_start = None
        self.drive_in_window = 0
        self.drive_since_break = 0

    def _break_30(self, lat, lng):
        place = self.last_place or "En route"
        self._add_marker(
            "break_30",
            lat,
            lng,
            "30-minute break",
            self.miles_driven,
            location=place,
        )
        self._add_time(
            STATUS_OFF_DUTY,
            BREAK_DURATION_MIN,
            "30-minute break",
            place,
            remark=remark_text(place, "30-min break"),
            show_bracket=True,
        )
        self.drive_since_break = 0

    def _window_remaining(self) -> int:
        if self.window_start is None:
            return MAX_WINDOW_MIN
        return max(0, MAX_WINDOW_MIN - (self.clock - self.window_start))

    def _ensure_duty_window(self, needed_min, lat, lng):
        while self.window_start is not None and self._window_remaining() < needed_min:
            self._reset_10(lat, lng)

    def _on_duty(
        self,
        minutes,
        label,
        location,
        lat,
        lng,
        marker_type,
        remark="",
        show_bracket=False,
    ):
        self._ensure_duty_window(minutes, lat, lng)
        self._add_marker(
            marker_type, lat, lng, label, self.miles_driven, location=location
        )
        self._add_time(
            STATUS_ON_DUTY_ND,
            minutes,
            label,
            location,
            counts_toward_cycle=True,
            remark=remark,
            show_bracket=show_bracket,
        )

    def _drive_leg(
        self,
        *,
        coordinates,
        duration_min,
        label,
        miles,
        route_mile_offset,
        start_remark="",
    ):
        from .routing_client import point_along_line

        remaining_drive = max(0.0, float(duration_min))
        remaining_miles = max(0.0, float(miles))
        if remaining_drive <= 0 and remaining_miles <= 0:
            return
        if remaining_drive <= 0:
            remaining_drive = max(remaining_miles / 55.0 * 60.0, 1.0)
        leg_miles = max(miles, 0.0001)
        pending_start_remark = start_remark

        while remaining_drive > 0.5:
            progress_miles = leg_miles - remaining_miles
            lat, lng = point_along_line(
                coordinates, route_mile_offset + max(progress_miles, 0)
            )
            if self.window_start is None:
                self.window_start = self.clock
            window_left = self._window_remaining()
            drive_left_11 = MAX_DRIVE_MIN - self.drive_in_window
            drive_left_break = BREAK_AFTER_DRIVE_MIN - self.drive_since_break
            if window_left <= 0 or drive_left_11 <= 0:
                self._reset_10(lat, lng)
                continue
            if drive_left_break <= 0:
                self._break_30(lat, lng)
                continue
            chunk = min(remaining_drive, window_left, drive_left_11, drive_left_break)
            miles_per_min = remaining_miles / remaining_drive if remaining_drive else 0
            miles_in_chunk = miles_per_min * chunk
            if (
                self.miles_driven + miles_in_chunk >= self.next_fuel_at
                and remaining_miles > 0
            ):
                miles_to_fuel = self.next_fuel_at - self.miles_driven
                if miles_to_fuel > 0.05 and miles_per_min > 0:
                    portion_min = min(
                        miles_to_fuel / miles_per_min, chunk, remaining_drive
                    )
                    self._add_time(
                        STATUS_DRIVING, portion_min, label, "", counts_toward_cycle=True
                    )
                    driven = miles_per_min * portion_min
                    self.miles_driven += driven
                    remaining_drive -= portion_min
                    remaining_miles -= driven
                fuel_lat, fuel_lng = point_along_line(
                    coordinates,
                    route_mile_offset + (leg_miles - remaining_miles),
                )
                place = self.last_place or "En route"
                self._add_marker(
                    "fueling",
                    fuel_lat,
                    fuel_lng,
                    "Fueling stop",
                    self.miles_driven,
                    location=place,
                )
                self._add_time(
                    STATUS_ON_DUTY_ND,
                    FUEL_MIN,
                    "Fueling",
                    place,
                    counts_toward_cycle=True,
                    remark=remark_text(place, "Fueling"),
                    show_bracket=True,
                )
                self.next_fuel_at += FUEL_EVERY_MILES
                continue
            self._add_time(
                STATUS_DRIVING,
                chunk,
                label,
                "",
                counts_toward_cycle=True,
                remark=pending_start_remark,
            )
            pending_start_remark = ""
            self.miles_driven += miles_in_chunk
            remaining_drive -= chunk
            remaining_miles -= miles_in_chunk


def plan_result_to_dict(result: PlanResult) -> dict:
    return {
        "available_cycle_hours": result.available_cycle_hours,
        "cycle_exceeded": result.cycle_exceeded,
        "cycle_exceeded_at_mile": result.cycle_exceeded_at_mile,
        "cycle_warning": result.cycle_warning,
        "markers": [asdict(marker) for marker in result.markers],
        "summary": result.summary,
        "timeline": [asdict(segment) for segment in result.timeline],
    }
