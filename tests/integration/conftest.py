"""Shared fixtures for all integration tests.

Every fixture wires REAL in-memory repositories and services.
No mocks anywhere in this directory.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from models.book import Book
from models.reader import Reader
from models.enums import MembershipType
from storage.memory.book_repo import InMemoryBookRepository
from storage.memory.reader_repo import InMemoryReaderRepository
from storage.memory.loan_repo import InMemoryLoanRepository
from storage.memory.reservation_repo import InMemoryReservationRepository
from storage.memory.fine_repo import InMemoryFineRepository
from services.events import EventBus
from services.fine_strategies import FlatFineStrategy
from services.notification import ReaderNotifier
from services.loan_service import LoanService
from services.return_service import ReturnService
from services.reservation_service import ReservationService
from services.membership_service import MembershipService


class Clock:
    """Deterministic, manually-advanceable clock for injecting into services."""

    def __init__(self, start: datetime) -> None:
        self._dt = start

    def __call__(self) -> datetime:
        return self._dt

    def advance(self, **kwargs) -> None:
        self._dt += timedelta(**kwargs)

    def set(self, dt: datetime) -> None:
        self._dt = dt


@dataclass
class Repos:
    books: InMemoryBookRepository
    readers: InMemoryReaderRepository
    loans: InMemoryLoanRepository
    reservations: InMemoryReservationRepository
    fines: InMemoryFineRepository


@dataclass
class Svc:
    loan: LoanService
    returns: ReturnService
    reservation: ReservationService
    membership: MembershipService
    notifier: ReaderNotifier
    bus: EventBus


# ── Fixtures (all function-scoped → fresh state per test) ─────────────────────

@pytest.fixture
def clock() -> Clock:
    return Clock(datetime(2025, 1, 15, 9, 0, 0))


@pytest.fixture
def repos() -> Repos:
    return Repos(
        books=InMemoryBookRepository(),
        readers=InMemoryReaderRepository(),
        loans=InMemoryLoanRepository(),
        reservations=InMemoryReservationRepository(),
        fines=InMemoryFineRepository(),
    )


@pytest.fixture
def svc(repos: Repos, clock: Clock) -> Svc:
    """Wire all real services together; subscribe ReaderNotifier to the EventBus."""
    strategy = FlatFineStrategy(Decimal("1.00"))   # $1 per overdue calendar day
    bus      = EventBus()
    notifier = ReaderNotifier(repos.reservations, repos.readers)
    bus.subscribe(notifier)

    return Svc(
        loan=LoanService(
            repos.loans, repos.books, repos.readers, clock=clock,
        ),
        returns=ReturnService(
            repos.loans, repos.books, repos.readers, repos.fines,
            strategy, bus, clock=clock,
        ),
        reservation=ReservationService(
            repos.reservations, repos.books, repos.readers,
            expiry_days=3, clock=clock,
        ),
        membership=MembershipService(
            repos.readers, repos.fines,
            max_unpaid_amount=Decimal("10.00"),
            max_overdue_count=3,
        ),
        notifier=notifier,
        bus=bus,
    )


# ── Shared book / reader helpers used across test modules ─────────────────────

ISBNS = [
    "9780132350884", "047096890X",    "0132350882",
    "9780201633610", "9780596007126", "9780471958697",
    "9781492056355", "9780134685991", "9780735619678",
    "9780201485677",
]


def make_book(book_id: str = "b0", isbn_idx: int = 0, copies: int = 2) -> Book:
    return Book(book_id, f"Book {book_id}", "Author", ISBNS[isbn_idx], copies, copies)


def make_reader(
    reader_id: str = "r0",
    membership: MembershipType = MembershipType.STANDARD,
) -> Reader:
    return Reader(reader_id, f"Reader {reader_id}", membership)
