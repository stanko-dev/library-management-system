from dataclasses import dataclass
from .enums import StudentRole


@dataclass
class Student:
    id: str
    name: str
    role: StudentRole
    is_blocked: bool = False
    active_projects_count: int = 0
    missed_deadlines_count: int = 0

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.active_projects_count < 0:
            raise ValueError("active_projects_count cannot be negative")
        if self.missed_deadlines_count < 0:
            raise ValueError("missed_deadlines_count cannot be negative")
