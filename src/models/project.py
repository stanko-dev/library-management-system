from dataclasses import dataclass
from datetime import datetime
from .enums import ProjectStatus


@dataclass
class Project:
    id: str
    title: str
    description: str
    status: ProjectStatus = ProjectStatus.DRAFT
    team_id: str | None = None
    created_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")
        if self.created_at is None:
            self.created_at = datetime.now()
