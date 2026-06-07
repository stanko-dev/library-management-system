"""Integration tests: borrow → overdue → return → fine created → pay fine.

All services and repositories are real; no mocks.
Fine strategy: FlatFineStrategy($1/day).  Loan period: 14 days.
"""
import pytest
from decimal import Decimal

from models.enums import MembershipType
from utils.exceptions import BookNotAvailableError, LoanLimitExceededError
from tests.integration.conftest import make_book, make_reader, ISBNS
from models.book import Book

_LOAN = 14   # default loan period in days


# ── On-time return ────────────────────────────────────────────────────────────

class TestOnTimeReturn:
    def test_issue_decrements_available_copies(self, repos, svc):
        repos.books.add(make_book("b0", copies=3))
        repos.readers.add(make_reader("r0"))
        svc.loan.issue_book("r0", "b0")
        assert repos.books.get_by_id("b0").available_copies == 2

    def test_on_time_return_produces_no_fine(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=10)          # inside 14-day window
        fine = svc.returns.return_book(loan.id)
        assert fine is None
        assert repos.fines.find_by_reader("r0") == []

    def test_return_exactly_on_due_date_no_fine(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN)       # exactly at boundary
        fine = svc.returns.return_book(loan.id)
        assert fine is None

    def test_available_copies_restored_after_on_time_return(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=2))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        assert repos.books.get_by_id("b0").available_copies == 1
        clock.advance(days=7)
        svc.returns.return_book(loan.id)
        assert repos.books.get_by_id("b0").available_copies == 2

    def test_reader_active_loans_incremented_then_decremented(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        assert repos.readers.get_by_id("r0").active_loans == 1
        clock.advance(days=7)
        svc.returns.return_book(loan.id)
        assert repos.readers.get_by_id("r0").active_loans == 0

    def test_return_restores_copy_for_next_borrower(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        repos.readers.add(make_reader("r1"))
        loan = svc.loan.issue_book("r0", "b0")
        with pytest.raises(BookNotAvailableError):
            svc.loan.issue_book("r1", "b0")  # no copies left
        clock.advance(days=7)
        svc.returns.return_book(loan.id)
        assert svc.loan.issue_book("r1", "b0") is not None


# ── Overdue return ────────────────────────────────────────────────────────────

class TestOverdueReturn:
    def test_one_day_late_creates_one_dollar_fine(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 1)
        fine = svc.returns.return_book(loan.id)
        assert fine is not None
        assert fine.amount == Decimal("1.00")

    def test_seven_days_late_creates_seven_dollar_fine(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 7)
        fine = svc.returns.return_book(loan.id)
        assert fine.amount == Decimal("7.00")

    def test_fine_stored_in_fine_repo(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 3)
        svc.returns.return_book(loan.id)
        stored = repos.fines.find_by_reader("r0")
        assert len(stored) == 1
        assert stored[0].amount == Decimal("3.00")
        assert not stored[0].is_paid

    def test_overdue_return_increments_reader_overdue_count(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 5)
        svc.returns.return_book(loan.id)
        assert repos.readers.get_by_id("r0").overdue_count == 1

    def test_on_time_return_does_not_increment_overdue_count(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN - 1)
        svc.returns.return_book(loan.id)
        assert repos.readers.get_by_id("r0").overdue_count == 0


# ── Full borrow → overdue → return → pay fine cycle ──────────────────────────

class TestFullBorrowOverdueCycle:
    def test_full_cycle_borrow_overdue_return_pay(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))

        # Borrow
        loan = svc.loan.issue_book("r0", "b0")
        assert repos.books.get_by_id("b0").available_copies == 0
        assert repos.readers.get_by_id("r0").active_loans == 1

        # Advance past due date by 7 days
        clock.advance(days=_LOAN + 7)

        # Return — overdue
        fine = svc.returns.return_book(loan.id)
        assert fine is not None
        assert fine.amount == Decimal("7.00")
        assert not fine.is_paid
        assert repos.books.get_by_id("b0").available_copies == 1
        assert repos.readers.get_by_id("r0").active_loans == 0
        assert repos.readers.get_by_id("r0").overdue_count == 1

        # Pay fine
        fine.is_paid = True
        repos.fines.update(fine)
        assert repos.fines.get_by_id(fine.id).is_paid is True
        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("0")

    def test_two_sequential_loans_accumulate_two_fines(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))

        # First overdue return — $5 fine
        loan1 = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 5)
        svc.returns.return_book(loan1.id)

        # Second overdue return — $3 fine
        loan2 = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 3)
        svc.returns.return_book(loan2.id)

        fines = repos.fines.find_by_reader("r0")
        assert len(fines) == 2
        total = repos.fines.total_unpaid_by_reader("r0")
        assert total == Decimal("8.00")
        assert repos.readers.get_by_id("r0").overdue_count == 2

    def test_pay_all_fines_zeroes_total_unpaid(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))

        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 4)
        fine = svc.returns.return_book(loan.id)

        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("4.00")
        fine.is_paid = True
        repos.fines.update(fine)
        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("0")


