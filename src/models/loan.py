from dataclasses import dataclass
from datetime import datetime


@dataclass
class Loan:
    id: str
    book_id: str
    reader_id: str
    issued_at: datetime
    due_date: datetime
    returned_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.book_id or not self.book_id.strip():
            raise ValueError("book_id cannot be empty")
        if not self.reader_id or not self.reader_id.strip():
            raise ValueError("reader_id cannot be empty")
        if self.due_date <= self.issued_at:
            raise ValueError("due_date must be strictly after issued_at")
        if self.returned_at is not None and self.returned_at < self.issued_at:
            raise ValueError("returned_at cannot be before issued_at")

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    def is_overdue(self, as_of: datetime) -> bool:
        """Return True only when the loan is still open and as_of is past due_date."""
        if self.returned_at is not None:
            return False
        return as_of > self.due_date
