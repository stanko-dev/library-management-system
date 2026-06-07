import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from models.loan import Loan
from models.enums import MembershipType
from storage.interfaces import LoanRepository, BookRepository, ReaderRepository
from utils.exceptions import (
    ReaderNotFoundError,
    BookNotFoundError,
    ReaderBlockedError,
    BookNotAvailableError,
    LoanLimitExceededError,
)

_LOAN_LIMITS: dict[MembershipType, int] = {
    MembershipType.STANDARD: 3,
    MembershipType.PREMIUM: 5,
}


class LoanService:
    """Issues new loans after enforcing reader eligibility and copy availability.

    All domain rules live here; repositories are injected and never instantiated
    internally (Dependency Inversion Principle).
    """

    def __init__(
        self,
        loan_repo: LoanRepository,
        book_repo: BookRepository,
        reader_repo: ReaderRepository,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._loan_repo = loan_repo
        self._book_repo = book_repo
        self._reader_repo = reader_repo
        self._clock = clock

    def issue_book(
        self, reader_id: str, book_id: str, loan_days: int = 14
    ) -> Loan:
        """Create a loan for reader_id / book_id, decrement available copies.

        Raises:
            ReaderNotFoundError: reader does not exist.
            ReaderBlockedError: reader is currently blocked.
            BookNotFoundError: book does not exist.
            BookNotAvailableError: all copies are checked out.
            LoanLimitExceededError: reader has reached their membership limit.
        """
        reader = self._reader_repo.get_by_id(reader_id)
        if reader is None:
            raise ReaderNotFoundError(f"Reader not found: {reader_id!r}")
        if reader.is_blocked:
            raise ReaderBlockedError(f"Reader is blocked: {reader_id!r}")

        book = self._book_repo.get_by_id(book_id)
        if book is None:
            raise BookNotFoundError(f"Book not found: {book_id!r}")
        if book.available_copies == 0:
            raise BookNotAvailableError(f"No copies available: {book_id!r}")

        active_count = len(self._loan_repo.find_active_by_reader(reader_id))
        limit = _LOAN_LIMITS[reader.membership]
        if active_count >= limit:
            raise LoanLimitExceededError(
                f"Loan limit {limit} reached for reader {reader_id!r}"
            )

        issued_at = self._clock()
        loan = Loan(
            id=str(uuid.uuid4()),
            book_id=book_id,
            reader_id=reader_id,
            issued_at=issued_at,
            due_date=issued_at + timedelta(days=loan_days),
        )
        self._loan_repo.add(loan)

        book.available_copies -= 1
        self._book_repo.update(book)

        reader.active_loans += 1
        self._reader_repo.update(reader)

        return loan
