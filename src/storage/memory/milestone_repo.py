from datetime import datetime

from models.milestone import Milestone
from models.enums import MilestoneStatus
from storage.interfaces import MilestoneRepository


class InMemoryMilestoneRepository(MilestoneRepository):
    def __init__(self) -> None:
        self._store: dict[str, Milestone] = {}

    def add(self, milestone: Milestone) -> None:
        if milestone.id in self._store:
            raise ValueError(f"Milestone already exists: {milestone.id}")
        self._store[milestone.id] = milestone

    def get_by_id(self, milestone_id: str) -> Milestone | None:
        return self._store.get(milestone_id)

    def list_all(self) -> list[Milestone]:
        return list(self._store.values())

    def update(self, milestone: Milestone) -> None:
        if milestone.id not in self._store:
            raise KeyError(milestone.id)
        self._store[milestone.id] = milestone

    def delete(self, milestone_id: str) -> None:
        if milestone_id not in self._store:
            raise KeyError(milestone_id)
        del self._store[milestone_id]

    def find_by_project(self, project_id: str) -> list[Milestone]:
        return [m for m in self._store.values() if m.project_id == project_id]

    def find_pending(self) -> list[Milestone]:
        return [m for m in self._store.values()
                if m.status == MilestoneStatus.PENDING]

    def find_overdue(self, as_of: datetime) -> list[Milestone]:
        return [m for m in self._store.values()
                if m.status == MilestoneStatus.PENDING and m.due_date < as_of]
