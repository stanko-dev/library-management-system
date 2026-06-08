from dataclasses import dataclass, field


@dataclass
class Team:
    id: str
    name: str
    capacity: int
    member_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")
        if len(self.member_ids) > self.capacity:
            raise ValueError("member_ids cannot exceed capacity")

    @property
    def is_full(self) -> bool:
        return len(self.member_ids) >= self.capacity

    @property
    def available_spots(self) -> int:
        return self.capacity - len(self.member_ids)
