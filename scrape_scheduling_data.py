import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import re
import csv

url = "https://ssbprod.auburn.edu/pls/PROD/bwckschd.p_get_crse_unsec"
payload = [
    ("term_in", "202710"),

    # subjects
    ("sel_subj", "dummy"),
    ("sel_subj", "ACCT"),
    ("sel_subj", "ADED"),
    ("sel_subj", "AERO"),
    ("sel_subj", "AIRF"),
    ("sel_subj", "AAAS"),
    ("sel_subj", "AGEC"),
    ("sel_subj", "AGSC"),
    ("sel_subj", "AGRI"),
    ("sel_subj", "ANSC"),
    ("sel_subj", "ANTH"),
    ("sel_subj", "APBT"),
    ("sel_subj", "ARCH"),
    ("sel_subj", "ARTS"),
    ("sel_subj", "GLOB"),
    ("sel_subj", "AVMG"),
    ("sel_subj", "BATM"),
    ("sel_subj", "BCHE"),
    ("sel_subj", "BIOL"),
    ("sel_subj", "BIOP"),
    ("sel_subj", "BSEN"),
    ("sel_subj", "BSCI"),
    ("sel_subj", "BUSI"),
    ("sel_subj", "BUAL"),
    ("sel_subj", "CTCT"),
    ("sel_subj", "CHEN"),
    ("sel_subj", "CHEM"),
    ("sel_subj", "CIVL"),
    ("sel_subj", "COMM"),
    ("sel_subj", "CMJN"),
    ("sel_subj", "CPLN"),
    ("sel_subj", "COMP"),
    ("sel_subj", "CADS"),
    ("sel_subj", "COOP"),
    ("sel_subj", "COUN"),
    ("sel_subj", "CSES"),
    ("sel_subj", "DRDD"),
    ("sel_subj", "DBPS"),
    ("sel_subj", "EAGL"),
    ("sel_subj", "CTEC"),
    ("sel_subj", "ESSI"),
    ("sel_subj", "ECON"),
    ("sel_subj", "ERMA"),
    ("sel_subj", "EDLD"),
    ("sel_subj", "EDMD"),
    ("sel_subj", "EPSY"),
    ("sel_subj", "ELEC"),
    ("sel_subj", "CTEE"),
    ("sel_subj", "ENGR"),
    ("sel_subj", "ENGL"),
    ("sel_subj", "CTES"),
    ("sel_subj", "ENTM"),
    ("sel_subj", "ENFB"),
    ("sel_subj", "ENVD"),
    ("sel_subj", "ENVI"),
    ("sel_subj", "EXPL"),
    ("sel_subj", "FINC"),
    ("sel_subj", "FISH"),
    ("sel_subj", "AVMF"),
    ("sel_subj", "FDSC"),
    ("sel_subj", "FLNG"),
    ("sel_subj", "FLAS"),
    ("sel_subj", "FLCN"),
    ("sel_subj", "FLFR"),
    ("sel_subj", "FLGR"),
    ("sel_subj", "FLGC"),
    ("sel_subj", "FLIT"),
    ("sel_subj", "FLJP"),
    ("sel_subj", "FLKN"),
    ("sel_subj", "FLLN"),
    ("sel_subj", "FLSP"),
    ("sel_subj", "FOEN"),
    ("sel_subj", "FORY"),
    ("sel_subj", "FOWS"),
    ("sel_subj", "FOUN"),
    ("sel_subj", "GEOG"),
    ("sel_subj", "GEOL"),
    ("sel_subj", "GSEI"),
    ("sel_subj", "GSHS"),
    ("sel_subj", "GRAD"),
    ("sel_subj", "GDES"),
    ("sel_subj", "HADM"),
    ("sel_subj", "HORP"),
    ("sel_subj", "HIED"),
    ("sel_subj", "HIST"),
    ("sel_subj", "HONR"),
    ("sel_subj", "HORT"),
    ("sel_subj", "HOSP"),
    ("sel_subj", "HDFS"),
    ("sel_subj", "HRMN"),
    ("sel_subj", "HUSC"),
    ("sel_subj", "INSY"),
    ("sel_subj", "INDD"),
    ("sel_subj", "ISMN"),
    ("sel_subj", "EDUC"),
    ("sel_subj", "PYDI"),
    ("sel_subj", "IDSC"),
    ("sel_subj", "ARIA"),
    ("sel_subj", "INTL"),
    ("sel_subj", "JRNL"),
    ("sel_subj", "JRSP"),
    ("sel_subj", "KINE"),
    ("sel_subj", "LBSC"),
    ("sel_subj", "LAND"),
    ("sel_subj", "LEAD"),
    ("sel_subj", "LBAR"),
    ("sel_subj", "MNGT"),
    ("sel_subj", "MKTG"),
    ("sel_subj", "MATL"),
    ("sel_subj", "MATH"),
    ("sel_subj", "MECH"),
    ("sel_subj", "MDIA"),
    ("sel_subj", "FILM"),
    ("sel_subj", "MILS"),
    ("sel_subj", "MUSI"),
    ("sel_subj", "MUAP"),
    ("sel_subj", "CTMU"),
    ("sel_subj", "MUSE"),
    ("sel_subj", "NATR"),
    ("sel_subj", "NAVS"),
    ("sel_subj", "NURS"),
    ("sel_subj", "NTRI"),
    ("sel_subj", "PARK"),
    ("sel_subj", "PYPD"),
    ("sel_subj", "PHIL"),
    ("sel_subj", "PHED"),
    ("sel_subj", "KNPT"),
    ("sel_subj", "PHYS"),
    ("sel_subj", "PLPA"),
    ("sel_subj", "POLI"),
    ("sel_subj", "PFEN"),
    ("sel_subj", "POUL"),
    ("sel_subj", "PSYC"),
    ("sel_subj", "PRCM"),
    ("sel_subj", "PAOH"),
    ("sel_subj", "CTRD"),
    ("sel_subj", "RDEV"),
    ("sel_subj", "RSED"),
    ("sel_subj", "RELG"),
    ("sel_subj", "RSOC"),
    ("sel_subj", "SCMH"),
    ("sel_subj", "CTSE"),
    ("sel_subj", "SOWO"),
    ("sel_subj", "SOCY"),
    ("sel_subj", "SPCE"),
    ("sel_subj", "SLHS"),
    ("sel_subj", "STAT"),
    ("sel_subj", "SCMN"),
    ("sel_subj", "SUST"),
    ("sel_subj", "THEA"),
    ("sel_subj", "UNIV"),
    ("sel_subj", "VBMS"),
    ("sel_subj", "VMED"),
    ("sel_subj", "WILD"),
    ("sel_subj", "WMST"),

    # other filters
    ("sel_day", "dummy"),
    ("sel_schd", "dummy"),
    ("sel_insm", "dummy"),
    ("sel_camp", "dummy"),
    ("sel_levl", "dummy"),
    ("sel_sess", "dummy"),

    ("sel_instr", "dummy"),
    ("sel_instr", "%"),

    ("sel_ptrm", "dummy"),
    ("sel_ptrm", "%"),

    ("sel_attr", "dummy"),
    ("sel_attr", "%"),

    # text filters
    ("sel_crse", ""),
    ("sel_title", ""),
    ("sel_from_cred", ""),
    ("sel_to_cred", ""),

    # time filters
    ("begin_hh", "0"),
    ("begin_mi", "0"),
    ("begin_ap", "a"),
    ("end_hh", "0"),
    ("end_mi", "0"),
    ("end_ap", "a"),
]

