from models.penalty import Penalty
from storage.interfaces import PenaltyRepository


class InMemoryPenaltyRepository(PenaltyRepository):
    def __init__(self) -> None:
        self._store: dict[str, Penalty] = {}

    def add(self, penalty: Penalty) -> None:
        if penalty.id in self._store:
            raise ValueError(f"Penalty already exists: {penalty.id}")
        self._store[penalty.id] = penalty

    def get_by_id(self, penalty_id: str) -> Penalty | None:
        return self._store.get(penalty_id)

    def list_all(self) -> list[Penalty]:
        return list(self._store.values())

    def update(self, penalty: Penalty) -> None:
        if penalty.id not in self._store:
            raise KeyError(penalty.id)
        self._store[penalty.id] = penalty

    def delete(self, penalty_id: str) -> None:
        if penalty_id not in self._store:
            raise KeyError(penalty_id)
        del self._store[penalty_id]

    def find_by_student(self, student_id: str) -> list[Penalty]:
        return [p for p in self._store.values() if p.student_id == student_id]

    def find_by_milestone(self, milestone_id: str) -> list[Penalty]:
        return [p for p in self._store.values() if p.milestone_id == milestone_id]

    def find_unresolved(self) -> list[Penalty]:
        return [p for p in self._store.values() if not p.is_resolved]

    def find_unresolved_by_student(self, student_id: str) -> list[Penalty]:
        return [p for p in self._store.values()
                if p.student_id == student_id and not p.is_resolved]

    def total_unresolved_by_student(self, student_id: str) -> int:
        return sum(p.points for p in self.find_unresolved_by_student(student_id))
