import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from models.reservation import Reservation
from models.enums import ReservationStatus
from storage.interfaces import ReservationRepository, BookRepository, ReaderRepository
from services.priority import reservation_priority_key
from utils.exceptions import (
    ReaderNotFoundError,
    BookNotFoundError,
    ReaderBlockedError,
    DuplicateReservationError,
    ReservationNotFoundError,
)


class ReservationService:
    """Manages reservation lifecycle and priority queue.

    Queue ordering: PREMIUM members are served before STANDARD members;
    within the same tier, the longest-waiting reader (smallest created_at)
    is served first.
    """

    def __init__(
        self,
        reservation_repo: ReservationRepository,
        book_repo: BookRepository,
        reader_repo: ReaderRepository,
        expiry_days: int = 3,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._reservation_repo = reservation_repo
        self._book_repo = book_repo
        self._reader_repo = reader_repo
        self._expiry_days = expiry_days
        self._clock = clock

    def reserve(self, reader_id: str, book_id: str) -> Reservation:
        """Create an ACTIVE reservation for reader_id on book_id.

        Raises:
            ReaderNotFoundError: reader does not exist.
            ReaderBlockedError: reader is currently blocked.
            BookNotFoundError: book does not exist.
            DuplicateReservationError: reader already has an active reservation
                for this book.
        """
        reader = self._reader_repo.get_by_id(reader_id)
        if reader is None:
            raise ReaderNotFoundError(f"Reader not found: {reader_id!r}")
        if reader.is_blocked:
            raise ReaderBlockedError(f"Reader is blocked: {reader_id!r}")

        book = self._book_repo.get_by_id(book_id)
        if book is None:
            raise BookNotFoundError(f"Book not found: {book_id!r}")

        existing = self._reservation_repo.find_active_by_book(book_id)
        if any(r.reader_id == reader_id for r in existing):
            raise DuplicateReservationError(
                f"Reader {reader_id!r} already has an active reservation for {book_id!r}"
            )

        now = self._clock()
        reservation = Reservation(
            id=str(uuid.uuid4()),
            book_id=book_id,
            reader_id=reader_id,
            created_at=now,
            expires_at=now + timedelta(days=self._expiry_days),
        )
        self._reservation_repo.add(reservation)
        return reservation

    def cancel(self, reservation_id: str) -> None:
        """Cancel an existing reservation.

        Raises:
            ReservationNotFoundError: no reservation with this id.
        """
        reservation = self._reservation_repo.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError(f"Reservation not found: {reservation_id!r}")
        reservation.status = ReservationStatus.CANCELLED
        self._reservation_repo.update(reservation)

    def expire_old(self, as_of: datetime | None = None) -> list[Reservation]:
        """Expire all ACTIVE reservations whose expires_at <= as_of.

        Uses the injected clock when as_of is None.
        Returns the list of reservations that were just expired.
        """
        reference = as_of if as_of is not None else self._clock()
        expired = []
        for res in self._reservation_repo.find_active():
            if res.expires_at <= reference:
                res.status = ReservationStatus.EXPIRED
                self._reservation_repo.update(res)
                expired.append(res)
        return expired

    def get_next_in_queue(self, book_id: str) -> Reservation | None:
        """Return the highest-priority active reservation for book_id, or None.

        Priority: PREMIUM membership first, then earliest created_at.
        Reservations whose reader cannot be found are treated as STANDARD rank.
        """
        active = self._reservation_repo.find_active_by_book(book_id)
        if not active:
            return None
        return min(active, key=lambda r: reservation_priority_key(r, self._reader_repo))
