from dataclasses import dataclass

from models.enums import MembershipType
from models.reservation import Reservation
from storage.interfaces import ReservationRepository, ReaderRepository
from services.events import BookAvailabilityObserver, BookAvailableEvent


@dataclass(frozen=True)
class Notification:
    """Immutable record that a specific reader was alerted about a book."""

    reader_id: str
    book_id: str


def _queue_key(res: Reservation, reader_repo: ReaderRepository) -> tuple:
    """Sort key: PREMIUM (0) before STANDARD (1), then oldest created_at."""
    reader = reader_repo.get_by_id(res.reader_id)
    rank = 0 if (reader and reader.membership == MembershipType.PREMIUM) else 1
    return (rank, res.created_at)


class ReaderNotifier(BookAvailabilityObserver):
    """Concrete observer: on each availability event records a Notification for
    the highest-priority reader in the reservation queue.

    Priority: PREMIUM membership first; ties broken by earliest created_at.

    Dependencies are injected; no external I/O.
    """

    def __init__(
        self,
        reservation_repo: ReservationRepository,
        reader_repo: ReaderRepository,
    ) -> None:
        self._reservation_repo = reservation_repo
        self._reader_repo = reader_repo
        self._notifications: list[Notification] = []

    def on_book_available(self, event: BookAvailableEvent) -> None:
        reservations = self._reservation_repo.find_active_by_book(event.book_id)
        if not reservations:
            return
        first = min(reservations, key=lambda r: _queue_key(r, self._reader_repo))
        self._notifications.append(
            Notification(reader_id=first.reader_id, book_id=event.book_id)
        )

    def get_notifications(self) -> list[Notification]:
        return list(self._notifications)

    def get_notifications_for_reader(self, reader_id: str) -> list[Notification]:
        return [n for n in self._notifications if n.reader_id == reader_id]
