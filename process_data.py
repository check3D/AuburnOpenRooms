import argparse
import csv
from datetime import datetime, timedelta
import json
import re
from collections import defaultdict
from pathlib import Path

# This script takes the scraped scheduling CSV and:
# 1) drops rows that do not describe a physical room location
# 2) writes a cleaned CSV
# 3) produces a building -> [rooms...] mapping
#
# Some rows are "TBA" / online / off-campus / special sites. Those are not
# useful for finding open rooms, so they are excluded from the building map.


def _is_missing(value: str | None) -> bool:
    # Treat blank strings and "TBA" as missing.
    if value is None:
        return True
    v = value.strip()
    return (not v) or (v.upper() == "TBA")


# The upstream page sometimes returns a combined "Building Room" string. The
# scraper tries to split it, but certain rows end up with the room portion kept
# in the Building column (leaving Room blank). We repair a few common patterns.
_ROOM_TWO_TOKEN_RE = re.compile(r"^(.*\S)\s+(\d+)\s+([A-Za-z]+)$")
_ROOM_ONE_TOKEN_DIGIT_RE = re.compile(r"^(.*\S)\s+(\S*\d\S*)$")
_ROOM_CODE_RE = re.compile(r"^(.*\S)\s+([A-Z][A-Z0-9_-]{1,15})$")


def normalize_location(building: str | None, room: str | None) -> tuple[str, str]:
    """Return (Building, Room) with a best-effort split.

    The scraper writes some non-numeric room codes into the Building column
    (e.g. "Rane Center LAUREL") leaving Room blank.
    """

    b = "" if building is None else building.strip()
    r = "" if room is None else room.strip()

    if r and r.upper() != "TBA":
        return b, r

    if not b or b.upper() == "TBA":
        return "", ""

    m = _ROOM_TWO_TOKEN_RE.match(b)
    if m:
        return m.group(1).strip(), f"{m.group(2).strip()} {m.group(3).strip()}"

    m = _ROOM_ONE_TOKEN_DIGIT_RE.match(b)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    m = _ROOM_CODE_RE.match(b)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return b, ""


def _is_standard_room(room: str | None) -> bool:
    """Heuristic for a physical room number.

    For this dataset, real rooms almost always start with a digit (e.g. "113A",
    "0407", "177 B"). Anything else ("ONLINE", "SITE", "LAUREL", etc.) is
    treated as non-standard.
    """

    if room is None:
        return False
    r = room.strip()
    return bool(r) and r[0].isdigit()


_ROOM_SPLIT_RE = re.compile(r"^(\d+)(.*)$")
DAY_ORDER = ["M", "T", "W", "R", "F", "S", "U"]


def room_sort_key(room: str):
    # Sort rooms by their numeric prefix first ("0407" before "113A"), then by
    # suffix ("113A" after "113"). If the room isn't numeric, sort it last.
    r = room.strip()
    m = _ROOM_SPLIT_RE.match(r)
    if not m:
        return (1, r.upper())
    return (0, int(m.group(1)), m.group(2).upper())


def parse_time(value: str) -> datetime:
    """Convert strings like '2:00 pm' into a datetime for comparison/merging."""

    return datetime.strptime(value.strip().lower(), "%I:%M %p")


def format_time(value: datetime) -> str:
    """Convert a datetime back into the dataset's lowercase time format."""

    return value.strftime("%I:%M %p").lstrip("0").lower()


def format_ranges(ranges: list[tuple[datetime, datetime]]) -> list[str]:
    """Convert datetime ranges into display strings."""

    return [f"{format_time(start)} - {format_time(end)}" for start, end in ranges]


def split_days(value: str) -> list[str]:
    """Break strings like 'MWF' into ['M', 'W', 'F']."""

    days = [char for char in value.strip().upper() if char in DAY_ORDER]
    return [day for day in DAY_ORDER if day in days]


