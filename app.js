const AVAILABILITY_PATH = "room_availability.json";
const BUILDINGS_PATH = "building_rooms.json";
const SCHEDULE_CSV_PATH = "scheduling_data_clean.csv";
const SOON_WINDOW_MINUTES = 120;

const DAY_CODE_BY_WEEKDAY = ["U", "M", "T", "W", "R", "F", "S"];
const DAY_NAME_BY_CODE = {
  M: "Monday",
  T: "Tuesday",
  W: "Wednesday",
  R: "Thursday",
  F: "Friday",
  S: "Saturday",
  U: "Sunday",
};
const DAY_CODES = ["M", "T", "W", "R", "F", "S", "U"];
const MONTH_NUMBER_BY_NAME = {
  Jan: 1,
  Feb: 2,
  Mar: 3,
  Apr: 4,
  May: 5,
  Jun: 6,
  Jul: 7,
  Aug: 8,
  Sep: 9,
  Oct: 10,
  Nov: 11,
  Dec: 12,
};

const state = {
  roomsByBuilding: {},
  availabilityByBuilding: {},
  scheduleIndex: {},
  selectedBuilding: "",
  query: "",
  timeMode: "now",
  customDate: "",
  customMinute: 8 * 60,
  expandedRoomKey: "",
};

function parseClockToMinutes(text) {
  const normalized = String(text).trim().toLowerCase();
  const match = normalized.match(/^(\d{1,2}):(\d{2})\s*(am|pm)$/);
  if (!match) {
    return null;
  }
  let hour = Number(match[1]);
  const minute = Number(match[2]);
  const meridiem = match[3];
  if (hour === 12) {
    hour = 0;
  }
  if (meridiem === "pm") {
    hour += 12;
  }
  return hour * 60 + minute;
}

function formatMinutesAsClock(totalMinutes) {
  let hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const meridiem = hours >= 12 ? "pm" : "am";
  if (hours === 0) {
    hours = 12;
  } else if (hours > 12) {
    hours -= 12;
  }
  return `${hours}:${String(minutes).padStart(2, "0")} ${meridiem}`;
}

function formatMinutesForInput(totalMinutes) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function parseInputTime(value) {
  const match = String(value).trim().match(/^(\d{2}):(\d{2})$/);
  if (!match) {
    return null;
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
    return null;
  }
  return hours * 60 + minutes;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0 && mins > 0) {
    return `${hours}h ${mins}m`;
  }
  if (hours > 0) {
    return `${hours}h`;
  }
  return `${mins}m`;
}

function parseRange(rangeText) {
  const parts = String(rangeText).split(" - ");
  if (parts.length !== 2) {
    return null;
  }
  const start = parseClockToMinutes(parts[0]);
  const end = parseClockToMinutes(parts[1]);
  if (start == null || end == null) {
    return null;
  }
  return { start, end };
}

function parseCsvLine(line) {
  const fields = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === "," && !inQuotes) {
      fields.push(current);
      current = "";
      continue;
    }
    current += char;
  }

  fields.push(current);
  return fields;
}

function parseCsvText(csvText) {
  const lines = String(csvText)
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => line.trim().length > 0);

  if (lines.length < 2) {
    return [];
  }

  const headers = parseCsvLine(lines[0]).map((header, index) => {
    if (index === 0) {
      return header.replace(/^\uFEFF/, "").trim();
    }
    return header.trim();
  });
  const rows = [];
  for (let i = 1; i < lines.length; i += 1) {
    const values = parseCsvLine(lines[i]);
    const row = {};
    for (let j = 0; j < headers.length; j += 1) {
      row[headers[j]] = values[j] || "";
    }
    rows.push(row);
  }

  return rows;
}

function splitDays(dayText) {
  const normalized = String(dayText).toUpperCase();
  return DAY_CODES.filter((dayCode) => normalized.includes(dayCode));
}

function indexScheduleRows(rows) {
  const index = {};

  for (const row of rows) {
    const building = String(row["Building"] || "").trim();
    const room = String(row["Room"] || "").trim();
    const className = String(row["Class Name"] || "").trim();
    const crn = String(row["CRN"] || "").trim();
    const startText = String(row["Time Start"] || "").trim();
    const endText = String(row["Time End"] || "").trim();
    const dateStart = parseDisplayDate(String(row["Date Start"] || "").trim());
    const dateEnd = parseDisplayDate(String(row["Date End"] || "").trim());
    const start = parseClockToMinutes(startText);
    const end = parseClockToMinutes(endText);

    if (
      !building ||
      !room ||
      !className ||
      start == null ||
      end == null ||
      end <= start ||
      !dateStart ||
      !dateEnd
    ) {
      continue;
    }

    const days = splitDays(row["Days"] || "");
    if (days.length === 0) {
      continue;
    }

    if (!index[building]) {
      index[building] = {};
    }
    if (!index[building][room]) {
      index[building][room] = [];
    }
    index[building][room].push({
      crn,
      className,
      start,
      end,
      startText,
      endText,
      dateStart,
      dateEnd,
      days,
    });
  }

  for (const building of Object.keys(index)) {
    for (const room of Object.keys(index[building])) {
      index[building][room].sort(
        (a, b) => a.start - b.start || a.end - b.end || a.className.localeCompare(b.className)
      );
    }
  }

  return index;
}

