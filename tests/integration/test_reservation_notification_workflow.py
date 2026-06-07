"""Integration tests: reserve a borrowed book → return → eligible reader notified → borrows.

Verifies the full Observer chain:
  ReturnService → EventBus → ReaderNotifier → Notification recorded.

Priority rule under test: PREMIUM before STANDARD; ties broken by earliest created_at.
All services and repositories are real; no mocks.
"""
import pytest
from decimal import Decimal

from models.enums import MembershipType, ReservationStatus
from utils.exceptions import BookNotAvailableError, DuplicateReservationError
from tests.integration.conftest import make_book, make_reader


# ── Basic reservation and single-reader notification ─────────────────────────

class TestBasicReservationNotification:
    def test_reservation_created_with_active_status(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))
        svc.loan.issue_book("borrower", "b0")
        res = svc.reservation.reserve("waiter", "b0")
        assert res.status == ReservationStatus.ACTIVE

    def test_single_reservation_notified_when_book_returned(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("waiter", "b0")
        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        notifs = svc.notifier.get_notifications()
        assert len(notifs) == 1
        assert notifs[0].reader_id == "waiter"
        assert notifs[0].book_id == "b0"

    def test_no_reservation_means_no_notification(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        loan = svc.loan.issue_book("borrower", "b0")
        clock.advance(days=7)
        svc.returns.return_book(loan.id)
        assert svc.notifier.get_notifications() == []

    def test_notified_reader_can_borrow_returned_book(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("waiter", "b0")
        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        # waiter was notified and can now borrow
        new_loan = svc.loan.issue_book("waiter", "b0")
        assert new_loan is not None
        assert repos.books.get_by_id("b0").available_copies == 0

    def test_available_copies_positive_after_return_before_borrow(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        loan = svc.loan.issue_book("borrower", "b0")
        clock.advance(days=7)
        svc.returns.return_book(loan.id)
        assert repos.books.get_by_id("b0").available_copies == 1


# ── Priority queue: PREMIUM before STANDARD ──────────────────────────────────

class TestPriorityQueueNotification:
    def test_premium_beats_standard_even_when_standard_reserved_first(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("std", MembershipType.STANDARD))
        repos.readers.add(make_reader("prm", MembershipType.PREMIUM))

        loan = svc.loan.issue_book("borrower", "b0")

        # STANDARD reserves first (older created_at)
        svc.reservation.reserve("std", "b0")
        clock.advance(hours=1)
        # PREMIUM reserves second (newer created_at)
        svc.reservation.reserve("prm", "b0")

        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        notifs = svc.notifier.get_notifications()
        assert len(notifs) == 1
        assert notifs[0].reader_id == "prm"    # PREMIUM wins despite joining later

    def test_older_standard_beats_newer_standard(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("std_early", MembershipType.STANDARD))
        repos.readers.add(make_reader("std_late",  MembershipType.STANDARD))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("std_early", "b0")
        clock.advance(hours=2)
        svc.reservation.reserve("std_late", "b0")

        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        assert svc.notifier.get_notifications()[0].reader_id == "std_early"

    def test_older_premium_beats_newer_premium(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("prm_early", MembershipType.PREMIUM))
        repos.readers.add(make_reader("prm_late",  MembershipType.PREMIUM))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("prm_early", "b0")
        clock.advance(hours=1)
        svc.reservation.reserve("prm_late", "b0")

        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        assert svc.notifier.get_notifications()[0].reader_id == "prm_early"

    def test_full_premium_beats_standard_then_premium_borrows(
        self, repos, svc, clock
    ):
        """End-to-end: PREMIUM notified → PREMIUM borrows → STANDARD still blocked."""
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("std", MembershipType.STANDARD))
        repos.readers.add(make_reader("prm", MembershipType.PREMIUM))

        # Initial borrow takes the only copy
        loan = svc.loan.issue_book("borrower", "b0")

        # STANDARD reserves first, PREMIUM one hour later
        svc.reservation.reserve("std", "b0")
        clock.advance(hours=1)
        svc.reservation.reserve("prm", "b0")

        # Return
        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        # Notification went to PREMIUM
        assert svc.notifier.get_notifications()[0].reader_id == "prm"

        # PREMIUM borrows — copy taken
        prm_loan = svc.loan.issue_book("prm", "b0")
        assert prm_loan is not None
        assert repos.books.get_by_id("b0").available_copies == 0

        # STANDARD still cannot borrow
        with pytest.raises(BookNotAvailableError):
            svc.loan.issue_book("std", "b0")


# ── Cancellation and expiry remove readers from queue ────────────────────────

class TestCancellationAndExpiry:
    def test_cancelled_reservation_excluded_from_notification(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("std_cancel", MembershipType.STANDARD))
        repos.readers.add(make_reader("std_keep",   MembershipType.STANDARD))

        loan = svc.loan.issue_book("borrower", "b0")
        res_to_cancel = svc.reservation.reserve("std_cancel", "b0")
        svc.reservation.reserve("std_keep", "b0")

        svc.reservation.cancel(res_to_cancel.id)

        clock.advance(days=7)
        svc.returns.return_book(loan.id)

        notifs = svc.notifier.get_notifications()
        assert len(notifs) == 1
        assert notifs[0].reader_id == "std_keep"

    def test_duplicate_reservation_rejected(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))

        svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("waiter", "b0")

        with pytest.raises(DuplicateReservationError):
            svc.reservation.reserve("waiter", "b0")

    def test_can_re_reserve_after_cancellation(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))

        svc.loan.issue_book("borrower", "b0")
        res = svc.reservation.reserve("waiter", "b0")
        svc.reservation.cancel(res.id)

        # Re-reserve is allowed after cancellation
        new_res = svc.reservation.reserve("waiter", "b0")
        assert new_res.status == ReservationStatus.ACTIVE

    def test_expired_reservations_removed_from_queue(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("w1"))
        repos.readers.add(make_reader("w2"))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("w1", "b0")
        svc.reservation.reserve("w2", "b0")

        # Advance past the 3-day expiry window then run cleanup
        clock.advance(days=4)
        expired = svc.reservation.expire_old()
        assert len(expired) == 2
        for r in expired:
            assert r.status == ReservationStatus.EXPIRED

        # Return the book — no active reservations left → no notification
        svc.returns.return_book(loan.id)
        assert svc.notifier.get_notifications() == []

    def test_non_expired_reservation_survives_cleanup(self, repos, svc, clock):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("waiter"))

        loan = svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("waiter", "b0")

        # Advance only 2 days (below 3-day expiry)
        clock.advance(days=2)
        expired = svc.reservation.expire_old()
        assert expired == []

        svc.returns.return_book(loan.id)
        assert svc.notifier.get_notifications()[0].reader_id == "waiter"

    def test_reservation_service_get_next_in_queue_respects_priority(
        self, repos, svc, clock
    ):
        repos.books.add(make_book("b0", copies=1))
        repos.readers.add(make_reader("borrower"))
        repos.readers.add(make_reader("std",  MembershipType.STANDARD))
        repos.readers.add(make_reader("prm",  MembershipType.PREMIUM))

        svc.loan.issue_book("borrower", "b0")
        svc.reservation.reserve("std", "b0")
        clock.advance(hours=1)
        svc.reservation.reserve("prm", "b0")

        next_res = svc.reservation.get_next_in_queue("b0")
        assert next_res is not None
        assert next_res.reader_id == "prm"
