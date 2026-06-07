from dataclasses import dataclass
from datetime import datetime
from .enums import ReservationStatus


@dataclass
class Reservation:
    id: str
    book_id: str
    reader_id: str
    created_at: datetime
    expires_at: datetime
    status: ReservationStatus = ReservationStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.book_id or not self.book_id.strip():
            raise ValueError("book_id cannot be empty")
        if not self.reader_id or not self.reader_id.strip():
            raise ValueError("reader_id cannot be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be strictly after created_at")
