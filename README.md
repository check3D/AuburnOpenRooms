# AuburnOpenRooms

Locate empty rooms on campus.

## Workflow

1. Scrape the scheduling data:

```bash
python scrape_scheduling_data.py
```

2. Process the CSV into room maps, occupancy, availability, and per-building hours:

```bash
python process_data.py
```

This creates or reconciles `building_hours.json`. Buildings default to `8:00 am`
through `10:00 pm` Monday-Friday and closed Saturday-Sunday. Each building has
per-day entries that can be edited for different hours or weekend access.

Meeting start/end dates are preserved, so short-session classes only block a
room while that meeting is active. The generated occupancy and availability
JSON files are keyed by ISO date (`YYYY-MM-DD`) rather than weekday alone.

3. Run the CLI and choose a building to see which rooms are open right now:

```bash
python cli.py
```

You can also skip the prompt with an exact building name:

```bash
python cli.py --building "Haley Center"
```

For quick testing, you can override the current time:

```bash
python cli.py --building "Haley Center" --time "3:30 pm"
```

Override the date as well when checking another day:

```bash
python cli.py --building "Haley Center" --date "2026-09-14" --time "3:30 pm"
```

## Web UI

A simple browser UI is included in the repo root:

- `index.html`
- `app.css`
- `app.js`

It uses the generated JSON files (`building_rooms.json` and `room_availability.json`) to show:

- buildings on the left with current open-room counts
- open rooms for the selected building
- rooms opening soon (next 2 hours)
- a `Now` / `Custom` date-time toggle for previewing availability at another time
- expandable room rows that show that room's schedule for the selected date (time blocks + class/CRN)

Run a local static server from the project root, then open the page:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.

Do not open `index.html` directly from File Explorer. Browsers block the JSON
and CSV requests that the page needs when it is loaded with a `file://` URL.
