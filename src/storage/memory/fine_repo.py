from decimal import Decimal

from models.fine import Fine
from storage.interfaces import FineRepository


class InMemoryFineRepository(FineRepository):
    def __init__(self) -> None:
        self._store: dict[str, Fine] = {}

    def add(self, fine: Fine) -> None:
        if fine.id in self._store:
            raise ValueError(f"Fine already exists: {fine.id}")
        self._store[fine.id] = fine

    def get_by_id(self, fine_id: str) -> Fine | None:
        return self._store.get(fine_id)

    def list_all(self) -> list[Fine]:
        return list(self._store.values())

    def update(self, fine: Fine) -> None:
        if fine.id not in self._store:
            raise KeyError(fine.id)
        self._store[fine.id] = fine

    def delete(self, fine_id: str) -> None:
        if fine_id not in self._store:
            raise KeyError(fine_id)
        del self._store[fine_id]

    def find_by_reader(self, reader_id: str) -> list[Fine]:
        return [f for f in self._store.values() if f.reader_id == reader_id]

    def find_by_loan(self, loan_id: str) -> list[Fine]:
        return [f for f in self._store.values() if f.loan_id == loan_id]

    def find_unpaid(self) -> list[Fine]:
        return [f for f in self._store.values() if not f.is_paid]

    def find_unpaid_by_reader(self, reader_id: str) -> list[Fine]:
        return [f for f in self._store.values()
                if f.reader_id == reader_id and not f.is_paid]

    def total_unpaid_by_reader(self, reader_id: str) -> Decimal:
        return sum(
            (f.amount for f in self.find_unpaid_by_reader(reader_id)),
            Decimal("0"),
        )
