from models.reservation import Reservation
from models.enums import ReservationStatus
from storage.interfaces import ReservationRepository


class InMemoryReservationRepository(ReservationRepository):
    def __init__(self) -> None:
        self._store: dict[str, Reservation] = {}

    def add(self, reservation: Reservation) -> None:
        if reservation.id in self._store:
            raise ValueError(f"Reservation already exists: {reservation.id}")
        self._store[reservation.id] = reservation

    def get_by_id(self, reservation_id: str) -> Reservation | None:
        return self._store.get(reservation_id)

    def list_all(self) -> list[Reservation]:
        return list(self._store.values())

    def update(self, reservation: Reservation) -> None:
        if reservation.id not in self._store:
            raise KeyError(reservation.id)
        self._store[reservation.id] = reservation

    def delete(self, reservation_id: str) -> None:
        if reservation_id not in self._store:
            raise KeyError(reservation_id)
        del self._store[reservation_id]

    def find_by_reader(self, reader_id: str) -> list[Reservation]:
        return [r for r in self._store.values() if r.reader_id == reader_id]

    def find_by_book(self, book_id: str) -> list[Reservation]:
        return [r for r in self._store.values() if r.book_id == book_id]

    def find_active(self) -> list[Reservation]:
        return [r for r in self._store.values()
                if r.status == ReservationStatus.ACTIVE]

    def find_active_by_book(self, book_id: str) -> list[Reservation]:
        return [r for r in self._store.values()
                if r.book_id == book_id and r.status == ReservationStatus.ACTIVE]
