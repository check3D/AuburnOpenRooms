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

This creates `building_hours.json` if it does not already exist. Right now every building defaults to `8:00 am` through `10:00 pm`, but you can edit that file later to give specific buildings different hours.

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

## Web UI

A simple browser UI is included in the repo root:

- `index.html`
- `app.css`
- `app.js`

It uses the generated JSON files (`building_rooms.json` and `room_availability.json`) to show:

- buildings on the left with current open-room counts
- open rooms for the selected building
- rooms opening soon (next 2 hours)
- a `Now` / `Custom` day-time toggle for previewing availability at another time
- expandable room rows that show that room's day schedule (time blocks + class/CRN)

Run a local static server from the project root, then open the page:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.
