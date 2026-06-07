from dataclasses import dataclass, field
from .enums import BookStatus


def _validate_isbn(isbn: str) -> None:
    stripped = isbn.replace("-", "")
    if len(stripped) not in (10, 13):
        raise ValueError(
            f"isbn must be 10 or 13 digits when hyphens are removed (got {len(stripped)})"
        )
    allowed = set("0123456789X")
    invalid = set(stripped) - allowed
    if invalid:
        raise ValueError(f"isbn contains invalid characters: {sorted(invalid)}")


@dataclass
class Book:
    id: str
    title: str
    author: str
    isbn: str
    total_copies: int
    available_copies: int
    status: BookStatus = BookStatus.AVAILABLE

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")
        if not self.author or not self.author.strip():
            raise ValueError("author cannot be empty")
        if not self.isbn or not self.isbn.strip():
            raise ValueError("isbn cannot be empty")
        _validate_isbn(self.isbn)
        if self.total_copies < 1:
            raise ValueError("total_copies must be at least 1")
        if self.available_copies < 0:
            raise ValueError("available_copies cannot be negative")
        if self.available_copies > self.total_copies:
            raise ValueError("available_copies cannot exceed total_copies")
