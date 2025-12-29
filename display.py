from typing import Dict, List

from tabulate import tabulate

from models import Course


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
