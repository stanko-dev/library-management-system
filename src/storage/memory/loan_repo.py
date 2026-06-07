from datetime import datetime

from models.loan import Loan
from storage.interfaces import LoanRepository


class InMemoryLoanRepository(LoanRepository):
    def __init__(self) -> None:
        self._store: dict[str, Loan] = {}

    def add(self, loan: Loan) -> None:
        if loan.id in self._store:
            raise ValueError(f"Loan already exists: {loan.id}")
        self._store[loan.id] = loan

    def get_by_id(self, loan_id: str) -> Loan | None:
        return self._store.get(loan_id)

    def list_all(self) -> list[Loan]:
        return list(self._store.values())

    def update(self, loan: Loan) -> None:
        if loan.id not in self._store:
            raise KeyError(loan.id)
        self._store[loan.id] = loan

    def delete(self, loan_id: str) -> None:
        if loan_id not in self._store:
            raise KeyError(loan_id)
        del self._store[loan_id]

    def find_by_reader(self, reader_id: str) -> list[Loan]:
        return [l for l in self._store.values() if l.reader_id == reader_id]

    def find_by_book(self, book_id: str) -> list[Loan]:
        return [l for l in self._store.values() if l.book_id == book_id]

    def find_active(self) -> list[Loan]:
        return [l for l in self._store.values() if l.is_active]

    def find_active_by_reader(self, reader_id: str) -> list[Loan]:
        return [l for l in self._store.values()
                if l.reader_id == reader_id and l.is_active]

    def find_overdue(self, as_of: datetime) -> list[Loan]:
        return [l for l in self._store.values() if l.is_overdue(as_of)]