def get_classes_page():
    session = requests.Session()

    print("Visiting the form page")
    session.get(url=url, timeout=30) # visit the form page

    print("Requesting scheduling data (this may take a while)")
    response = session.post(  # request the data
    url,
    data=payload,
    timeout=200 # the request can take a long time (~50s usually)
    )

    response.raise_for_status() # will error out if the request fails

    print("Raw data successfully acquired")
    
    return response.text
    
CSV_HEADER = [
    "CRN",
    "Class Name",
    "Time Start",
    "Time End",
    "Days",
    "Date Start",
    "Date End",
    "Building",
    "Room",
]
    
def extract_relevant_rows(response_text, include_non_class_meetings=False):
    rows = [CSV_HEADER]

    soup = BeautifulSoup(response_text, "lxml")
    for title in soup.select("th.ddtitle"):  # each title corresponds to a class
        title_text = title.get_text(" ", strip=True)  # readable text

        parts = title_text.split(" - ")  # Class Title - CRN - subject course_code - section
        if len(parts) < 3:
            continue

        crn = parts[1].strip()
        class_name = parts[2].strip()  # subject course_code

        # Find the specific "Scheduled Meeting Times" table for this class.
        # Walk forward in-document, but stop at the next class title so we don't
        # accidentally grab another class's meeting table.
        meeting_table = None
        for elem in title.next_elements:
            if not isinstance(elem, Tag):
                continue

            if elem.name == "th" and "ddtitle" in (elem.get("class") or []):
                break

            if elem.name != "table":
                continue

            if "datadisplaytable" not in (elem.get("class") or []):
                continue

            cap = elem.find("caption", class_="captiontext")
            if cap and cap.get_text(" ", strip=True).strip().lower() == "scheduled meeting times":
                meeting_table = elem
                break

        if meeting_table is None:
            continue

        for row in meeting_table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue  # header rows and unexpected rows

            cell_text = [td.get_text(" ", strip=True) for td in cells]

            meeting_type = cell_text[0].strip()
            if (not include_non_class_meetings) and meeting_type.lower() != "class":
                continue

            times = parse_time(cell_text[1])
            if not times:
                continue

            start, end = times

            days_text = cell_text[2].strip()
            days = "" if (not days_text or days_text.upper() == "TBA") else days_text

            building, room = parse_location(cell_text[3])
            date_range = parse_date_range(cell_text[4])
            if not date_range:
                continue
            date_start, date_end = date_range

            rows.append(
                [
                    crn,
                    class_name,
                    start,
                    end,
                    days,
                    date_start,
                    date_end,
                    building,
                    room,
                ]
            )

    return rows
        
