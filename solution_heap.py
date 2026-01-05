import heapq
from dataclasses import dataclass, field

from models import DAYS, Course, Solution

type Score = tuple[int, ...]  # (free_days, max_streak, -morning_lessons)
type Assignment = tuple[tuple[str, str], ...]  # ((course_code, index), ...)
type HeapEntry = tuple[Score, Assignment]


@dataclass
class SolutionHeap:
    all_courses: dict[str, Course]
    assigned_indexes: dict[str, str]
    limit: int = 50
    heap: list[Solution] = field(default_factory=list)

    def get_solution(self, assignment: dict[str, str]) -> Solution:
        morning_lessons, busy_days = 0, [False] * (DAYS + 1)
        mandatory = {"Tut", "Sem", "Lab"}
        vacancy_shortfall = set()
        for code, idx in assignment.items():
            if (
                code not in self.assigned_indexes
                and not self.all_courses[code].get_index(idx).vacant
            ):
                vacancy_shortfall.add((code, idx))
            for lesson in self.all_courses[code].get_index(idx).lessons:
                if any(m in lesson.lesson_type for m in mandatory):
                    busy_days[lesson.day - 1] = True
                    if lesson.start < 9:
                        morning_lessons += 2
                    elif lesson.start < 10:
                        morning_lessons += 1
        cur_streak, max_streak = 0, 0
        for day in busy_days * 2:
            if day:
                cur_streak = 0
            else:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
        aus = sum(self.all_courses[code].aus for code in assignment)
        score = (
            -len(vacancy_shortfall),
            DAYS + 1 - sum(busy_days),
            max_streak,
            -morning_lessons,
            aus,
        )
        return Solution(
            assignment=assignment, vacancy_shortfall=vacancy_shortfall, score=score
        )

    def add_assignment(self, assignment: dict[str, str]):
        solution = self.get_solution(assignment)
        self.add_solution(solution)

    def add_solution(self, solution: Solution):
        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, solution)
        else:
            if solution > self.heap[0]:
                heapq.heapreplace(self.heap, solution)

    def get_sorted_results(self) -> list[Solution]:
        return sorted(self.heap, reverse=True)
