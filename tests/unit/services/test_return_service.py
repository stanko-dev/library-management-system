"""TDD unit tests for ReturnService — all repos and strategy mocked."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, call

from models.book import Book
from models.fine import Fine
from models.loan import Loan
from models.reader import Reader
from models.enums import MembershipType
from storage.interfaces import (
    LoanRepository, BookRepository, ReaderRepository, FineRepository,
)
from services.events import BookAvailabilitySubject, BookAvailableEvent
from services.fine_strategies import FineStrategy
from services.return_service import ReturnService
from utils.exceptions import LoanNotFoundError, AlreadyReturnedError

# ── Constants ─────────────────────────────────────────────────────────────────

_ISSUED   = datetime(2025, 5,  1, 10, 0, 0)
_DUE      = datetime(2025, 5, 15, 10, 0, 0)
_ON_TIME  = datetime(2025, 5, 14, 10, 0, 0)   # 1 day before due
_OVERDUE  = datetime(2025, 5, 20, 10, 0, 0)   # 5 days past due

# ── Helpers ───────────────────────────────────────────────────────────────────

def _loan(returned_at=None) -> Loan:
    return Loan("l1", "b1", "r1", _ISSUED, _DUE, returned_at=returned_at)


def _book(available: int = 0) -> Book:
    return Book("b1", "Title", "Author", "9780132350884", 5, available)


def _reader(active_loans: int = 1, overdue_count: int = 0) -> Reader:
    return Reader("r1", "Alice", MembershipType.STANDARD,
                  active_loans=active_loans, overdue_count=overdue_count)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def loan_repo(mocker):
    m = mocker.MagicMock(spec=LoanRepository)
    m.get_by_id.return_value = _loan()
    return m


@pytest.fixture
def book_repo(mocker):
    m = mocker.MagicMock(spec=BookRepository)
    m.get_by_id.return_value = _book(available=0)
    return m


@pytest.fixture
def reader_repo(mocker):
    m = mocker.MagicMock(spec=ReaderRepository)
    m.get_by_id.return_value = _reader()
    return m


@pytest.fixture
def fine_repo(mocker):
    return mocker.MagicMock(spec=FineRepository)


@pytest.fixture
def strategy(mocker):
    m = mocker.MagicMock(spec=FineStrategy)
    m.calculate.return_value = Decimal("0")    # on-time by default
    return m


@pytest.fixture
def event_bus(mocker):
    return mocker.MagicMock(spec=BookAvailabilitySubject)


def _svc(loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus, clock):
    return ReturnService(
        loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus, clock=clock,
    )


# ── Validation errors ─────────────────────────────────────────────────────────

class TestReturnValidation:
    def test_loan_not_found_raises(self, loan_repo, book_repo, reader_repo,
                                    fine_repo, strategy, event_bus):
        loan_repo.get_by_id.return_value = None
        svc = _svc(loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus,
                   clock=lambda: _ON_TIME)
        with pytest.raises(LoanNotFoundError):
            svc.return_book("l1")

    def test_already_returned_raises(self, loan_repo, book_repo, reader_repo,
                                      fine_repo, strategy, event_bus):
        loan_repo.get_by_id.return_value = _loan(returned_at=_ISSUED + timedelta(days=1))
        svc = _svc(loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus,
                   clock=lambda: _ON_TIME)
        with pytest.raises(AlreadyReturnedError):
            svc.return_book("l1")


# ── On-time return ────────────────────────────────────────────────────────────

class TestOnTimeReturn:
    @pytest.fixture(autouse=True)
    def setup(self, loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus):
        self.svc = _svc(loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus,
                        clock=lambda: _ON_TIME)
        self.loan_repo  = loan_repo
        self.book_repo  = book_repo
        self.reader_repo = reader_repo
        self.fine_repo  = fine_repo
        self.strategy   = strategy
        self.event_bus  = event_bus

    def test_returns_none(self):
        assert self.svc.return_book("l1") is None

    def test_fine_repo_not_called(self):
        self.svc.return_book("l1")
        self.fine_repo.add.assert_not_called()

    def test_returned_at_set_from_clock(self):
        loan = _loan()
        self.loan_repo.get_by_id.return_value = loan
        self.svc.return_book("l1")
        assert loan.returned_at == _ON_TIME

    def test_loan_repo_updated(self):
        self.svc.return_book("l1")
        self.loan_repo.update.assert_called_once()

    def test_book_available_copies_incremented(self):
        book = _book(available=0)
        self.book_repo.get_by_id.return_value = book
        self.svc.return_book("l1")
        assert book.available_copies == 1

    def test_book_repo_updated(self):
        self.svc.return_book("l1")
        self.book_repo.update.assert_called_once()

    def test_reader_active_loans_decremented(self):
        reader = _reader(active_loans=2)
        self.reader_repo.get_by_id.return_value = reader
        self.svc.return_book("l1")
        assert reader.active_loans == 1

    def test_reader_overdue_count_unchanged(self):
        reader = _reader(overdue_count=1)
        self.reader_repo.get_by_id.return_value = reader
        self.svc.return_book("l1")
        assert reader.overdue_count == 1

    def test_reader_repo_updated(self):
        self.svc.return_book("l1")
        self.reader_repo.update.assert_called_once()

    def test_event_bus_notified_with_book_id(self):
        self.svc.return_book("l1")
        self.event_bus.notify.assert_called_once()
        event = self.event_bus.notify.call_args[0][0]
        assert isinstance(event, BookAvailableEvent)
        assert event.book_id == "b1"

    def test_strategy_called_with_due_and_return_dates(self):
        self.svc.return_book("l1")
        self.strategy.calculate.assert_called_once_with(
            _DUE.date(), _ON_TIME.date()
        )

    def test_reader_active_loans_floored_at_zero(self):
        reader = _reader(active_loans=0)
        self.reader_repo.get_by_id.return_value = reader
        self.svc.return_book("l1")
        assert reader.active_loans == 0


# ── Overdue return ────────────────────────────────────────────────────────────

class TestOverdueReturn:
    @pytest.fixture(autouse=True)
    def setup(self, loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus):
        strategy.calculate.return_value = Decimal("10.00")
        self.svc = _svc(loan_repo, book_repo, reader_repo, fine_repo, strategy, event_bus,
                        clock=lambda: _OVERDUE)
        self.loan_repo   = loan_repo
        self.book_repo   = book_repo
        self.reader_repo = reader_repo
        self.fine_repo   = fine_repo
        self.strategy    = strategy
        self.event_bus   = event_bus

    def test_returns_fine_object(self):
        result = self.svc.return_book("l1")
        assert isinstance(result, Fine)

    def test_fine_amount_from_strategy(self):
        fine = self.svc.return_book("l1")
        assert fine.amount == Decimal("10.00")

    def test_fine_linked_to_reader_and_loan(self):
        fine = self.svc.return_book("l1")
        assert fine.reader_id == "r1"
        assert fine.loan_id == "l1"

    def test_fine_not_paid_initially(self):
        fine = self.svc.return_book("l1")
        assert fine.is_paid is False

    def test_fine_repo_add_called(self):
        fine = self.svc.return_book("l1")
        self.fine_repo.add.assert_called_once_with(fine)

    def test_reader_overdue_count_incremented(self):
        reader = _reader(overdue_count=0)
        self.reader_repo.get_by_id.return_value = reader
        self.svc.return_book("l1")
        assert reader.overdue_count == 1

    def test_event_bus_notified_even_when_overdue(self):
        self.svc.return_book("l1")
        self.event_bus.notify.assert_called_once()

    def test_strategy_receives_date_objects_not_datetimes(self):
        self.svc.return_book("l1")
        args = self.strategy.calculate.call_args[0]
        from datetime import date
        assert isinstance(args[0], date) and not isinstance(args[0], datetime)
        assert isinstance(args[1], date) and not isinstance(args[1], datetime)
