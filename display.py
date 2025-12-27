from typing import Dict, List

from tabulate import tabulate

from load import process_all_courses
from models import Course
from planner import run_planner


def display_timetable(course_list: List[Course], assigned_indexes: Dict[str, str]):
    """
    Displays a weekly grid.
    assigned_indexes: { "SC2002": "10155", "AB1201": "00160", ... }
    """
    # Days and Time slots (8am to 10pm)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    time_slots = range(8, 22)  # 8 AM to 9 PM (starts)

    # Initialize the grid: Rows = Time, Cols = Days
    # Structure: { 8: ["", "", ...], 9: ["", "", ...], ... }
    grid = {t: [""] * 7 for t in time_slots}

    # Fill the grid with assignment data
    for course in course_list:
        if course.code in assigned_indexes:
            idx_id = assigned_indexes[course.code]
            lessons = course.indexes[idx_id]

            for lesson in lessons:
                d_idx = lesson.day - 1  # 1-7 to 0-6 index
                # Fill all slots occupied by the duration
                for hour in range(lesson.start, lesson.start + lesson.duration):
                    if hour in grid:
                        # Append course code and type (e.g., SC2002-Lec)
                        grid[hour][d_idx] = f"{course.code}\n({lesson.lesson_type})"

    # Prepare data for tabulate
    table_data = []
    for hour in time_slots:
        row = [f"{hour:02d}30"] + grid[hour]
        table_data.append(row)

    headers = ["Time"] + days
    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="center"))


# --- Integration with your CSP Solver ---
if __name__ == "__main__":
    # 1. Run your solver
    target_courses = [
        "AB1201",
        "AB1601",
        "SC2001",
        "SC2002",
        "AD1102",
        "CC0001",
        "SC1006",
        "SC2203",
        "AB2008",
    ]
    all_courses = process_all_courses("raw_data", target_courses=target_courses)
    target_num = 7
    result = run_planner(list(all_courses.values()), target_num)

    # 2. If successful, display:
    if result:
        for r in result:
            print(r)
            display_timetable(list(all_courses.values()), {k: v for k, v in r[2]})
