from dataclasses import dataclass


@dataclass
class Penalty:
    id: str
    student_id: str
    milestone_id: str
    points: int
    is_resolved: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.student_id or not self.student_id.strip():
            raise ValueError("student_id cannot be empty")
        if not self.milestone_id or not self.milestone_id.strip():
            raise ValueError("milestone_id cannot be empty")
        if self.points <= 0:
            raise ValueError(f"points must be positive (got {self.points})")
