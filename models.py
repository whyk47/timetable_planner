from typing import Dict, List

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


class Course(BaseModel):
    name: str
    code: str
    aus: int
    # Maps an Index string (e.g., "10155") to its list of associated lessons
    indexes: Dict[str, List[Lesson]]
