from itertools import combinations
from typing import Dict, List, Optional

from tqdm import tqdm

from load import process_all_courses
from models import Course, Lesson


# --- CSP Solver Class ---
class TimetablePlanner:
    def __init__(self, combo_courses: List[Course]):
        self.combo_courses = combo_courses
        self.combo_solutions = []

    def overlaps(self, l1: Lesson, l2: Lesson) -> bool:
        if l1.day != l2.day:
            return False
        return l1.start < l2.end and l1.end > l2.start

    def is_clash(
        self, index_lessons: List[Lesson], current_schedule: List[Lesson]
    ) -> bool:
        for new_l in index_lessons:
            for existing_l in current_schedule:
                if self.overlaps(new_l, existing_l):
                    return True
        return False

    def get_mrv_variable(
        self, unassigned: List[Course], domains: Dict[str, List[str]]
    ) -> Course:
        return min(unassigned, key=lambda c: len(domains[c.code]))

    def forward_check(
        self,
        assigned_course: Course,
        assigned_index: str,
        unassigned: List[Course],
        domains: Dict[str, List[str]],
    ) -> Optional[Dict[str, List[str]]]:
        new_domains = {code: list(idxs) for code, idxs in domains.items()}
        assigned_lessons = assigned_course.indexes[assigned_index]

        for course in unassigned:
            pruned = [
                idx
                for idx in new_domains[course.code]
                if not self.is_clash(course.indexes[idx], assigned_lessons)
            ]
            new_domains[course.code] = pruned
            if not pruned:
                return None
        return new_domains

    def solve_all(
        self,
        unassigned: List[Course],
        domains: Dict[str, List[str]],
        current_schedule: List[Lesson],
        current_assignment: Dict[str, str],
    ):
        if not unassigned:
            self.combo_solutions.append(current_assignment.copy())
            return

        course = self.get_mrv_variable(unassigned, domains)
        remaining = [c for c in unassigned if c.code != course.code]

        for idx_id in domains[course.code]:
            pruned_domains = self.forward_check(course, idx_id, remaining, domains)
            if pruned_domains is not None:
                current_assignment[course.code] = idx_id
                self.solve_all(
                    remaining,
                    pruned_domains,
                    current_schedule + course.indexes[idx_id],
                    current_assignment,
                )
                del current_assignment[course.code]


# --- Sorting Logic ---
def get_free_days(assignment: Dict[str, str], courses: List[Course]) -> int:
    """Counts days without Tutorials, Seminars, or Labs."""
    busy_days = set()
    # Lectures are excluded from 'busy' days as they are often recorded/flexible
    mandatory = {"Tut", "Sem", "Lab", "Tutorial", "Seminar"}

    for course in courses:
        idx = assignment[course.code]
        for lesson in course.indexes[idx]:
            if any(m in lesson.lesson_type for m in mandatory):
                busy_days.add(lesson.day)
    return 7 - len(busy_days)


def stream_and_bucket_sort(all_courses: List[Course], num_modules: int):
    all_combos = list(combinations(all_courses, num_modules))
    total_solutions = 0

    # Progress bar for the combinations
    pbar = tqdm(all_combos, desc="Scanning Combinations", unit="combo")

    for combo in pbar:
        planner = TimetablePlanner(list(combo))
        initial_domains = {c.code: list(c.indexes.keys()) for c in combo}
        planner.solve_all(list(combo), initial_domains, [], {})

        if planner.combo_solutions:
            # 1. Bucket Sort the solutions for this specific combination
            buckets = [[] for _ in range(8)]
            for sol in planner.combo_solutions:
                score = get_free_days(sol, list(combo))
                buckets[score].append(sol)

            # 2. Print results from highest bucket (most free days) to lowest
            for score in range(7, -1, -1):
                if buckets[score]:
                    total_solutions += len(buckets[score])
                    # Update progress bar description
                    pbar.set_description(
                        f"Best: {score} Free Days | Total Sols: {total_solutions}"
                    )

                    # Print high-priority solutions (e.g., 3+ free days)
                    if score >= 3:
                        tqdm.write(
                            f"\n[FOUND {score} FREE DAYS] Module Set: {[c.code for c in combo]}"
                        )
                        for s in buckets[score][
                            :1
                        ]:  # Print first example in this bucket
                            tqdm.write(f" -> Assignment: {s}")

    print(f"\nSearch complete. Total valid timetables: {total_solutions}")


# --- Execution ---
if __name__ == "__main__":
    target_courses = [
        "AB1201",
        "AB1601",
        "SC2001",
        "SC2002",
        "AD1102",
        "CC0001",
        "SC1006",
    ]
    extracted_courses = process_all_courses("raw_data", target_courses=target_courses)
    stream_and_bucket_sort(list(extracted_courses.values()), 7)
