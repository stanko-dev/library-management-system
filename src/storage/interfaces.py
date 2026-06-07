from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from models.book import Book
from models.reader import Reader
from models.loan import Loan
from models.reservation import Reservation
from models.fine import Fine


class BookRepository(ABC):
    @abstractmethod
    def add(self, book: Book) -> None: ...

    @abstractmethod
    def get_by_id(self, book_id: str) -> Book | None: ...

    @abstractmethod
    def get_by_isbn(self, isbn: str) -> Book | None: ...

    @abstractmethod
    def list_all(self) -> list[Book]: ...

    @abstractmethod
    def update(self, book: Book) -> None: ...

    @abstractmethod
    def delete(self, book_id: str) -> None: ...

    @abstractmethod
    def find_by_title(self, title: str) -> list[Book]: ...

    @abstractmethod
    def find_by_author(self, author: str) -> list[Book]: ...

    @abstractmethod
    def find_available(self) -> list[Book]: ...


class ReaderRepository(ABC):
    @abstractmethod
    def add(self, reader: Reader) -> None: ...

    @abstractmethod
    def get_by_id(self, reader_id: str) -> Reader | None: ...

    @abstractmethod
    def list_all(self) -> list[Reader]: ...

    @abstractmethod
    def update(self, reader: Reader) -> None: ...

    @abstractmethod
    def delete(self, reader_id: str) -> None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Reader]: ...

    @abstractmethod
    def find_active(self) -> list[Reader]: ...

    @abstractmethod
    def find_blocked(self) -> list[Reader]: ...


class LoanRepository(ABC):
    @abstractmethod
    def add(self, loan: Loan) -> None: ...

    @abstractmethod
    def get_by_id(self, loan_id: str) -> Loan | None: ...

    @abstractmethod
    def list_all(self) -> list[Loan]: ...

    @abstractmethod
    def update(self, loan: Loan) -> None: ...

    @abstractmethod
    def delete(self, loan_id: str) -> None: ...

    @abstractmethod
    def find_by_reader(self, reader_id: str) -> list[Loan]: ...

    @abstractmethod
    def find_by_book(self, book_id: str) -> list[Loan]: ...

    @abstractmethod
    def find_active(self) -> list[Loan]: ...

    @abstractmethod
    def find_active_by_reader(self, reader_id: str) -> list[Loan]: ...

    @abstractmethod
    def find_overdue(self, as_of: datetime) -> list[Loan]: ...


class ReservationRepository(ABC):
    @abstractmethod
    def add(self, reservation: Reservation) -> None: ...

    @abstractmethod
    def get_by_id(self, reservation_id: str) -> Reservation | None: ...

    @abstractmethod
    def list_all(self) -> list[Reservation]: ...

    @abstractmethod
    def update(self, reservation: Reservation) -> None: ...

    @abstractmethod
    def delete(self, reservation_id: str) -> None: ...

    @abstractmethod
    def find_by_reader(self, reader_id: str) -> list[Reservation]: ...

    @abstractmethod
    def find_by_book(self, book_id: str) -> list[Reservation]: ...

    @abstractmethod
    def find_active(self) -> list[Reservation]: ...

    @abstractmethod
    def find_active_by_book(self, book_id: str) -> list[Reservation]: ...


class FineRepository(ABC):
    @abstractmethod
    def add(self, fine: Fine) -> None: ...

    @abstractmethod
    def get_by_id(self, fine_id: str) -> Fine | None: ...

    @abstractmethod
    def list_all(self) -> list[Fine]: ...

    @abstractmethod
    def update(self, fine: Fine) -> None: ...

    @abstractmethod
    def delete(self, fine_id: str) -> None: ...

    @abstractmethod
    def find_by_reader(self, reader_id: str) -> list[Fine]: ...

    @abstractmethod
    def find_by_loan(self, loan_id: str) -> list[Fine]: ...

    @abstractmethod
    def find_unpaid(self) -> list[Fine]: ...

    @abstractmethod
    def find_unpaid_by_reader(self, reader_id: str) -> list[Fine]: ...

    @abstractmethod
    def total_unpaid_by_reader(self, reader_id: str) -> Decimal: ...
