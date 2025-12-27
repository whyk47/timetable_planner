from load import process_all_courses
from models import DAYS, TIMESLOTS, Course, Lesson


class PruningGrid:
    def __init__(self, all_courses: dict[str, Course]):
        self.all_courses = all_courses
        self.grid = [[set() for _ in range(TIMESLOTS)] for _ in range(DAYS)]
        for course in all_courses.values():
            for index, lessons in course.indexes.items():
                for lesson in lessons:
                    for day, start in lesson.periods:
                        slot = self.slot(day, start)
                        slot.add((course.code, index))

    def slot(self, day: int, start: int) -> set:
        if day < 1 or day > DAYS or start < 8 or start >= 8 + TIMESLOTS:
            raise ValueError("Invalid day or start time for slot retrieval.")
        return self.grid[day - 1][start - 8]

    def remove_lesson(self, course: str, index: str, lesson: Lesson) -> None:
        for day, start in lesson.periods:
            slot = self.slot(day, start)
            slot -= {(course, index)}

    def remove_index(self, course: str, index: str) -> None:
        for lesson in self.all_courses[course].indexes[index]:
            self.remove_lesson(course, index, lesson)

    def prune(self, lesson: Lesson) -> None:
        indexes = set()
        for day, start in lesson.periods:
            slot = self.slot(day, start)
            indexes |= slot
        for course, index in indexes:
            self.remove_index(course, index)

    def prune_day(self, day: int) -> None:
        for start in range(8, 8 + TIMESLOTS):
            slot = self.slot(day, start)
            for course, index in slot.copy():
                self.remove_index(course, index)

    def __str__(self):
        return str(self.grid)


if __name__ == "__main__":
    # ab1201 = process_all_courses("raw_data", ["AB1201"])
    # pg = PruningGrid(ab1201)
    # print(pg)
    # # Example usage:
    # lesson = Lesson(lesson_type="Lec", day=1, start=11, duration=3)
    # pg.prune(lesson)  # Prune slots on Monday from 10am for 2 hours
    # print(pg)

    sc2001 = process_all_courses("raw_data", ["SC2001"])
    pg2 = PruningGrid(sc2001)
    print(pg2)
    pg2.prune_day(3)  # Prune all slots on Wednesday
    print(pg2)
