from dataclasses import dataclass
from datetime import datetime


@dataclass
class Submission:
    id: str
    milestone_id: str
    team_id: str
    submitted_at: datetime

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.milestone_id or not self.milestone_id.strip():
            raise ValueError("milestone_id cannot be empty")
        if not self.team_id or not self.team_id.strip():
            raise ValueError("team_id cannot be empty")