# ── Loan limits enforced end-to-end ──────────────────────────────────────────

class TestLoanLimitsEndToEnd:
    def test_standard_reader_capped_at_3(self, repos, svc):
        for i in range(4):
            repos.books.add(
                Book(f"b{i}", f"Book {i}", "Author", ISBNS[i], 5, 5)
            )
        repos.readers.add(make_reader("r0", MembershipType.STANDARD))

        svc.loan.issue_book("r0", "b0")
        svc.loan.issue_book("r0", "b1")
        svc.loan.issue_book("r0", "b2")

        with pytest.raises(LoanLimitExceededError):
            svc.loan.issue_book("r0", "b3")

    def test_premium_reader_capped_at_5(self, repos, svc):
        for i in range(6):
            repos.books.add(
                Book(f"b{i}", f"Book {i}", "Author", ISBNS[i], 5, 5)
            )
        repos.readers.add(make_reader("r0", MembershipType.PREMIUM))

        for i in range(5):
            svc.loan.issue_book("r0", f"b{i}")

        with pytest.raises(LoanLimitExceededError):
            svc.loan.issue_book("r0", "b5")

    def test_premium_not_blocked_at_standard_limit_of_3(self, repos, svc):
        for i in range(4):
            repos.books.add(
                Book(f"b{i}", f"Book {i}", "Author", ISBNS[i], 5, 5)
            )
        repos.readers.add(make_reader("r0", MembershipType.PREMIUM))

        for i in range(3):
            svc.loan.issue_book("r0", f"b{i}")

        # Premium should still be able to borrow the 4th
        loan = svc.loan.issue_book("r0", "b3")
        assert loan is not None

    def test_return_frees_slot_for_further_borrowing(self, repos, svc, clock):
        for i in range(4):
            repos.books.add(
                Book(f"b{i}", f"Book {i}", "Author", ISBNS[i], 5, 5)
            )
        repos.readers.add(make_reader("r0", MembershipType.STANDARD))

        loans = [svc.loan.issue_book("r0", f"b{i}") for i in range(3)]

        # At limit — returning one frees a slot
        clock.advance(days=7)
        svc.returns.return_book(loans[0].id)
        assert svc.loan.issue_book("r0", "b3") is not None

    def test_zero_available_copies_raises_immediately(self, repos, svc):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("r0"))
        repos.readers.add(make_reader("r1"))

        svc.loan.issue_book("r0", "b0")   # takes the only copy

        with pytest.raises(BookNotAvailableError):
            svc.loan.issue_book("r1", "b0")

    def test_multiple_borrows_exhaust_all_copies(self, repos, svc):
        repos.books.add(make_book("b0", copies=2))
        for i in range(3):
            repos.readers.add(make_reader(f"r{i}"))

        svc.loan.issue_book("r0", "b0")
        svc.loan.issue_book("r1", "b0")

        assert repos.books.get_by_id("b0").available_copies == 0

        with pytest.raises(BookNotAvailableError):
            svc.loan.issue_book("r2", "b0")
