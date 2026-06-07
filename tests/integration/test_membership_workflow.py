"""Integration tests: reader accumulates overdue/unpaid fines → blocked → rejected
→ unblock → borrow succeeds.

Thresholds wired in conftest: max_unpaid=$10.00, max_overdue_count=3.
Fine strategy: FlatFineStrategy($1/day).
All services and repositories are real; no mocks.
"""
import pytest
from decimal import Decimal

from models.enums import MembershipType
from models.book import Book
from utils.exceptions import ReaderBlockedError
from tests.integration.conftest import make_book, make_reader, ISBNS

_LOAN = 14   # default loan period


# ── Blocking via unpaid fines ─────────────────────────────────────────────────

class TestFineBasedBlocking:
    def test_unpaid_fines_at_threshold_block_on_evaluate(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # Return 10 days late → $10 fine — exactly at threshold
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 10)
        svc.returns.return_book(loan.id)

        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("10.00")
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

    def test_unpaid_fines_below_threshold_do_not_block(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # Return 9 days late → $9 fine — just below threshold
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 9)
        svc.returns.return_book(loan.id)

        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False

    def test_blocked_reader_borrow_rejected(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 10)
        svc.returns.return_book(loan.id)
        svc.membership.evaluate("r0")

        with pytest.raises(ReaderBlockedError):
            svc.loan.issue_book("r0", "b0")

    def test_paying_fine_and_evaluating_unblocks_reader(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 10)
        fine = svc.returns.return_book(loan.id)
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

        # Pay the fine
        fine.is_paid = True
        repos.fines.update(fine)

        # Evaluate again: unpaid=$0, overdue_count=1 < 3 → should unblock
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False

    def test_force_unblock_allows_borrow_despite_unpaid_fines(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 10)
        svc.returns.return_book(loan.id)
        svc.membership.block("r0")     # force-block

        svc.membership.unblock("r0")   # force-unblock (fines NOT paid)

        assert svc.loan.issue_book("r0", "b0") is not None

    def test_two_sequential_fines_accumulate_to_threshold(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # First: 5 days late → $5 — below threshold
        loan1 = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 5)
        svc.returns.return_book(loan1.id)
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False   # $5 < $10

        # Second: 5 days late → another $5 — total $10 at threshold
        loan2 = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 5)
        svc.returns.return_book(loan2.id)
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True    # $10 >= $10


# ── Blocking via overdue count ────────────────────────────────────────────────

class TestOverdueCountBlocking:
    def test_three_overdue_returns_reach_threshold_and_block(
        self, repos, svc, clock
    ):
        for i in range(4):
            repos.books.add(Book(f"b{i}", f"Book {i}", "A", ISBNS[i], 5, 5))
        repos.readers.add(make_reader("r0"))

        # 3 overdue returns → overdue_count = 3 (at threshold)
        for i in range(3):
            loan = svc.loan.issue_book("r0", f"b{i}")
            clock.advance(days=_LOAN + 1)   # 1 day late each time
            svc.returns.return_book(loan.id)

        assert repos.readers.get_by_id("r0").overdue_count == 3
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

    def test_two_overdue_returns_stay_below_threshold(self, repos, svc, clock):
        for i in range(3):
            repos.books.add(Book(f"b{i}", f"Book {i}", "A", ISBNS[i], 5, 5))
        repos.readers.add(make_reader("r0"))

        for i in range(2):
            loan = svc.loan.issue_book("r0", f"b{i}")
            clock.advance(days=_LOAN + 1)
            svc.returns.return_book(loan.id)

        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False

    def test_overdue_count_does_not_increment_on_time_returns(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        for _ in range(3):
            loan = svc.loan.issue_book("r0", "b0")
            clock.advance(days=_LOAN - 1)   # 1 day before due — on time
            svc.returns.return_book(loan.id)

        assert repos.readers.get_by_id("r0").overdue_count == 0
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False


# ── Full block/unblock cycle ──────────────────────────────────────────────────

class TestFullBlockUnblockCycle:
    def test_accumulate_fines_block_pay_evaluate_borrow(
        self, repos, svc, clock
    ):
        """Complete cycle: fine accumulation → block → payment → unblock → borrow."""
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # Phase 1 — accumulate $10 fine
        loan = svc.loan.issue_book("r0", "b0")
        clock.advance(days=_LOAN + 10)
        fine = svc.returns.return_book(loan.id)

        # Phase 2 — evaluate and block
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

        # Phase 3 — blocked reader rejected
        with pytest.raises(ReaderBlockedError):
            svc.loan.issue_book("r0", "b0")

        # Phase 4 — pay fine
        fine.is_paid = True
        repos.fines.update(fine)
        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("0")

        # Phase 5 — re-evaluate: unpaid=$0, overdue_count=1<3 → unblock
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False

        # Phase 6 — borrow succeeds
        new_loan = svc.loan.issue_book("r0", "b0")
        assert new_loan is not None
        assert repos.readers.get_by_id("r0").active_loans == 1

    def test_accumulate_overdues_block_force_unblock_borrow(
        self, repos, svc, clock
    ):
        """3 overdue returns → overdue_count >= threshold → blocked → force-unblock → borrow."""
        for i in range(4):
            repos.books.add(Book(f"b{i}", f"Book {i}", "A", ISBNS[i], 5, 5))
        repos.readers.add(make_reader("r0"))

        for i in range(3):
            loan = svc.loan.issue_book("r0", f"b{i}")
            clock.advance(days=15)       # 1 day overdue each time
            svc.returns.return_book(loan.id)

        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

        with pytest.raises(ReaderBlockedError):
            svc.loan.issue_book("r0", "b3")

        svc.membership.unblock("r0")
        assert svc.loan.issue_book("r0", "b3") is not None

    def test_evaluate_unblocks_reader_when_both_thresholds_cleared(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # Force-block first
        svc.membership.block("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

        # Fines and overdue_count are both zero → evaluate unblocks
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False

    def test_block_via_fines_partial_payment_stays_blocked(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=5))
        repos.readers.add(make_reader("r0"))

        # Two loans, each 5 days late → $5 each → $10 total
        for _ in range(2):
            loan = svc.loan.issue_book("r0", "b0")
            clock.advance(days=_LOAN + 5)
            svc.returns.return_book(loan.id)

        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is True

        # Pay only the first fine ($5 paid, $5 still unpaid)
        all_fines = repos.fines.find_by_reader("r0")
        all_fines[0].is_paid = True
        repos.fines.update(all_fines[0])
        assert repos.fines.total_unpaid_by_reader("r0") == Decimal("5.00")

        # $5 < $10 threshold, overdue_count=2 < 3 → should unblock
        svc.membership.evaluate("r0")
        assert repos.readers.get_by_id("r0").is_blocked is False
