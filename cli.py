import argparse
import json
from datetime import datetime
from pathlib import Path

from process_data import parse_time, room_sort_key


DAY_CODE_BY_WEEKDAY = {
    0: "M",
    1: "T",
    2: "W",
    3: "R",
    4: "F",
    5: "S",
    6: "U",
}

DAY_NAME_BY_CODE = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
    "S": "Saturday",
    "U": "Sunday",
}


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python process_data.py` to generate the data files."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def parse_clock_time(value: str) -> datetime:
    return parse_time(value)


def parse_time_range(value: str) -> tuple[datetime, datetime]:
    start_text, end_text = value.split(" - ", 1)
    return parse_clock_time(start_text.strip()), parse_clock_time(end_text.strip())


def select_building(buildings: list[str], requested: str | None) -> str:
    if requested:
        normalized = requested.strip().lower()
        for building in buildings:
            if building.lower() == normalized:
                return building
        raise ValueError(f"Unknown building: {requested}")

    print("Select a building:")
    for index, building in enumerate(buildings, start=1):
        print(f"{index:>2}. {building}")

    while True:
        choice = input("Building number or exact name: ").strip()
        if not choice:
            print("Please enter a building number or exact name.")
            continue

        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(buildings):
                return buildings[index - 1]
            print("That number is out of range.")
            continue

        normalized = choice.lower()
        for building in buildings:
            if building.lower() == normalized:
                return building
        print("No exact building match found. Try the number shown in the list.")


def rooms_available_now(
    availability: dict[str, dict[str, dict[str, list[str]]]],
    building: str,
    day_code: str,
    current_time: datetime,
) -> list[tuple[str, str]]:
    building_data = availability.get(building, {})
    matches: list[tuple[str, str]] = []

    for room in sorted(building_data, key=room_sort_key):
        for time_range in building_data[room].get(day_code, []):
            start, end = parse_time_range(time_range)
            if start <= current_time < end:
                matches.append((room, end.strftime("%I:%M %p").lstrip("0").lower()))
                break

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select a building and see which rooms are available right now."
    )
    parser.add_argument(
        "--rooms-json",
        default="building_rooms.json",
        help="Path to building->rooms JSON",
    )
    parser.add_argument(
        "--availability-json",
        default="room_availability.json",
        help="Path to building->room->day availability JSON",
    )
    parser.add_argument(
        "--building",
        help="Exact building name to skip the interactive prompt",
    )
    parser.add_argument(
        "--time",
        help="Override the current local time for testing, for example '3:30 pm'",
    )
    args = parser.parse_args()

    rooms_by_building = load_json(Path(args.rooms_json))
    availability = load_json(Path(args.availability_json))

    buildings = [building for building in sorted(rooms_by_building, key=str.upper) if building != "OTHER"]
    selected_building = select_building(buildings, args.building)

    now = datetime.now()
    current_time = parse_clock_time(args.time) if args.time else now
    day_code = DAY_CODE_BY_WEEKDAY[now.weekday()]
    day_name = DAY_NAME_BY_CODE[day_code]

    available_rooms = rooms_available_now(availability, selected_building, day_code, current_time)

    print()
    print(f"{selected_building}")
    print(f"{day_name} at {current_time.strftime('%I:%M %p').lstrip('0').lower()}")

    if not available_rooms:
        print("No rooms are currently available.")
        return 0

    print(f"{len(available_rooms)} room(s) available now:")
    for room, end_time in available_rooms:
        print(f"- Room {room}: available until {end_time}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
