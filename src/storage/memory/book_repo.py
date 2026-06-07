from models.book import Book
from storage.interfaces import BookRepository


class InMemoryBookRepository(BookRepository):
    def __init__(self) -> None:
        self._store: dict[str, Book] = {}

    def add(self, book: Book) -> None:
        if book.id in self._store:
            raise ValueError(f"Book already exists: {book.id}")
        self._store[book.id] = book

    def get_by_id(self, book_id: str) -> Book | None:
        return self._store.get(book_id)

    def get_by_isbn(self, isbn: str) -> Book | None:
        return next((b for b in self._store.values() if b.isbn == isbn), None)

    def list_all(self) -> list[Book]:
        return list(self._store.values())

    def update(self, book: Book) -> None:
        if book.id not in self._store:
            raise KeyError(book.id)
        self._store[book.id] = book

    def delete(self, book_id: str) -> None:
        if book_id not in self._store:
            raise KeyError(book_id)
        del self._store[book_id]

    def find_by_title(self, title: str) -> list[Book]:
        needle = title.lower()
        return [b for b in self._store.values() if needle in b.title.lower()]

    def find_by_author(self, author: str) -> list[Book]:
        needle = author.lower()
        return [b for b in self._store.values() if needle in b.author.lower()]

    def find_available(self) -> list[Book]:
        return [b for b in self._store.values() if b.available_copies > 0]
