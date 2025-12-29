import heapq
from dataclasses import dataclass, field

from models import DAYS, Course


@dataclass
class SolutionHeap:
    all_courses: dict[str, Course]
    limit: int = 50
    heap: list[tuple[tuple[int, ...], tuple[tuple[str, str], ...]]] = field(
        default_factory=list
    )

    def get_score(self, assignment: dict[str, str]) -> tuple[int, int, int]:
        morning_lessons, busy_days = 0, [False] * (DAYS + 1)
        mandatory = {"Tut", "Sem", "Lab"}
        for code, idx in assignment.items():
            for lesson in self.all_courses[code].indexes[idx]:
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
        return DAYS + 1 - sum(busy_days), max_streak, -morning_lessons

    def add_solution(self, assignment: dict[str, str]):
        score = self.get_score(assignment)
        entry = (score, tuple(assignment.items()))

        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, entry)
        else:
            if score > self.heap[0][0]:
                heapq.heapreplace(self.heap, entry)

    def get_sorted_results(self):
        return sorted(self.heap, key=lambda x: x[0], reverse=True)