def parse_time(times):
    # Time data, does not have leading 0s: 9:00 am - 10:15 am
    times = times.strip()
    if not times or times.upper() == "TBA":
        return None

    parts = re.split(r"\s*-\s*", times)
    if len(parts) != 2:
        return None

    start = parts[0].strip()
    end = parts[1].strip()
    if not start or not end:
        return None

    return start, end


def parse_date_range(value):
    """Return the upstream meeting date range as two display strings."""

    value = value.strip()
    if not value or value.upper() == "TBA":
        return None

    parts = re.split(r"\s+-\s+", value, maxsplit=1)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        return None

    return parts[0].strip(), parts[1].strip()
    
def parse_location(where):    
    where = where.strip()
    if not where or where.upper() == "TBA":
        return "", ""

    match = re.match(r"^(.*)\s+(\S*\d\S*)$", where)
    if not match:
        # e.g. ONLINE / WEB / OFF CAMPUS / etc.
        return where, ""

    return match.group(1).strip(), match.group(2).strip()

if __name__ == "__main__":
    response = get_classes_page()

    soup = BeautifulSoup(response, "lxml")
    print(f"Found {len(soup.select('th.ddtitle'))} classes")

    rows = extract_relevant_rows(response)
    with open("scheduling_data.csv", "w", newline="", encoding="utf-8") as data_file:
        writer = csv.writer(data_file)
        writer.writerows(rows)

    print(f"Wrote {len(rows) - 1} meeting rows to scheduling_data.csv")
    
