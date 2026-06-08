from models.queue_request import QueueRequest
from models.enums import QueueRequestStatus
from storage.interfaces import QueueRequestRepository


class InMemoryQueueRequestRepository(QueueRequestRepository):
    def __init__(self) -> None:
        self._store: dict[str, QueueRequest] = {}

    def add(self, request: QueueRequest) -> None:
        if request.id in self._store:
            raise ValueError(f"QueueRequest already exists: {request.id}")
        self._store[request.id] = request

    def get_by_id(self, request_id: str) -> QueueRequest | None:
        return self._store.get(request_id)

    def list_all(self) -> list[QueueRequest]:
        return list(self._store.values())

    def update(self, request: QueueRequest) -> None:
        if request.id not in self._store:
            raise KeyError(request.id)
        self._store[request.id] = request

    def delete(self, request_id: str) -> None:
        if request_id not in self._store:
            raise KeyError(request_id)
        del self._store[request_id]

    def find_by_student(self, student_id: str) -> list[QueueRequest]:
        return [r for r in self._store.values() if r.student_id == student_id]

    def find_by_team(self, team_id: str) -> list[QueueRequest]:
        return [r for r in self._store.values() if r.team_id == team_id]

    def find_pending(self) -> list[QueueRequest]:
        return [r for r in self._store.values()
                if r.status == QueueRequestStatus.PENDING]

    def find_pending_by_team(self, team_id: str) -> list[QueueRequest]:
        return [r for r in self._store.values()
                if r.team_id == team_id and r.status == QueueRequestStatus.PENDING]
