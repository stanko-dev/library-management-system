from dataclasses import dataclass

from storage.interfaces import ReservationRepository, ReaderRepository
from services.events import BookAvailabilityObserver, BookAvailableEvent
from services.priority import reservation_priority_key


@dataclass(frozen=True)
class Notification:
    """Immutable record that a specific reader was alerted about a book."""

    reader_id: str
    book_id: str


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
        first = min(reservations, key=lambda r: reservation_priority_key(r, self._reader_repo))
        self._notifications.append(
            Notification(reader_id=first.reader_id, book_id=event.book_id)
        )

    def get_notifications(self) -> list[Notification]:
        return list(self._notifications)

    def get_notifications_for_reader(self, reader_id: str) -> list[Notification]:
        return [n for n in self._notifications if n.reader_id == reader_id]
