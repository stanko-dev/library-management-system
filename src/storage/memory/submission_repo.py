from models.submission import Submission
from storage.interfaces import SubmissionRepository


class InMemorySubmissionRepository(SubmissionRepository):
    def __init__(self) -> None:
        self._store: dict[str, Submission] = {}

    def add(self, submission: Submission) -> None:
        if submission.id in self._store:
            raise ValueError(f"Submission already exists: {submission.id}")
        self._store[submission.id] = submission

    def get_by_id(self, submission_id: str) -> Submission | None:
        return self._store.get(submission_id)

    def list_all(self) -> list[Submission]:
        return list(self._store.values())

    def update(self, submission: Submission) -> None:
        if submission.id not in self._store:
            raise KeyError(submission.id)
        self._store[submission.id] = submission

    def delete(self, submission_id: str) -> None:
        if submission_id not in self._store:
            raise KeyError(submission_id)
        del self._store[submission_id]

    def find_by_milestone(self, milestone_id: str) -> list[Submission]:
        return [s for s in self._store.values() if s.milestone_id == milestone_id]

    def find_by_team(self, team_id: str) -> list[Submission]:
        return [s for s in self._store.values() if s.team_id == team_id]
