from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from tqdm import tqdm

from models import DAYS, Course
from pruning_grid import PruningGrid, PruningList
from solution_heap import HeapEntry, SolutionHeap


@dataclass
class Planner:
    all_courses: dict[str, Course]
    target_num: int
    assigned_indexes: dict[str, str] = field(default_factory=dict)
    pruned_indexes: PruningList = field(default_factory=lambda: defaultdict(set))
    unassigned_courses: set[str] = field(init=False)
    pruning_grid: PruningGrid = field(init=False)
    solution_heap: SolutionHeap = field(init=False)

    def __post_init__(self):
        for course_code, index in self.assigned_indexes.items():
            index_keys = self.all_courses[course_code].indexes.keys()
            if index not in index_keys:
                for k in index_keys:
                    if index in k:
                        self.assigned_indexes[course_code] = k
                        break

        self.unassigned_courses = set(
            c for c in self.all_courses if c not in self.assigned_indexes
        )
        # prune indexes which clash with assigned indexes
        self.pruning_grid = PruningGrid.construct(self.all_courses)
        for course_code, index in self.assigned_indexes.items():
            clashing = self.pruning_grid.clashing_indexes(
                self.all_courses[course_code].indexes[index]
            )
            self.add_new_pruned(clashing)
        self.solution_heap = SolutionHeap(self.all_courses)

    def mrv(self, combo: set[str]) -> str:
        mrv, min_remaining = "", float("inf")
        for course_code in self.unassigned_courses & combo:
            num_indexes = len(self.all_courses[course_code].indexes)
            num_pruned = len(self.pruned_indexes[course_code])
            if num_indexes - num_pruned < min_remaining:
                min_remaining = num_indexes - num_pruned
                mrv = course_code
        return mrv

    def add_new_pruned(self, clashing: PruningList) -> PruningList:
        new_pruned = {idx: clashing[idx] - self.pruned_indexes[idx] for idx in clashing}
        for idx in new_pruned:
            self.pruned_indexes[idx] |= new_pruned[idx]
        return new_pruned

    def remove_pruned(self, new_pruned: PruningList):
        for idx in new_pruned:
            self.pruned_indexes[idx] -= new_pruned[idx]

    def solve(self, combo: set[str]):
        if len(self.assigned_indexes) == self.target_num:
            self.solution_heap.add_assignment(self.assigned_indexes.copy())
            return
        course_code = self.mrv(combo)
        course_indexes = self.all_courses[course_code].indexes
        valid_indexes = set(course_indexes.keys()) - self.pruned_indexes[course_code]
        self.unassigned_courses.remove(course_code)
        for index in valid_indexes:
            clashing = self.pruning_grid.clashing_indexes(course_indexes[index])
            new_pruned = self.add_new_pruned(clashing)
            self.assigned_indexes[course_code] = index
            self.solve(combo)
            del self.assigned_indexes[course_code]
            self.remove_pruned(new_pruned)
        self.unassigned_courses.add(course_code)

    def run_planner(self) -> list[HeapEntry]:
        all_combos = tuple(
            combinations(
                self.unassigned_courses, self.target_num - len(self.assigned_indexes)
            )
        )

        pbar = tqdm(all_combos, desc="Scanning")

        for combo in pbar:
            for day in range(DAYS):
                clashing = self.pruning_grid.prune_day(day + 1)
                new_pruned = self.add_new_pruned(clashing)
                self.solve(set(combo))
                self.remove_pruned(new_pruned)
        return self.solution_heap.get_sorted_results()


if __name__ == "__main__":
    from load import process_all_courses
    from ui import TimetableGUI

    extracted_courses = process_all_courses("raw_data")
    assigned_indexes = {
        "AB1201": "00182",
        "AB1601": "00871",
        "AD1102": "00109",
    }
    planner = Planner(
        extracted_courses, target_num=7, assigned_indexes=assigned_indexes
    )
    solutions = planner.run_planner()

    if solutions:
        TimetableGUI(solutions, extracted_courses)
    else:
        print("No solutions found.")
