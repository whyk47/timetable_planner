import re
from collections import defaultdict
from typing import Dict, List

from bs4 import BeautifulSoup

from models import Course, Lesson


# --- Extraction Function ---
def extract_entire_course(course_code: str) -> Course:
    day_map = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}

    with open(
        f"mods/{course_code}.html", "r", encoding="windows-1252", errors="ignore"
    ) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # 1. Extract Metadata using [+] anchor
    anchor = soup.find(string=re.compile(r"\[\+\]"))
    if not anchor:
        raise ValueError(f"Could not find metadata anchor [+] for {course_code}")

    meta_row = anchor.find_parent("tr")
    meta_cells = meta_row.find_all("td")

    code = meta_cells[0].get_text(strip=True).replace("[+]", "").strip()
    name = meta_cells[1].get_text(strip=True)

    au_text = meta_cells[2].get_text(strip=True)
    au_match = re.search(r"[\d]+", au_text)
    aus = int(au_match.group()) if au_match else 0

    # 2. Locate Schedule Table (the next table after the header metadata table)
    schedule_table = meta_row.find_parent("table").find_next("table")
    rows = schedule_table.find_all("tr")[1:]  # Skip "INDEX TYPE..." header row

    indexes_data: Dict[str, List[Lesson]] = {}
    current_index = ""

    for row in rows:
        cells = row.find_all("td")
        clean_cells = [c.get_text(strip=True).replace("\xa0", "") for c in cells]

        if len(clean_cells) < 5 or clean_cells[0] == "INDEX":
            continue

        # Carry forward the index if the cell is empty
        if clean_cells[0]:
            current_index = clean_cells[0]

        if current_index not in indexes_data:
            indexes_data[current_index] = []

        # Process Time (e.g., '1130to1220')
        time_str = clean_cells[4]
        if "to" in time_str:
            try:
                start_part, end_part = time_str.split("to")
                sh, sm = int(start_part[:2]), int(start_part[2:])
                eh, em = int(end_part[:2]), int(end_part[2:])

                # Duration logic: (End Total Minutes - Start Total Minutes) / 60
                duration_hrs = int(round(((eh * 60 + em) - (sh * 60 + sm)) / 60))

                lesson = Lesson(
                    lesson_type=clean_cells[1],
                    day=day_map.get(clean_cells[3], 0),
                    start=sh,
                    duration=duration_hrs,
                )
                indexes_data[current_index].append(lesson)
            except (ValueError, IndexError):
                continue

    # 3. Return validated Course model
    return Course(name=name, code=code, aus=aus, indexes=indexes_data)


def extract_vacancy_data() -> dict[str, dict[str, tuple[int, int]]]:
    with open("mods/stars.html", "r", encoding="windows-1252", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    vacancies = defaultdict(dict)

    # Target rows that contain an index selection dropdown
    # This prevents picking up header or legend rows
    rows = soup.find_all("tr")

    for row in rows:
        # 1. Find the index dropdown in the current row
        select_tag = row.find("select", attrs={"name": "index_nmbr"})
        if not select_tag:
            continue

        # 2. Find the Course Code in the same row
        # It is located in a <font size="-1"> tag as specified
        course_font = row.find("font", attrs={"size": "-1"})
        if not course_font:
            continue

        course_code = course_font.get_text(strip=True)  # e.g., 'AB1201'
        if len(course_code) != 6:
            continue

        # 3. Extract all options from the dropdown
        options = select_tag.find_all("option")
        for option in options:
            text = option.get_text(strip=True)

            # Regex to capture: Index / Vacancy / Wait
            # Example text: "00160 / 0 / 0 "
            match = re.search(r"(\d{5})\s*/\s*(\d+)\s*/\s*(\d+)", text)

            if match:
                index, vacancy, wait = (
                    match.group(1),
                    int(match.group(2)),
                    int(match.group(3)),
                )
                vacancies[course_code][index] = (vacancy, wait)
    return vacancies


if __name__ == "__main__":
    course_model = extract_entire_course("SC2000")
    print(course_model.model_dump_json(indent=2))

    data = extract_vacancy_data()
    print(data)
