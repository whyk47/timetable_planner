from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from itertools import combinations

from tqdm import tqdm

from models import DAYS, Course, Solution
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
        # for course_code, index in self.assigned_indexes.items():
        #     index_keys = self.all_courses[course_code].indexes.keys()
        #     if index not in index_keys:
        #         for k in index_keys:
        #             if index in k:
        #                 self.assigned_indexes[course_code] = k
        #                 break

        self.unassigned_courses = set(
            c for c in self.all_courses  # if c not in self.assigned_indexes
        )
        # prune indexes which clash with assigned indexes
        self.pruning_grid = PruningGrid.construct(self.all_courses)
        for course_code, index in self.assigned_indexes.items():
            self.all_courses[course_code].get_index(index).vacancies += 1

        self.assigned_indexes = {}

        # clashing = self.pruning_grid.clashing_indexes(
        #     self.all_courses[course_code].indexes[index]
        # )
        # self.pruned_indexes = PruningGrid.add_new_pruned(
        #     clashing, self.pruned_indexes
        # )
        self.solution_heap = SolutionHeap(self.all_courses, self.assigned_indexes)

    def mrv(
        self, combo: set[str], unassigned_courses: set[str], pruned_indexes: PruningList
    ) -> str:
        mrv, min_remaining = "", float("inf")
        for course_code in unassigned_courses & combo:
            num_indexes = len(self.all_courses[course_code].indexes)
            num_pruned = len(pruned_indexes[course_code])
            if num_indexes - num_pruned < min_remaining:
                min_remaining = num_indexes - num_pruned
                mrv = course_code
        return mrv

    def solve(
        self,
        combo: set[str],
        assigned_indexes: dict[str, str],
        unassigned_courses: set[str],
        pruned_indexes: PruningList,
        solution_heap: SolutionHeap,
    ):
        if len(assigned_indexes) == self.target_num:
            solution_heap.add_assignment(assigned_indexes.copy())
            return
        course_code = self.mrv(combo, unassigned_courses, pruned_indexes)
        course_indexes = self.all_courses[course_code].indexes
        valid_indexes = set(course_indexes.keys()) - pruned_indexes[course_code]
        unassigned_courses.remove(course_code)
        for index in valid_indexes:
            clashing = self.pruning_grid.clashing_indexes(course_indexes[index])
            new_pruned = self.pruning_grid.get_new_pruned(clashing, pruned_indexes)
            pruned_indexes = self.pruning_grid.add_new_pruned(
                new_pruned, pruned_indexes
            )
            assigned_indexes[course_code] = index
            self.solve(
                combo,
                assigned_indexes,
                unassigned_courses,
                pruned_indexes,
                solution_heap,
            )
            del assigned_indexes[course_code]
            pruned_indexes = self.pruning_grid.remove_new_pruned(
                new_pruned, pruned_indexes
            )
        unassigned_courses.add(course_code)

    def worker_task(self, combo: set[str], limit: int) -> list[Solution]:
        """
        Standalone function to handle a single combination.
        This runs in a separate process.
        """
        local_solutions = SolutionHeap(
            self.all_courses, self.assigned_indexes, limit=limit
        )

        for day in range(DAYS - 3):
            clashing = self.pruning_grid.prune_day(day + 1)
            new_pruned = self.pruning_grid.get_new_pruned(clashing, self.pruned_indexes)
            pruned = self.pruning_grid.add_new_pruned(
                new_pruned, self.pruned_indexes.copy()
            )
            self.solve(
                combo,
                self.assigned_indexes.copy(),
                self.unassigned_courses.copy(),
                pruned,
                local_solutions,
            )
            pruned = self.pruning_grid.remove_new_pruned(new_pruned, pruned)
        return local_solutions.get_sorted_results()

    def run_planner(self) -> list[Solution]:
        all_combos = tuple(
            combinations(
                self.unassigned_courses, self.target_num - len(self.assigned_indexes)
            )
        )
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(
                    self.worker_task, set(combo), max(10, 50 // len(all_combos))
                ): combo
                for combo in all_combos
            }
            for future in tqdm(
                as_completed(futures), total=len(all_combos), desc="Parallel Scanning"
            ):
                try:
                    found_sols = future.result()
                    for sol in found_sols:
                        self.solution_heap.add_solution(sol)
                except Exception as exc:
                    print(f"Combination generated an exception: {exc}")
        return self.solution_heap.get_sorted_results()


if __name__ == "__main__":
    from extract import Parser
    from ui import TimetableGUI

    target_courses = [
        "AB1201",
        "AB1601",
        "AD1102",
        "CC0001",
        "SC1006",
        "SC2001",
        "SC2002",
        "SC2203",
        "SC2006",
        "SC2008",
    ]
    parser = Parser("mods")
    parser.process_all_courses(target_courses)
    assigned_indexes = {
        "SC2002": "10171",
        "SC2001": "10254",
        "AB1201": "00182",
        "AB1601": "00871",
        "AD1102": "00109",
    }
    planner = Planner(parser.courses, target_num=7, assigned_indexes=assigned_indexes)
    solutions = planner.run_planner()
    if solutions:
        TimetableGUI(solutions, parser.courses)
    else:
        print("No solutions found.")
