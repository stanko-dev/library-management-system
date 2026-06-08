from dataclasses import dataclass
from datetime import datetime
from .enums import QueueRequestStatus


@dataclass
class QueueRequest:
    id: str
    student_id: str
    team_id: str
    created_at: datetime
    expires_at: datetime
    status: QueueRequestStatus = QueueRequestStatus.PENDING

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.student_id or not self.student_id.strip():
            raise ValueError("student_id cannot be empty")
        if not self.team_id or not self.team_id.strip():
            raise ValueError("team_id cannot be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be strictly after created_at")
