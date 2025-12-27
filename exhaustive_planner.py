from itertools import combinations
from typing import Dict, List, Optional

from tqdm import tqdm  # Standard progress bar library

from display import display_timetable
from load import process_all_courses
from models import Course, Lesson


# --- CSP Solver Class ---
class TimetablePlanner:
    def __init__(self):
        self.all_solutions = []

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
            self.all_solutions.append(current_assignment.copy())
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


# ... (Include your Lesson and Course Models here) ...


def stream_with_tqdm(all_courses: List[Course], num_modules: int):
    # 1. Generate combinations
    all_combos = list(combinations(all_courses, num_modules))
    total_combos = len(all_combos)
    total_solutions = 0
    results = []

    print(f"Searching for {num_modules} modules across {total_combos} combinations...")

    # 2. Wrap the iterator with tqdm
    # 'desc' updates the text on the left, 'unit' labels the iterations
    progress_bar = tqdm(all_combos, desc="Planning", unit="combo", leave=True)

    for combo in progress_bar:
        planner = TimetablePlanner()
        initial_domains = {c.code: list(c.indexes.keys()) for c in combo}

        planner.solve_all(list(combo), initial_domains, [], {})

        if planner.all_solutions:
            total_solutions += len(planner.all_solutions)
            results.extend(planner.all_solutions)

        # 3. Update the description dynamically with the solution count
        progress_bar.set_description(f"Solutions: {total_solutions}")

    print(f"\nSearch Complete. {total_solutions} valid timetables found.")
    return results


target_courses = ["AB1201", "AB1601", "SC2001", "SC2002", "AD1102", "CC0001", "SC1006"]
all_courses = process_all_courses("raw_data", target_courses=target_courses)
num_modules = 7
all_results = stream_with_tqdm(all_courses, num_modules)
display_timetable(all_courses, all_results[0])
