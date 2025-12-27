import json
import os
import re
from typing import List

from extract import extract_entire_course
from models import Course

# Assuming the previous code (Models and extract_entire_course)
# is in the same file or imported


def merge_overlapping_indexes(course: Course) -> Course:
    """Merges indexes with identical lesson schedules for CC courses.
    The identical indexes must be consecutive.
    """
    seen_schedules = {}

    for index, lessons in course.indexes.items():
        # Create a unique key based on the lessons' schedule
        schedule_key = tuple(
            sorted(
                (lesson.lesson_type, lesson.day, lesson.start, lesson.duration)
                for lesson in lessons
            )
        )

        if schedule_key in seen_schedules:
            # Merge indexes by appending the new index to the existing one
            existing = seen_schedules[schedule_key]
            seen_schedules[schedule_key] += f"/{index}"
        else:
            seen_schedules[schedule_key] = index

    # Convert merged indexes back to the required format
    merged_indexes = {}
    for index in seen_schedules.values():
        lessons = course.indexes[
            index.split("/")[0]
        ]  # Get lessons from the first index
        merged_indexes[index] = lessons

    return Course(
        name=course.name,
        code=course.code,
        aus=course.aus,
        indexes=merged_indexes,
    )


def process_all_courses(
    folder_path: str, target_courses: List[str] = []
) -> dict[str, Course]:
    all_courses = {}

    # Ensure the folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' not found.")
        return {}

    # Get all .html files in the directory
    files = [f for f in os.listdir(folder_path) if f.endswith(".html")]
    print(f"Found {len(files)} course files. Starting extraction...")

    for file_name in files:
        # Extract the course code from the filename
        # (Assuming format: "Content of Course_ SC2002.html")
        match = re.search(r"Course_ (.*?)\.html", file_name)
        if not match:
            continue

        course_code = match.group(1)
        if target_courses and course_code not in target_courses:
            continue

        try:
            course_model = extract_entire_course(course_code)
            course_model = merge_overlapping_indexes(course_model)
            all_courses[course_code] = course_model
            print(f"Successfully extracted: {course_code}")
        except Exception as e:
            print(f"Failed to extract {course_code}: {e}")

    return all_courses


if __name__ == "__main__":
    folder = "raw_data"
    extracted_data = process_all_courses(folder)

    # Save the combined data to a single JSON file
    output_file = "all_courses_data.json"

    # We use model_dump to convert the list of Pydantic objects to a list of dicts
    json_output = {
        course.code: course.model_dump() for course in extracted_data.values()
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)

    print(
        f"\nExtraction complete. Data for {len(extracted_data)} courses saved to {output_file}"
    )
