from dataclasses import dataclass
from .enums import MembershipType


@dataclass
class Reader:
    id: str
    name: str
    membership: MembershipType
    is_blocked: bool = False
    active_loans: int = 0
    overdue_count: int = 0

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.active_loans < 0:
            raise ValueError("active_loans cannot be negative")
        if self.overdue_count < 0:
            raise ValueError("overdue_count cannot be negative")