function parseDisplayDate(value) {
  const match = String(value).match(/^([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})$/);
  if (!match) {
    return "";
  }
  const month = MONTH_NUMBER_BY_NAME[match[1]];
  const day = Number(match[2]);
  const year = Number(match[3]);
  if (!month || day < 1 || day > 31) {
    return "";
  }
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function formatDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(dateKey) {
  const match = String(dateKey).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return null;
  }
  const parsed = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getRoomSchedule(building, room, dateKey, dayCode) {
  const meetings = state.scheduleIndex?.[building]?.[room] || [];
  return meetings.filter(
    (meeting) =>
      meeting.dateStart <= dateKey &&
      dateKey <= meeting.dateEnd &&
      meeting.days.includes(dayCode)
  );
}

function getCurrentDayCode(date) {
  return DAY_CODE_BY_WEEKDAY[date.getDay()];
}

function getCurrentMinuteOfDay(date) {
  return date.getHours() * 60 + date.getMinutes();
}

function setCustomFromDate(date) {
  state.customDate = formatDateKey(date);
  state.customMinute = getCurrentMinuteOfDay(date);
}

function getViewContext() {
  if (state.timeMode === "custom") {
    const selectedDate = parseDateKey(state.customDate) || new Date();
    const dateKey = formatDateKey(selectedDate);
    const dayCode = getCurrentDayCode(selectedDate);
    const minuteOfDay = Number.isFinite(state.customMinute) ? state.customMinute : 8 * 60;
    return {
      dateKey,
      dayCode,
      minuteOfDay,
      isCustom: true,
      clockLabel: `Preview: ${selectedDate.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })} at ${formatMinutesAsClock(minuteOfDay)}`,
    };
  }

  const now = new Date();
  const dayCode = getCurrentDayCode(now);
  return {
    dateKey: formatDateKey(now),
    dayCode,
    minuteOfDay: getCurrentMinuteOfDay(now),
    isCustom: false,
    clockLabel: `Now: ${now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`,
  };
}

function renderTimeControls() {
  const isCustom = state.timeMode === "custom";
  const modeNow = document.querySelector("#mode-now");
  const modeCustom = document.querySelector("#mode-custom");
  const dateSelect = document.querySelector("#date-select");
  const timeSelect = document.querySelector("#time-select");

  modeNow.classList.toggle("is-active", !isCustom);
  modeCustom.classList.toggle("is-active", isCustom);
  modeNow.setAttribute("aria-pressed", String(!isCustom));
  modeCustom.setAttribute("aria-pressed", String(isCustom));

  dateSelect.disabled = !isCustom;
  timeSelect.disabled = !isCustom;
  dateSelect.value = state.customDate;
  timeSelect.value = formatMinutesForInput(state.customMinute);
}

function buildRoomStatus(building, dateKey, nowMinute) {
  const buildingData = state.availabilityByBuilding[building] || {};
  const openNow = [];
  const openingSoon = [];

  for (const room of Object.keys(buildingData)) {
    const ranges = buildingData[room]?.[dateKey] || [];
    const parsedRanges = ranges.map(parseRange).filter(Boolean);

    let currentRange = null;
    let nextRange = null;

    for (const range of parsedRanges) {
      if (!currentRange && range.start <= nowMinute && nowMinute < range.end) {
        currentRange = range;
        break;
      }
      if (!nextRange && range.start > nowMinute) {
        nextRange = range;
      }
    }

    if (currentRange) {
      openNow.push({
        room,
        end: currentRange.end,
        minutesLeft: currentRange.end - nowMinute,
      });
      continue;
    }

    if (nextRange && nextRange.start <= nowMinute + SOON_WINDOW_MINUTES) {
      openingSoon.push({
        room,
        start: nextRange.start,
        end: nextRange.end,
        durationMinutes: Math.max(0, nextRange.end - nextRange.start),
      });
    }
  }

  openNow.sort(
    (a, b) =>
      b.minutesLeft - a.minutesLeft ||
      b.end - a.end ||
      a.room.localeCompare(b.room, undefined, { numeric: true })
  );
  openingSoon.sort(
    (a, b) =>
      b.durationMinutes - a.durationMinutes ||
      a.start - b.start ||
      a.room.localeCompare(b.room, undefined, { numeric: true })
  );
  return { openNow, openingSoon };
}

function getBuildingOpenCounts(dateKey, nowMinute) {
  const counts = new Map();
  for (const building of Object.keys(state.roomsByBuilding)) {
    if (building === "OTHER") {
      continue;
    }
    const { openNow } = buildRoomStatus(building, dateKey, nowMinute);
    counts.set(building, openNow.length);
  }
  return counts;
}

function renderBuildingList(dateKey, nowMinute) {
  const listEl = document.querySelector("#building-list");
  const counts = getBuildingOpenCounts(dateKey, nowMinute);
  const query = state.query.trim().toLowerCase();

  const buildings = Object.keys(state.roomsByBuilding)
    .filter((name) => name !== "OTHER");

  const filtered = buildings
    .filter((name) => name.toLowerCase().includes(query))
    .sort(
      (a, b) =>
        (counts.get(b) || 0) - (counts.get(a) || 0) ||
        a.localeCompare(b)
    );
  listEl.innerHTML = "";

  for (const building of filtered) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "building-button";
    if (building === state.selectedBuilding) {
      button.classList.add("is-active");
    }
    button.addEventListener("click", () => {
      state.selectedBuilding = building;
      render();
    });

    const nameEl = document.createElement("span");
    nameEl.className = "building-name";
    nameEl.textContent = building;

    const badgeEl = document.createElement("span");
    badgeEl.className = "badge";
    const openCount = counts.get(building) || 0;
    badgeEl.textContent = `${openCount} open`;

    button.append(nameEl, badgeEl);
    li.appendChild(button);
    listEl.appendChild(li);
  }

  if (filtered.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "No building names match this search.";
    listEl.appendChild(empty);
  }

  if (!filtered.includes(state.selectedBuilding) && filtered.length > 0) {
    state.selectedBuilding = filtered[0];
  }
}

