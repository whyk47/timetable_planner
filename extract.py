import re
from typing import Dict, List

from bs4 import BeautifulSoup

from models import Course, Lesson


# --- Extraction Function ---
def extract_entire_course(course_code: str) -> Course:
    file_path = f"raw_data/Content of Course_ {course_code}.html"
    day_map = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}

    with open(file_path, "r", encoding="windows-1252", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

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


if __name__ == "__main__":
    # Example execution for SC2002
    course_model = extract_entire_course("SC2002")

    # Print as validated JSON
    print(course_model.model_dump_json(indent=2))
