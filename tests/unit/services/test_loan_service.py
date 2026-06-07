"""TDD unit tests for LoanService — all repos mocked."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

from models.book import Book
from models.loan import Loan
from models.reader import Reader
from models.enums import MembershipType
from storage.interfaces import LoanRepository, BookRepository, ReaderRepository
from services.loan_service import LoanService
from utils.exceptions import (
    ReaderNotFoundError, BookNotFoundError,
    ReaderBlockedError, BookNotAvailableError, LoanLimitExceededError,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_NOW = datetime(2025, 6, 1, 10, 0, 0)
_DUE = _NOW + timedelta(days=14)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _book(available: int = 3) -> Book:
    return Book("b1", "Clean Code", "Martin", "9780132350884", 5, available)


def _reader(
    membership: MembershipType = MembershipType.STANDARD,
    is_blocked: bool = False,
    active_loans: int = 0,
) -> Reader:
    return Reader("r1", "Alice", membership, is_blocked=is_blocked, active_loans=active_loans)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def loan_repo(mocker):
    m = mocker.MagicMock(spec=LoanRepository)
    m.find_active_by_reader.return_value = []
    return m


@pytest.fixture
def book_repo(mocker):
    m = mocker.MagicMock(spec=BookRepository)
    m.get_by_id.return_value = _book()
    return m


@pytest.fixture
def reader_repo(mocker):
    m = mocker.MagicMock(spec=ReaderRepository)
    m.get_by_id.return_value = _reader()
    return m


@pytest.fixture
def svc(loan_repo, book_repo, reader_repo) -> LoanService:
    return LoanService(loan_repo, book_repo, reader_repo, clock=lambda: _NOW)


# ── Successful issue ──────────────────────────────────────────────────────────

class TestIssuebookSuccess:
    def test_returns_loan_with_correct_ids(self, svc):
        loan = svc.issue_book("r1", "b1")
        assert loan.reader_id == "r1"
        assert loan.book_id == "b1"

    def test_issued_at_taken_from_clock(self, svc):
        loan = svc.issue_book("r1", "b1")
        assert loan.issued_at == _NOW

    def test_due_date_defaults_to_14_days(self, svc):
        loan = svc.issue_book("r1", "b1")
        assert loan.due_date == _NOW + timedelta(days=14)

    def test_custom_loan_days_respected(self, svc):
        loan = svc.issue_book("r1", "b1", loan_days=7)
        assert loan.due_date == _NOW + timedelta(days=7)

    def test_loan_added_to_repo(self, svc, loan_repo):
        loan = svc.issue_book("r1", "b1")
        loan_repo.add.assert_called_once_with(loan)

    def test_available_copies_decremented(self, svc, book_repo):
        book = _book(available=3)
        book_repo.get_by_id.return_value = book
        svc.issue_book("r1", "b1")
        assert book.available_copies == 2

    def test_book_repo_updated(self, svc, book_repo):
        svc.issue_book("r1", "b1")
        book_repo.update.assert_called_once()

    def test_reader_active_loans_incremented(self, svc, reader_repo):
        reader = _reader(active_loans=1)
        reader_repo.get_by_id.return_value = reader
        svc.issue_book("r1", "b1")
        assert reader.active_loans == 2

    def test_reader_repo_updated(self, svc, reader_repo):
        svc.issue_book("r1", "b1")
        reader_repo.update.assert_called_once()

    def test_loan_has_non_empty_id(self, svc):
        loan = svc.issue_book("r1", "b1")
        assert loan.id and loan.id.strip()


# ── Validation errors ─────────────────────────────────────────────────────────

class TestIssuebookValidation:
    def test_reader_not_found_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = None
        with pytest.raises(ReaderNotFoundError):
            svc.issue_book("r1", "b1")

    def test_reader_blocked_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = _reader(is_blocked=True)
        with pytest.raises(ReaderBlockedError):
            svc.issue_book("r1", "b1")

    def test_blocked_reader_never_reaches_book_lookup(self, svc, reader_repo, book_repo):
        reader_repo.get_by_id.return_value = _reader(is_blocked=True)
        with pytest.raises(ReaderBlockedError):
            svc.issue_book("r1", "b1")
        book_repo.get_by_id.assert_not_called()

    def test_book_not_found_raises(self, svc, book_repo):
        book_repo.get_by_id.return_value = None
        with pytest.raises(BookNotFoundError):
            svc.issue_book("r1", "b1")

    def test_no_available_copies_raises(self, svc, book_repo):
        book_repo.get_by_id.return_value = _book(available=0)
        with pytest.raises(BookNotAvailableError):
            svc.issue_book("r1", "b1")

    def test_no_available_copies_does_not_modify_repo(self, svc, book_repo, loan_repo):
        book_repo.get_by_id.return_value = _book(available=0)
        with pytest.raises(BookNotAvailableError):
            svc.issue_book("r1", "b1")
        loan_repo.add.assert_not_called()
        book_repo.update.assert_not_called()


# ── Loan limits by membership ─────────────────────────────────────────────────

class TestLoanLimits:
    def test_standard_at_limit_3_raises(self, svc, loan_repo, reader_repo):
        reader_repo.get_by_id.return_value = _reader(MembershipType.STANDARD)
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 3
        with pytest.raises(LoanLimitExceededError):
            svc.issue_book("r1", "b1")

    def test_standard_below_limit_2_succeeds(self, svc, loan_repo, reader_repo):
        reader_repo.get_by_id.return_value = _reader(MembershipType.STANDARD)
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 2
        assert svc.issue_book("r1", "b1") is not None

    def test_premium_at_limit_5_raises(self, svc, loan_repo, reader_repo):
        reader_repo.get_by_id.return_value = _reader(MembershipType.PREMIUM)
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 5
        with pytest.raises(LoanLimitExceededError):
            svc.issue_book("r1", "b1")

    def test_premium_below_limit_4_succeeds(self, svc, loan_repo, reader_repo):
        reader_repo.get_by_id.return_value = _reader(MembershipType.PREMIUM)
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 4
        assert svc.issue_book("r1", "b1") is not None

    def test_premium_not_blocked_at_standard_limit_3(self, svc, loan_repo, reader_repo):
        """Premium reader with 3 loans must still be able to borrow (limit=5)."""
        reader_repo.get_by_id.return_value = _reader(MembershipType.PREMIUM)
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 3
        assert svc.issue_book("r1", "b1") is not None

    def test_standard_blocked_at_3_premium_not_at_3(self, svc, loan_repo, reader_repo):
        """Explicit boundary: standard=3 raises; premium=3 succeeds."""
        loan_repo.find_active_by_reader.return_value = [MagicMock()] * 3
        reader_repo.get_by_id.return_value = _reader(MembershipType.STANDARD)
        with pytest.raises(LoanLimitExceededError):
            svc.issue_book("r1", "b1")
        reader_repo.get_by_id.return_value = _reader(MembershipType.PREMIUM)
        assert svc.issue_book("r1", "b1") is not None
