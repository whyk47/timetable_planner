import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from models import Course, Index, Lesson


@dataclass
class Parser:
    folder_path: str
    vacancies: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    courses: dict[str, Course] = field(default_factory=dict)

    def extract_vacancy_data(self):
        with open(
            f"{self.folder_path}/stars.html",
            "r",
            encoding="windows-1252",
            errors="ignore",
        ) as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            select_tag = row.find("select", attrs={"name": "index_nmbr"})
            if not select_tag:
                continue
            course_font = row.find("font", attrs={"size": "-1"})
            if not course_font:
                continue
            course_code = course_font.get_text(strip=True)  # e.g., 'AB1201'
            if len(course_code) != 6:
                continue

            options = select_tag.find_all("option")
            for option in options:
                text = option.get_text(strip=True)
                match = re.search(r"(\d{5})\s*/\s*(\d+)\s*/\s*(\d+)", text)
                if match:
                    index, vacancy = (match.group(1), int(match.group(2)))
                    self.vacancies[course_code][index] = vacancy

    def get_vacancies(self, course: str, index: str) -> int:
        vacancy = 10
        if course in self.vacancies:
            vacancy = self.vacancies[course].get(index, 0)
        return vacancy

    def extract_course(self, course_code: str):
        day_map = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}

        with open(
            f"{self.folder_path}/{course_code}.html",
            "r",
            encoding="windows-1252",
            errors="ignore",
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

        indexes_data: dict[str, Index] = {}
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
                vacancy = self.get_vacancies(course_code, current_index)
                indexes_data[current_index] = Index(
                    index=current_index, vacancies=vacancy
                )

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
                    indexes_data[current_index].lessons.append(lesson)
                except (ValueError, IndexError):
                    continue

        self.courses[course_code] = Course(
            name=name, code=code, aus=aus, indexes=indexes_data
        )

    def process_all_courses(self, target_courses: list[str] = []):
        if not os.path.exists(self.folder_path):
            print(f"Error: Folder '{self.folder_path}' not found.")
            return {}
        self.extract_vacancy_data()
        files = [f for f in os.listdir(self.folder_path) if f.endswith(".html")]
        print(f"Found {len(files)} course files. Starting extraction...")

        for file_name in files:
            match = re.search(r"([A-Z]{2}\d{4})\.html", file_name)
            if not match:
                continue

            course_code = match.group(1)
            if target_courses and course_code not in target_courses:
                continue

            try:
                self.extract_course(course_code)
                print(f"Successfully extracted: {course_code}")
            except Exception as e:
                print(f"Failed to extract {course_code}: {e}")
        for course in self.courses.values():
            course.merge_overlapping_indexes()


if __name__ == "__main__":
    parser = Parser("mods")
    parser.process_all_courses()
    for c in parser.courses.values():
        print(c)