function renderRoomList(targetEl, rows, buildContent, context) {
  targetEl.innerHTML = "";
  if (rows.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "No rooms to show.";
    targetEl.appendChild(empty);
    return;
  }

  const template = document.querySelector("#room-item-template");
  for (const row of rows) {
    const node = template.content.cloneNode(true);
    const button = node.querySelector(".room-main");
    const details = node.querySelector(".room-details");
    const hint = node.querySelector(".room-hint");
    const roomKey = `${context.building}|${context.dateKey}|${row.room}`;
    const isExpanded = state.expandedRoomKey === roomKey;

    node.querySelector(".room-name").textContent = `Room ${row.room}`;
    const content = buildContent(row);
    node.querySelector(".room-subtext").textContent = content.subtext;
    node.querySelector(".room-time").textContent = content.time;

    button.classList.toggle("is-expanded", isExpanded);
    button.setAttribute("aria-expanded", String(isExpanded));
    hint.textContent = isExpanded ? "Hide date schedule" : "View date schedule";
    button.addEventListener("click", () => {
      state.expandedRoomKey = isExpanded ? "" : roomKey;
      render();
    });

    if (isExpanded) {
      const schedule = getRoomSchedule(
        context.building,
        row.room,
        context.dateKey,
        context.dayCode
      );
      details.hidden = false;
      if (schedule.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = "No scheduled classes for this room on this date.";
        details.appendChild(empty);
      } else {
        const list = document.createElement("ul");
        list.className = "schedule-list";
        for (const meeting of schedule) {
          const item = document.createElement("li");
          item.className = "schedule-item";

          const time = document.createElement("p");
          time.className = "schedule-time";
          time.textContent = `${meeting.startText} - ${meeting.endText}`;

          const course = document.createElement("p");
          course.className = "schedule-course";
          course.textContent = meeting.crn ? `${meeting.className} (CRN ${meeting.crn})` : meeting.className;

          item.append(time, course);
          list.appendChild(item);
        }
        details.appendChild(list);
      }
    }

    if (!isExpanded) {
      details.hidden = true;
    }
    targetEl.appendChild(node);
  }
}

