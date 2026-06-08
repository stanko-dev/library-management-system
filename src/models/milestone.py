from dataclasses import dataclass
from datetime import datetime
from .enums import MilestoneStatus


@dataclass
class Milestone:
    id: str
    project_id: str
    title: str
    due_date: datetime
    status: MilestoneStatus = MilestoneStatus.PENDING
    submitted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.project_id or not self.project_id.strip():
            raise ValueError("project_id cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")
