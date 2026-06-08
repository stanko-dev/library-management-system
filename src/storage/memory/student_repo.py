from models.student import Student
from storage.interfaces import StudentRepository


class InMemoryStudentRepository(StudentRepository):
    def __init__(self) -> None:
        self._store: dict[str, Student] = {}

    def add(self, student: Student) -> None:
        if student.id in self._store:
            raise ValueError(f"Student already exists: {student.id}")
        self._store[student.id] = student

    def get_by_id(self, student_id: str) -> Student | None:
        return self._store.get(student_id)

    def list_all(self) -> list[Student]:
        return list(self._store.values())

    def update(self, student: Student) -> None:
        if student.id not in self._store:
            raise KeyError(student.id)
        self._store[student.id] = student

    def delete(self, student_id: str) -> None:
        if student_id not in self._store:
            raise KeyError(student_id)
        del self._store[student_id]

    def find_by_name(self, name: str) -> list[Student]:
        needle = name.lower()
        return [s for s in self._store.values() if needle in s.name.lower()]

    def find_active(self) -> list[Student]:
        return [s for s in self._store.values() if not s.is_blocked]

    def find_blocked(self) -> list[Student]:
        return [s for s in self._store.values() if s.is_blocked]