function renderRightPanel(dayCode, nowMinute, viewContext) {
  const building = state.selectedBuilding;
  const dayName = DAY_NAME_BY_CODE[dayCode];
  const { openNow, openingSoon } = buildRoomStatus(building, viewContext.dateKey, nowMinute);

  document.querySelector("#selected-building").textContent = building || "No building";
  document.querySelector("#selected-building-subtitle").textContent = viewContext.isCustom ? `${dayName} (custom)` : `${dayName}`;
  document.querySelector("#clock").textContent = viewContext.clockLabel;
  document.querySelector("#open-now-count").textContent = `${openNow.length} open now`;
  document.querySelector("#opening-soon-count").textContent = `${openingSoon.length} opening soon`;

  const openNowListEl = document.querySelector("#open-now-list");
  renderRoomList(openNowListEl, openNow, (row) => ({
    subtext: `Available for ${formatDuration(row.minutesLeft)} more`,
    time: `Until ${formatMinutesAsClock(row.end)}`,
  }), { building, dayCode, dateKey: viewContext.dateKey });

  const soonListEl = document.querySelector("#opening-soon-list");
  renderRoomList(soonListEl, openingSoon, (row) => ({
    subtext: `Open for ${formatDuration(row.durationMinutes)}`,
    time: `${formatMinutesAsClock(row.start)} - ${formatMinutesAsClock(row.end)}`,
  }), { building, dayCode, dateKey: viewContext.dateKey });
}

function render() {
  const viewContext = getViewContext();
  renderBuildingList(viewContext.dateKey, viewContext.minuteOfDay);
  renderRightPanel(viewContext.dayCode, viewContext.minuteOfDay, viewContext);
  renderTimeControls();
}

async function loadData() {
  if (window.location.protocol === "file:") {
    throw new Error(
      "This page cannot load its data when opened as a local file. Start a web server from the project folder, then open http://localhost:8000/."
    );
  }

  const [buildingsResponse, availabilityResponse, scheduleResponse] = await Promise.all([
    fetch(BUILDINGS_PATH),
    fetch(AVAILABILITY_PATH),
    fetch(SCHEDULE_CSV_PATH),
  ]);
  const failedAssets = [
    [BUILDINGS_PATH, buildingsResponse],
    [AVAILABILITY_PATH, availabilityResponse],
  ]
    .filter(([, response]) => !response.ok)
    .map(([path, response]) => `${path} (${response.status})`);
  if (failedAssets.length > 0) {
    throw new Error(
      `Unable to load ${failedAssets.join(", ")}. Make sure the web server was started from the project folder.`
    );
  }
  state.roomsByBuilding = await buildingsResponse.json();
  state.availabilityByBuilding = await availabilityResponse.json();

  if (scheduleResponse.ok) {
    const scheduleCsv = await scheduleResponse.text();
    state.scheduleIndex = indexScheduleRows(parseCsvText(scheduleCsv));
  } else {
    state.scheduleIndex = {};
  }
}

function wireEvents() {
  const search = document.querySelector("#building-search");
  const modeNow = document.querySelector("#mode-now");
  const modeCustom = document.querySelector("#mode-custom");
  const dateSelect = document.querySelector("#date-select");
  const timeSelect = document.querySelector("#time-select");

  search.addEventListener("input", (event) => {
    state.query = event.target.value;
    render();
  });

  modeNow.addEventListener("click", () => {
    state.timeMode = "now";
    render();
  });

  modeCustom.addEventListener("click", () => {
    if (state.timeMode === "now") {
      setCustomFromDate(new Date());
    }
    state.timeMode = "custom";
    render();
  });

  dateSelect.addEventListener("change", (event) => {
    state.customDate = event.target.value;
    state.timeMode = "custom";
    render();
  });

  timeSelect.addEventListener("input", (event) => {
    const parsed = parseInputTime(event.target.value);
    if (parsed == null) {
      return;
    }
    state.customMinute = parsed;
    state.timeMode = "custom";
    render();
  });
}

async function boot() {
  try {
    await loadData();
    const buildings = Object.keys(state.roomsByBuilding)
      .filter((name) => name !== "OTHER")
      .sort((a, b) => a.localeCompare(b));
    state.selectedBuilding = buildings[0] || "";
    setCustomFromDate(new Date());
    wireEvents();
    render();
    setInterval(() => {
      if (state.timeMode === "now") {
        render();
      }
    }, 60_000);
  } catch (error) {
    document.querySelector("#selected-building").textContent = "Data load error";
    const openNowList = document.querySelector("#open-now-list");
    openNowList.innerHTML = "";
    document.querySelector("#opening-soon-list").innerHTML = "";
    const errorItem = document.createElement("li");
    errorItem.className = "empty-state";
    errorItem.textContent = error instanceof Error ? error.message : "Unable to load room data.";
    openNowList.appendChild(errorItem);
  }
}

boot();