def merge_time_ranges(
    ranges: list[tuple[datetime, datetime]], gap_minutes: int = 15
) -> list[tuple[datetime, datetime]]:
    """Merge ranges when they overlap or are separated by <= gap_minutes."""

    if not ranges:
        return []

    ordered = sorted(ranges)
    merged = [ordered[0]]
    gap = timedelta(minutes=gap_minutes)
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + gap:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def clean_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Return (cleaned_rows, other_buildings).

    - cleaned_rows: only rows with a standard room number (physical room)
    - other_buildings: building labels that appear, but never with a standard room
      number (online/off-campus/special site labels, etc.)
    """

    cleaned: list[dict] = []

    # Track which building labels ever show a standard room, vs only non-standard.
    standard_rooms_by_building: dict[str, set[str]] = defaultdict(set)
    seen_nonstandard_building: set[str] = set()

    for row in rows:
        building, room = normalize_location(row.get("Building"), row.get("Room"))

        # Drop entries with no usable location text at all.
        if _is_missing(building) and _is_missing(room):
            continue

        # If we can't attribute it to a building, it can't participate in the
        # building->rooms mapping.
        if _is_missing(building):
            continue

        if _is_standard_room(room):
            # Keep the row (physical room).
            normalized = dict(row)
            normalized["Building"] = building
            normalized["Room"] = room.strip()
            cleaned.append(normalized)
            standard_rooms_by_building[building].add(room.strip())
        else:
            # Remember this building label as non-standard unless we later see
            # a standard room for it.
            seen_nonstandard_building.add(building)

    other_buildings = sorted(
        [b for b in seen_nonstandard_building if b not in standard_rooms_by_building],
        key=lambda s: s.upper(),
    )

    return cleaned, other_buildings


def building_to_rooms(rows: list[dict], other_buildings: list[str]) -> dict[str, list[str]]:
    # Build a unique set of rooms per building.
    rooms_by_building: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        building = row["Building"].strip()
        room = row["Room"].strip()
        if not building or not room:
            continue
        rooms_by_building[building].add(room)

    building_rooms: dict[str, list[str]] = {
        building: sorted(list(rooms), key=room_sort_key)
        for building, rooms in sorted(rooms_by_building.items(), key=lambda kv: kv[0].upper())
    }

    # Add a convenience bucket for non-physical "building" labels.
    building_rooms["OTHER"] = other_buildings

    return building_rooms


def build_default_building_hours(
    building_rooms: dict[str, list[str]],
    default_open_time: str,
    default_close_time: str,
) -> dict[str, dict[str, str]]:
    hours: dict[str, dict[str, str]] = {}
    for building in sorted(building_rooms, key=str.upper):
        if building == "OTHER":
            continue
        hours[building] = {
            "open": default_open_time,
            "close": default_close_time,
        }
    return hours


def load_building_hours(
    path: Path,
    building_rooms: dict[str, list[str]],
    default_open_time: str,
    default_close_time: str,
) -> dict[str, tuple[str, str]]:
    default_hours = build_default_building_hours(
        building_rooms,
        default_open_time,
        default_close_time,
    )

    if not path.exists():
        path.write_text(json.dumps(default_hours, indent=2, sort_keys=True), encoding="utf-8")
        raw_hours = default_hours
    else:
        raw_hours = json.loads(path.read_text(encoding="utf-8"))

    hours_by_building: dict[str, tuple[str, str]] = {}
    for building in default_hours:
        value = raw_hours.get(building, {})
        open_time = value.get("open", default_open_time)
        close_time = value.get("close", default_close_time)
        hours_by_building[building] = (open_time, close_time)

    return hours_by_building


def build_room_occupancy(rows: list[dict]) -> dict[str, dict[str, dict[str, list[str]]]]:
    """Return building -> room -> day -> occupied time ranges.

    Each day contains a list of strings like '9:30 am - 12:15 pm'. Back-to-back
    classes are merged when the gap between them is 15 minutes or less.
    """

    occupancy_ranges: dict[str, dict[str, dict[str, list[tuple[datetime, datetime]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for row in rows:
        building = row["Building"].strip()
        room = row["Room"].strip()
        days = split_days(row.get("Days", ""))
        if not building or not room or not days:
            continue

        start = parse_time(row["Time Start"])
        end = parse_time(row["Time End"])
        for day in days:
            occupancy_ranges[building][room][day].append((start, end))

    occupancy: dict[str, dict[str, dict[str, list[str]]]] = {}
    for building in sorted(occupancy_ranges, key=str.upper):
        occupancy[building] = {}
        for room in sorted(occupancy_ranges[building], key=room_sort_key):
            day_map: dict[str, list[str]] = {}
            for day in DAY_ORDER:
                ranges = occupancy_ranges[building][room].get(day, [])
                if not ranges:
                    continue

                merged_ranges = merge_time_ranges(ranges)
                day_map[day] = format_ranges(merged_ranges)

            occupancy[building][room] = day_map

    return occupancy


def invert_room_occupancy(
    occupancy: dict[str, dict[str, dict[str, list[str]]]],
    default_open_time: str = "8:00 am",
    default_close_time: str = "10:00 pm",
    building_hours: dict[str, tuple[str, str]] | None = None,
) -> dict[str, dict[str, dict[str, list[str]]]]:
    """Return building -> room -> day -> open time ranges.

    `building_hours` can override the default open/close window per building:
    {
        "Lowder Hall": ("7:30 am", "9:00 pm"),
    }
    """

    hours_by_building = building_hours or {}
    availability: dict[str, dict[str, dict[str, list[str]]]] = {}

    for building in sorted(occupancy, key=str.upper):
        building_open_str, building_close_str = hours_by_building.get(
            building,
            (default_open_time, default_close_time),
        )
        building_open = parse_time(building_open_str)
        building_close = parse_time(building_close_str)
        if building_close <= building_open:
            raise ValueError(f"Close time must be after open time for {building!r}")

        availability[building] = {}
        for room in sorted(occupancy[building], key=room_sort_key):
            room_availability: dict[str, list[str]] = {}
            for day in DAY_ORDER:
                occupied_strings = occupancy[building][room].get(day, [])
                occupied_ranges = [
                    tuple(parse_time(part.strip()) for part in time_range.split(" - ", 1))
                    for time_range in occupied_strings
                ]

                free_ranges: list[tuple[datetime, datetime]] = []
                cursor = building_open
                for occupied_start, occupied_end in occupied_ranges:
                    clipped_start = max(occupied_start, building_open)
                    clipped_end = min(occupied_end, building_close)
                    if clipped_end <= building_open or clipped_start >= building_close:
                        continue
                    if cursor < clipped_start:
                        free_ranges.append((cursor, clipped_start))
                    cursor = max(cursor, clipped_end)

                if cursor < building_close:
                    free_ranges.append((cursor, building_close))

                room_availability[day] = format_ranges(free_ranges)

            availability[building][room] = room_availability

    return availability


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean scheduling data and build a building->rooms mapping")
    parser.add_argument("--input", default="scheduling_data.csv", help="Input CSV path")
    parser.add_argument(
        "--clean-csv",
        default="scheduling_data_clean.csv",
        help="Output path for cleaned CSV (only rows with standard room numbers)",
    )
    parser.add_argument(
        "--rooms-json",
        default="building_rooms.json",
        help="Output path for building->rooms JSON",
    )
    parser.add_argument(
        "--occupancy-json",
        default="room_occupancy.json",
        help="Output path for building->room->day occupied time ranges JSON",
    )
    parser.add_argument(
        "--availability-json",
        default="room_availability.json",
        help="Output path for building->room->day open time ranges JSON",
    )
    parser.add_argument(
        "--building-hours-json",
        default="building_hours.json",
        help="Path to per-building open/close times JSON (created with defaults if missing)",
    )
    parser.add_argument(
        "--open-time",
        default="8:00 am",
        help="Default building open time for the inverse availability view",
    )
    parser.add_argument(
        "--close-time",
        default="10:00 pm",
        help="Default building close time for the inverse availability view",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    fieldnames, rows = read_csv(input_path)
    cleaned, other_buildings = clean_rows(rows)

    cleaned_csv_path = Path(args.clean_csv)
    write_csv(cleaned_csv_path, fieldnames, cleaned)

    rooms = building_to_rooms(cleaned, other_buildings)
    rooms_json_path = Path(args.rooms_json)
    rooms_json_path.write_text(json.dumps(rooms, indent=2, sort_keys=True), encoding="utf-8")

    building_hours_json_path = Path(args.building_hours_json)
    building_hours = load_building_hours(
        building_hours_json_path,
        rooms,
        args.open_time,
        args.close_time,
    )

    occupancy = build_room_occupancy(cleaned)
    occupancy_json_path = Path(args.occupancy_json)
    occupancy_json_path.write_text(json.dumps(occupancy, indent=2, sort_keys=True), encoding="utf-8")

    availability = invert_room_occupancy(
        occupancy,
        default_open_time=args.open_time,
        default_close_time=args.close_time,
        building_hours=building_hours,
    )
    availability_json_path = Path(args.availability_json)
    availability_json_path.write_text(json.dumps(availability, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Read {len(rows)} rows from {input_path}")
    print(f"Wrote {len(cleaned)} cleaned rows to {cleaned_csv_path}")
    physical_buildings = max(0, len(rooms) - 1)  # excluding OTHER
    print(f"Wrote {physical_buildings} buildings (+ OTHER={len(other_buildings)}) to {rooms_json_path}")
    print(f"Wrote/updated per-building hours in {building_hours_json_path}")
    print(f"Wrote room occupancy by day to {occupancy_json_path}")
    print(f"Wrote room availability by day to {availability_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
