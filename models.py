from pydantic import BaseModel

DAYS = 6  # Mon-Sat
TIMESLOTS = 11  # 0830 - 1730


class Lesson(BaseModel):
    lesson_type: str
    day: int
    start: int
    duration: int

    @property
    def end(self) -> int:
        return self.start + self.duration

    @property
    def periods(self) -> list[tuple[int, int]]:
        """Returns a list of (day, start_time) tuples for each time slot this lesson occupies."""
        return [
            (self.day, self.start + i)
            for i in range(self.duration)
            if self.start + i - 8 < TIMESLOTS
        ]


class Index(BaseModel):
    index: str
    vacancies: int = 0
    lessons: list[Lesson] = []

    @property
    def schedule(self) -> tuple:
        return tuple(
            sorted(
                (lesson.lesson_type, lesson.day, lesson.start, lesson.duration)
                for lesson in self.lessons
            )
        )

    def merge(self, other: "Index"):
        self.vacancies += other.vacancies
        self.index += f"/{other.index}"

    @property
    def vacant(self) -> bool:
        return self.vacancies > 0

    def has_physical_lesson(self, day: int) -> bool:
        for lesson in self.lessons:
            if lesson.day == day and lesson.lesson_type in {"Tut", "Lab", "Sem"}:
                return True
        return False


class Course(BaseModel):
    name: str
    code: str
    aus: int
    indexes: dict[str, Index]
    idx_map: dict[str, str] = {}

    def merge_overlapping_indexes(self):
        seen_schedules: dict[tuple, Index] = {}

        for index in self.indexes.values():
            if index.schedule in seen_schedules:
                seen_schedules[index.schedule].merge(index)
            else:
                seen_schedules[index.schedule] = index
        self.indexes = {index.index: index for index in seen_schedules.values()}
        for idx in self.indexes:
            for i in idx.split("/"):
                self.idx_map[i] = idx

    def get_index(self, index: str) -> Index:
        if index in self.indexes:
            return self.indexes[index]
        idx_key = self.idx_map[index]
        return self.indexes[idx_key]

    def get_index_key(self, index: str) -> str:
        return self.idx_map[index]


class Solution(BaseModel):
    assignment: dict[str, str]
    vacancy_shortfall: set[tuple[str, str]]
    score: tuple

    def __lt__(self, other):
        # Prioritize the index with more vacancies
        return self.score < other.score

    def __eq__(self, other):
        return self.score == other.score
