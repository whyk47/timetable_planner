import heapq
from itertools import combinations

from tqdm import tqdm

from load import process_all_courses
from models import DAYS, TIMESLOTS, Course
from pruning_grid import PruningGrid


# --- CSP Solver Logic ---
class CSPPlanner:
    def __init__(self, selected_courses: list[Course]):
        self.selected_courses = selected_courses
        self.courses_dict = {c.code: c for c in selected_courses}
        self.solutions = []

    def get_mrv_variable(self, unassigned: list[Course], grid: PruningGrid) -> Course:
        """MRV Heuristic: Pick the course with the smallest remaining domain in the grid."""

        def count_valid_indexes(course: Course):
            count = 0
            # Check how many of this course's indexes still exist in the grid
            for idx in course.indexes:
                # If any slot for this index's first lesson still contains this index, it's valid
                # (Simple check: is the index still in its own designated slots)
                first_lesson = course.indexes[idx][0]
                d, s = first_lesson.periods[0]
                if (course.code, idx) in grid.slot(d, s):
                    count += 1
            return count

        return min(unassigned, key=count_valid_indexes)

    def solve(
        self, unassigned: list[Course], grid: PruningGrid, assignment: dict[str, str]
    ):
        if not unassigned:
            self.solutions.append(assignment.copy())
            return

        # 1. Select Variable (MRV)
        course = self.get_mrv_variable(unassigned, grid)
        remaining = [c for c in unassigned if c.code != course.code]

        # 2. Get valid values (indices still in the grid)
        valid_indices = []
        for idx in course.indexes:
            d, s = course.indexes[idx][0].periods[0]
            if (course.code, idx) in grid.slot(d, s):
                valid_indices.append(idx)

        # 3. Iterate and Prune
        for idx in valid_indices:
            # We must use a fresh grid for the next branch (Deep Copy Simulation)
            # In Python, for speed, we generate a new grid from current state
            branch_grid = self.create_branch_grid(grid)

            # Remove other indices of the SAME course from the grid
            for other_idx in course.indexes:
                if other_idx != idx:
                    branch_grid.remove_index(course.code, other_idx)

            # PRUNE: Remove all indices from OTHER courses that clash with this selection
            for lesson in course.indexes[idx]:
                branch_grid.prune(lesson)

            # Assign and Recurse
            assignment[course.code] = idx
            self.solve(remaining, branch_grid, assignment)
            del assignment[course.code]

    def create_branch_grid(self, current_grid: PruningGrid) -> PruningGrid:
        """Helper to create a copy of the grid state for backtracking."""
        import copy

        new_grid = PruningGrid(self.courses_dict)
        # Manually sync the sets to match the current_grid state
        for d in range(DAYS):
            for t in range(TIMESLOTS):
                new_grid.grid[d][t] = current_grid.grid[d][t].copy()
        return new_grid


# --- Main Bucket Sort Integration ---
class Top20Tracker:
    def __init__(self, limit: int = 20):
        self.limit = limit
        self.heap = (
            []
        )  # Elements will be (free_days, streak, assignment_dict, module_list)

    def add_solution(self, score: tuple[int, ...], assignment: dict):
        # We store (free_days, streak) as the priority key.
        # Python's heapq is a min-heap, so the "smallest" of our top 20 is at the top.
        entry = (score, list(assignment.items()))

        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, entry)
        else:
            # If current solution is better than the worst in our top 20
            # (Comparisons work lexicographically: free_days first, then streak)
            if score > self.heap[0][0]:
                heapq.heapreplace(self.heap, entry)

    def get_sorted_results(self):
        # Return results sorted from best to worst
        return sorted(self.heap, key=lambda x: (x[0], x[1]), reverse=True)


def get_score(
    assignment: dict[str, str], courses_dict: dict[str, Course]
) -> tuple[int, int, int]:
    morning_lessons = 0
    busy_days = [False] * (DAYS + 1)
    mandatory = {"Tut", "Sem", "Lab"}
    for code, idx in assignment.items():
        for lesson in courses_dict[code].indexes[idx]:
            if lesson.start < 9:
                morning_lessons += 1
            if any(m in lesson.lesson_type for m in mandatory):
                busy_days[lesson.day - 1] = True
    cur_streak, max_streak = 0, 0
    for day in busy_days * 2:
        if day:
            cur_streak = 0
        else:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
    return DAYS + 1 - sum(busy_days), max_streak, -morning_lessons


def run_planner(all_courses: list[Course], num_to_select: int):
    all_combos = list(combinations(all_courses, num_to_select))
    total_solutions = 0
    top_solutions = Top20Tracker(limit=20)

    pbar = tqdm(all_combos, desc="Scanning")

    for combo in pbar:
        planner = CSPPlanner(list(combo))
        # Initial grid with only the courses in this specific combination
        for day in range(DAYS):
            grid = PruningGrid({c.code: c for c in combo})
            grid.prune_day(day + 1)
            planner.solve(list(combo), grid, {})

        if planner.solutions:
            total_solutions += len(planner.solutions)
            for sol in planner.solutions:
                score = get_score(sol, planner.courses_dict)
                top_solutions.add_solution(score, sol)
    return top_solutions.get_sorted_results()


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
    run_planner(list(extracted_courses.values()), 7)
