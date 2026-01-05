from collections import defaultdict
from dataclasses import dataclass

from models import DAYS, TIMESLOTS, Course, Index, Lesson

type PruningList = defaultdict[str, set[str]] | dict[str, set[str]]


@dataclass
class PruningGrid:
    all_courses: dict[str, Course]
    # 2D grid of sets of (course_code, index)
    grid: tuple[tuple[frozenset[tuple[str, str]]]]

    @classmethod
    def construct(cls, all_courses: dict[str, Course]) -> "PruningGrid":
        grid = [[[] for slot in range(TIMESLOTS)] for day in range(DAYS)]
        for code, course in all_courses.items():
            for idx, index in course.indexes.items():
                for lesson in index.lessons:
                    for day, start in lesson.periods:
                        slot = grid[day - 1][start - 8]
                        slot.append((code, idx))
        frozen_grid = tuple(tuple(frozenset(slot) for slot in day) for day in grid)
        return cls(all_courses, frozen_grid)  # type: ignore

    def slot(self, day: int, start: int) -> frozenset:
        if day < 1 or day > DAYS or start < 8 or start >= 8 + TIMESLOTS:
            raise ValueError("Invalid day or start time for slot retrieval.")
        return self.grid[day - 1][start - 8]

    def clashing_indexes(self, index: Index) -> PruningList:

        indexes = defaultdict(set)
        for lesson in index.lessons:
            for day, start in lesson.periods:
                slot = self.slot(day, start)
                for code, index in slot:
                    indexes[code].add(index)
        return indexes

    def prune_day(self, day: int) -> PruningList:
        indexes = defaultdict(set)
        for start in range(8, 8 + TIMESLOTS):
            slot = self.slot(day, start)
            for code, index in slot:
                indexes[code].add(index)
        return indexes

    @staticmethod
    def get_new_pruned(
        clashing: PruningList, pruned_indexes: PruningList
    ) -> PruningList:
        new_pruned = {idx: clashing[idx] - pruned_indexes[idx] for idx in clashing}
        return new_pruned

    @staticmethod
    def add_new_pruned(
        new_pruned: PruningList, pruned_indexes: PruningList
    ) -> PruningList:
        for idx in new_pruned:
            pruned_indexes[idx] |= new_pruned[idx]
        return pruned_indexes

    @staticmethod
    def remove_new_pruned(
        new_pruned: PruningList, pruned_indexes: PruningList
    ) -> PruningList:
        for idx in new_pruned:
            pruned_indexes[idx] -= new_pruned[idx]
        return pruned_indexes


if __name__ == "__main__":
    from extract import Parser

    parser = Parser("mods")
    parser.process_all_courses(["SC2001"])
    lesson = Lesson(lesson_type="Lec", day=3, start=10, duration=2)
    print(parser.courses["SC2001"].indexes)
    pg = PruningGrid.construct(parser.courses)
    print(pg.prune_day(3))
