from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class BookAvailableEvent:
    """Fired when a book's available-copy count rises above zero."""

    book_id: str

    def __post_init__(self) -> None:
        if not self.book_id or not self.book_id.strip():
            raise ValueError("book_id cannot be empty")


class BookAvailabilityObserver(ABC):
    """Receives book-availability events."""

    @abstractmethod
    def on_book_available(self, event: BookAvailableEvent) -> None: ...


class BookAvailabilitySubject(ABC):
    """Manages a set of observers and dispatches availability events to them."""

    @abstractmethod
    def subscribe(self, observer: BookAvailabilityObserver) -> None: ...

    @abstractmethod
    def unsubscribe(self, observer: BookAvailabilityObserver) -> None: ...

    @abstractmethod
    def notify(self, event: BookAvailableEvent) -> None: ...


class EventBus(BookAvailabilitySubject):
    """In-memory publish/subscribe bus for book-availability events.

    Guarantees:
    - Duplicate subscribe calls are idempotent.
    - notify iterates a snapshot so observers may unsubscribe mid-dispatch
      without causing RuntimeError.
    - Unsubscribing an observer that is not registered raises ValueError.
    """

    def __init__(self) -> None:
        self._observers: list[BookAvailabilityObserver] = []

    def subscribe(self, observer: BookAvailabilityObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: BookAvailabilityObserver) -> None:
        if observer not in self._observers:
            raise ValueError(f"Observer is not subscribed: {observer!r}")
        self._observers.remove(observer)

    def notify(self, event: BookAvailableEvent) -> None:
        for observer in list(self._observers):   # snapshot prevents mutation bugs
            observer.on_book_available(event)
