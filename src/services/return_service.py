import uuid
from collections.abc import Callable
from datetime import datetime

from models.fine import Fine
from services.events import BookAvailabilitySubject, BookAvailableEvent
from services.fine_strategies import FineStrategy
from storage.interfaces import (
    LoanRepository, BookRepository, ReaderRepository, FineRepository,
)
from utils.exceptions import LoanNotFoundError, AlreadyReturnedError


class ReturnService:
    """Processes a book return: records the return date, computes any fine via
    the injected FineStrategy, updates reader/book state, and publishes a
    BookAvailableEvent so observers (e.g. ReaderNotifier) can react.

    The fine strategy and event bus are injected — this service never decides
    *which* fine policy or *which* observers to use (Open/Closed Principle).
    """

    def __init__(
        self,
        loan_repo: LoanRepository,
        book_repo: BookRepository,
        reader_repo: ReaderRepository,
        fine_repo: FineRepository,
        fine_strategy: FineStrategy,
        event_bus: BookAvailabilitySubject,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._loan_repo = loan_repo
        self._book_repo = book_repo
        self._reader_repo = reader_repo
        self._fine_repo = fine_repo
        self._fine_strategy = fine_strategy
        self._event_bus = event_bus
        self._clock = clock

    def return_book(self, loan_id: str) -> Fine | None:
        """Mark the loan returned, charge a fine if overdue, update book/reader.

        Returns the Fine object if a fine was created, otherwise None.

        Raises:
            LoanNotFoundError: no loan with loan_id exists.
            AlreadyReturnedError: loan was already returned.
        """
        loan = self._loan_repo.get_by_id(loan_id)
        if loan is None:
            raise LoanNotFoundError(f"Loan not found: {loan_id!r}")
        if loan.returned_at is not None:
            raise AlreadyReturnedError(f"Loan already returned: {loan_id!r}")

        returned_at = self._clock()
        loan.returned_at = returned_at
        self._loan_repo.update(loan)

        fine_amount = self._fine_strategy.calculate(
            loan.due_date.date(), returned_at.date()
        )

        fine: Fine | None = None
        if fine_amount > 0:
            fine = Fine(
                id=str(uuid.uuid4()),
                reader_id=loan.reader_id,
                loan_id=loan_id,
                amount=fine_amount,
            )
            self._fine_repo.add(fine)

        book = self._book_repo.get_by_id(loan.book_id)
        book.available_copies += 1
        self._book_repo.update(book)

        reader = self._reader_repo.get_by_id(loan.reader_id)
        reader.active_loans = max(0, reader.active_loans - 1)
        if fine_amount > 0:
            reader.overdue_count += 1
        self._reader_repo.update(reader)

        self._event_bus.notify(BookAvailableEvent(loan.book_id))

        return fine
