"""Parametrized edge-case sweep for all business services.

Every repository and strategy is replaced by a pytest-mock MagicMock so each
test exercises only the service under test.  The parametrized axes follow the
assignment requirements exactly:

  - empty repositories
  - max loan limits (STANDARD=3, PREMIUM=5) and every boundary around them
  - blocked readers
  - zero / negative / boundary overdue days
  - expired vs active reservations
  - duplicate reservations
  - full vs zero available copies
  - fine-threshold and overdue-count thresholds for membership blocking
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from models.book import Book
from models.fine import Fine
from models.loan import Loan
from models.reader import Reader
from models.reservation import Reservation
from models.enums import MembershipType, ReservationStatus
from storage.interfaces import (
    LoanRepository, BookRepository, ReaderRepository,
    FineRepository, ReservationRepository,
)
from services.events import BookAvailabilitySubject
from services.fine_strategies import FineStrategy
from services.loan_service import LoanService
from services.return_service import ReturnService
from services.reservation_service import ReservationService
from services.membership_service import MembershipService
from utils.exceptions import (
    ReaderBlockedError,
    BookNotAvailableError,
    LoanLimitExceededError,
    DuplicateReservationError,
)

# ── Shared constants ──────────────────────────────────────────────────────────

_NOW    = datetime(2025, 6, 1, 10, 0, 0)
_ISSUED = datetime(2025, 5, 1, 10, 0, 0)
_DUE    = datetime(2025, 5, 15, 10, 0, 0)

# ── Object factories ──────────────────────────────────────────────────────────

def _book(available: int = 3) -> Book:
    total = max(available, 10)   # keep total_copies >= available_copies
    return Book("b1", "Title", "Author", "9780132350884", total, available)


def _reader(
    membership: MembershipType = MembershipType.STANDARD,
    is_blocked: bool = False,
    overdue_count: int = 0,
    active_loans: int = 0,
) -> Reader:
    return Reader("r1", "Alice", membership,
                  is_blocked=is_blocked,
                  overdue_count=overdue_count,
                  active_loans=active_loans)


def _open_loan() -> Loan:
    return Loan("l1", "b1", "r1", _ISSUED, _DUE)


def _reservation(
    res_id: str = "res1",
    reader_id: str = "r1",
    book_id: str = "b1",
    status: ReservationStatus = ReservationStatus.ACTIVE,
    created_at: datetime = _NOW,
) -> Reservation:
    return Reservation(
        id=res_id, book_id=book_id, reader_id=reader_id,
        created_at=created_at,
        expires_at=created_at + timedelta(days=3),
        status=status,
    )


# ── Service builder helpers ───────────────────────────────────────────────────

def _loan_svc(mocker, *, book=None, reader=None, active_loans=None):
    lr  = mocker.MagicMock(spec=LoanRepository)
    br  = mocker.MagicMock(spec=BookRepository)
    rr  = mocker.MagicMock(spec=ReaderRepository)
    lr.find_active_by_reader.return_value = (
        [MagicMock()] * active_loans if active_loans is not None else []
    )
    br.get_by_id.return_value  = book   if book   is not None else _book()
    rr.get_by_id.return_value  = reader if reader is not None else _reader()
    svc = LoanService(lr, br, rr, clock=lambda: _NOW)
    return svc, lr, br, rr


def _return_svc(mocker, *, fine_amount=Decimal("0"), return_time=_DUE,
                loan=None, reader=None):
    lr  = mocker.MagicMock(spec=LoanRepository)
    br  = mocker.MagicMock(spec=BookRepository)
    rr  = mocker.MagicMock(spec=ReaderRepository)
    fr  = mocker.MagicMock(spec=FineRepository)
    st  = mocker.MagicMock(spec=FineStrategy)
    bus = mocker.MagicMock(spec=BookAvailabilitySubject)
    lr.get_by_id.return_value  = loan   if loan   is not None else _open_loan()
    br.get_by_id.return_value  = _book(available=0)
    rr.get_by_id.return_value  = reader if reader is not None else _reader(active_loans=1)
    st.calculate.return_value  = fine_amount
    svc = ReturnService(lr, br, rr, fr, st, bus, clock=lambda: return_time)
    return svc, lr, br, rr, fr, st, bus


def _res_svc(mocker, *, active_for_book=None, all_active=None):
    rp  = mocker.MagicMock(spec=ReservationRepository)
    br  = mocker.MagicMock(spec=BookRepository)
    rr  = mocker.MagicMock(spec=ReaderRepository)
    rp.find_active_by_book.return_value = active_for_book if active_for_book is not None else []
    rp.find_active.return_value         = all_active      if all_active      is not None else []
    br.get_by_id.return_value           = _book()
    rr.get_by_id.return_value           = _reader()
    svc = ReservationService(rp, br, rr, expiry_days=3, clock=lambda: _NOW)
    return svc, rp, br, rr


def _mem_svc(mocker, *, unpaid=Decimal("0"), overdue_count=0, is_blocked=False):
    rr  = mocker.MagicMock(spec=ReaderRepository)
    fr  = mocker.MagicMock(spec=FineRepository)
    rr.get_by_id.return_value              = _reader(is_blocked=is_blocked,
                                                      overdue_count=overdue_count)
    fr.total_unpaid_by_reader.return_value = unpaid
    svc = MembershipService(rr, fr,
                             max_unpaid_amount=Decimal("10.00"),
                             max_overdue_count=3)
    return svc, rr, fr


# ═════════════════════════════════════════════════════════════════════════════
#  LoanService
# ═════════════════════════════════════════════════════════════════════════════

class TestLoanAvailableCopiesBoundaries:
    @pytest.mark.parametrize("available,raises", [
        (0,   True),   # zero copies — must raise
        (1,   False),  # exactly one copy — succeeds
        (2,   False),
        (10,  False),
        (100, False),
    ])
    def test_available_copies(self, available, raises, mocker):
        svc, *_ = _loan_svc(mocker, book=_book(available=available))
        if raises:
            with pytest.raises(BookNotAvailableError):
                svc.issue_book("r1", "b1")
        else:
            assert svc.issue_book("r1", "b1") is not None

    @pytest.mark.parametrize("available", [1, 2, 5])
    def test_available_copies_decremented_by_one(self, available, mocker):
        book = _book(available=available)
        svc, _, br, _ = _loan_svc(mocker, book=book)
        svc.issue_book("r1", "b1")
        assert book.available_copies == available - 1

    def test_empty_book_repo_raises_not_found(self, mocker):
        svc, _, br, _ = _loan_svc(mocker, book=None)
        br.get_by_id.return_value = None
        from utils.exceptions import BookNotFoundError
        with pytest.raises(BookNotFoundError):
            svc.issue_book("r1", "b1")


class TestLoanLimitBoundaries:
    @pytest.mark.parametrize("membership,active_count,raises", [
        # STANDARD limit = 3
        (MembershipType.STANDARD, 0, False),
        (MembershipType.STANDARD, 1, False),
        (MembershipType.STANDARD, 2, False),
        (MembershipType.STANDARD, 3, True),   # at limit → raise
        (MembershipType.STANDARD, 4, True),   # over limit
        # PREMIUM limit = 5
        (MembershipType.PREMIUM,  0, False),
        (MembershipType.PREMIUM,  3, False),  # 3 is fine for premium
        (MembershipType.PREMIUM,  4, False),
        (MembershipType.PREMIUM,  5, True),   # at limit → raise
        (MembershipType.PREMIUM,  6, True),   # over limit
    ])
    def test_loan_limit(self, membership, active_count, raises, mocker):
        svc, lr, _, _ = _loan_svc(
            mocker,
            reader=_reader(membership=membership),
            active_loans=active_count,
        )
        if raises:
            with pytest.raises(LoanLimitExceededError):
                svc.issue_book("r1", "b1")
        else:
            assert svc.issue_book("r1", "b1") is not None

    def test_empty_loan_repo_is_below_any_limit(self, mocker):
        """Empty active-loan list → count=0 → always below limit."""
        for membership in (MembershipType.STANDARD, MembershipType.PREMIUM):
            svc, *_ = _loan_svc(mocker, reader=_reader(membership=membership))
            assert svc.issue_book("r1", "b1") is not None


class TestLoanBlockedReader:
    @pytest.mark.parametrize("is_blocked,op_raises", [
        (True,  True),
        (False, False),
    ])
    def test_blocked_state(self, is_blocked, op_raises, mocker):
        svc, *_ = _loan_svc(mocker, reader=_reader(is_blocked=is_blocked))
        if op_raises:
            with pytest.raises(ReaderBlockedError):
                svc.issue_book("r1", "b1")
        else:
            assert svc.issue_book("r1", "b1") is not None

    def test_blocked_reader_does_not_consume_copy(self, mocker):
        book = _book(available=3)
        svc, _, br, _ = _loan_svc(mocker, book=book, reader=_reader(is_blocked=True))
        with pytest.raises(ReaderBlockedError):
            svc.issue_book("r1", "b1")
        br.update.assert_not_called()


class TestLoanDaysVariants:
    @pytest.mark.parametrize("loan_days", [1, 7, 14, 21, 30, 90, 365])
    def test_due_date_offset(self, loan_days, mocker):
        svc, *_ = _loan_svc(mocker)
        loan = svc.issue_book("r1", "b1", loan_days=loan_days)
        assert loan.due_date == _NOW + timedelta(days=loan_days)


# ═════════════════════════════════════════════════════════════════════════════
#  ReturnService
# ═════════════════════════════════════════════════════════════════════════════

class TestReturnOverdueDaysBoundaries:
    @pytest.mark.parametrize("days_delta,fine_amount,fine_expected", [
        (-7,  Decimal("0"),     False),  # returned 7 days early
        (-1,  Decimal("0"),     False),  # returned 1 day early
        (0,   Decimal("0"),     False),  # returned exactly on due date
        (1,   Decimal("2.00"),  True),   # 1 day late
        (5,   Decimal("10.00"), True),   # 5 days late
        (14,  Decimal("28.00"), True),   # 14 days late
        (30,  Decimal("60.00"), True),   # 30 days late
        (365, Decimal("730.00"), True),  # extreme overdue
    ])
    def test_fine_creation(self, days_delta, fine_amount, fine_expected, mocker):
        return_time = _DUE + timedelta(days=days_delta)
        svc, _, _, _, fr, st, _ = _return_svc(
            mocker, fine_amount=fine_amount, return_time=return_time,
        )
        result = svc.return_book("l1")
        if fine_expected:
            assert result is not None
            assert result.amount == fine_amount
            fr.add.assert_called_once()
        else:
            assert result is None
            fr.add.assert_not_called()

    @pytest.mark.parametrize("days_delta", [-7, -1, 0])
    def test_on_time_overdue_count_unchanged(self, days_delta, mocker):
        reader = _reader(active_loans=1, overdue_count=2)
        svc, *_ = _return_svc(
            mocker,
            fine_amount=Decimal("0"),
            return_time=_DUE + timedelta(days=days_delta),
            reader=reader,
        )
        svc.return_book("l1")
        assert reader.overdue_count == 2

    @pytest.mark.parametrize("days_late", [1, 3, 14])
    def test_overdue_increments_overdue_count(self, days_late, mocker):
        reader = _reader(active_loans=1, overdue_count=0)
        svc, *_ = _return_svc(
            mocker,
            fine_amount=Decimal("5.00"),
            return_time=_DUE + timedelta(days=days_late),
            reader=reader,
        )
        svc.return_book("l1")
        assert reader.overdue_count == 1


class TestReturnActiveLoanFloor:
    @pytest.mark.parametrize("starting_active,expected_after", [
        (0, 0),   # floor at zero — cannot go negative
        (1, 0),
        (2, 1),
        (5, 4),
    ])
    def test_active_loans_decrement_with_floor(
        self, starting_active, expected_after, mocker
    ):
        reader = _reader(active_loans=starting_active)
        svc, *_ = _return_svc(mocker, reader=reader)
        svc.return_book("l1")
        assert reader.active_loans == expected_after


class TestReturnStrategyReceivesDateObjects:
    @pytest.mark.parametrize("days_delta", [-5, 0, 7, 30])
    def test_strategy_called_with_date_not_datetime(self, days_delta, mocker):
        from datetime import date
        return_time = _DUE + timedelta(days=days_delta)
        svc, _, _, _, _, st, _ = _return_svc(mocker, return_time=return_time)
        svc.return_book("l1")
        due_arg, ret_arg = st.calculate.call_args[0]
        assert isinstance(due_arg, date) and not isinstance(due_arg, datetime)
        assert isinstance(ret_arg, date) and not isinstance(ret_arg, datetime)
        assert ret_arg == return_time.date()
        assert due_arg == _DUE.date()


# ═════════════════════════════════════════════════════════════════════════════
#  ReservationService
# ═════════════════════════════════════════════════════════════════════════════

class TestReservationExpiryBoundaries:
    """Verify expire_old() respects the expires_at boundary precisely."""

    @pytest.mark.parametrize("offset_seconds,should_expire", [
        (-1,    True),   # expired 1 second ago
        (0,     True),   # expires exactly now — boundary → expired
        (1,     False),  # expires 1 second in the future → still active
        (86400, False),  # expires tomorrow
    ])
    def test_expiry_boundary(self, offset_seconds, should_expire, mocker):
        svc, rp, _, _ = _res_svc(mocker)
        expires_at = _NOW + timedelta(seconds=offset_seconds)
        created_at = expires_at - timedelta(days=3)
        res = Reservation("res1", "b1", "r1", created_at, expires_at)
        rp.find_active.return_value = [res]
        result = svc.expire_old(as_of=_NOW)
        if should_expire:
            assert res in result
            assert res.status == ReservationStatus.EXPIRED
        else:
            assert res not in result
            assert res.status == ReservationStatus.ACTIVE


class TestNonActiveReservationsNotExpired:
    @pytest.mark.parametrize("status", [
        ReservationStatus.CANCELLED,
        ReservationStatus.FULFILLED,
        ReservationStatus.EXPIRED,
    ])
    def test_non_active_not_returned_by_find_active(self, status, mocker):
        """find_active() only returns ACTIVE reservations, so these are never
        seen by expire_old — verified here via a real in-memory repo."""
        from storage.memory.reservation_repo import InMemoryReservationRepository
        repo = InMemoryReservationRepository()
        res = _reservation(status=status, created_at=_NOW - timedelta(days=100))
        repo.add(res)
        # find_active must not return this entry
        assert repo.find_active() == []


class TestReservationPriorityQueue:
    @pytest.mark.parametrize("memberships_by_age,expected_winner_idx", [
        # ([(membership, age_hours)], idx of winner in list)
        ([(MembershipType.PREMIUM, 1), (MembershipType.STANDARD, 0)], 0),  # PREMIUM wins despite being newer
        ([(MembershipType.STANDARD, 0), (MembershipType.PREMIUM, 1)], 1),  # PREMIUM wins even though it's second
        ([(MembershipType.PREMIUM, 0), (MembershipType.PREMIUM, 1)],  1),  # both PREMIUM → older created_at (age_hours=1, idx=1) wins
        ([(MembershipType.STANDARD, 0), (MembershipType.STANDARD, 1)], 1), # both STANDARD → older created_at (idx=1) wins
    ])
    def test_priority_order(self, memberships_by_age, expected_winner_idx, mocker):
        rp  = mocker.MagicMock(spec=ReservationRepository)
        br  = mocker.MagicMock(spec=BookRepository)
        rr  = mocker.MagicMock(spec=ReaderRepository)
        br.get_by_id.return_value = _book()

        readers = {}
        reservations = []
        for idx, (membership, age_hours) in enumerate(memberships_by_age):
            rid = f"r{idx}"
            readers[rid] = _reader(membership=membership)
            reservations.append(
                Reservation(
                    f"res{idx}", "b1", rid,
                    created_at=_NOW - timedelta(hours=age_hours),
                    expires_at=_NOW + timedelta(days=3),
                )
            )

        rp.find_active_by_book.return_value = reservations
        rr.get_by_id.side_effect = lambda rid: readers.get(rid)
        svc = ReservationService(rp, br, rr, clock=lambda: _NOW)
        result = svc.get_next_in_queue("b1")
        assert result is reservations[expected_winner_idx]


class TestDuplicateReservation:
    @pytest.mark.parametrize("same_reader,same_book,should_raise", [
        (True,  True,  True),   # exact duplicate → raise
        (True,  False, False),  # same reader, different book → OK
        (False, True,  False),  # different reader, same book → OK
        (False, False, False),  # entirely different → OK
    ])
    def test_duplicate_detection(
        self, same_reader, same_book, should_raise, mocker
    ):
        svc, rp, br, rr = _res_svc(mocker)
        existing_reader = "r1" if same_reader else "r2"
        existing_book   = "b1" if same_book   else "b2"
        existing_res    = _reservation(reader_id=existing_reader, book_id=existing_book)
        # Only return the existing reservation when the queried book matches
        rp.find_active_by_book.side_effect = (
            lambda bid: [existing_res] if bid == existing_book else []
        )
        if should_raise:
            with pytest.raises(DuplicateReservationError):
                svc.reserve("r1", "b1")
        else:
            assert svc.reserve("r1", "b1") is not None

    def test_can_reserve_after_cancellation(self, mocker):
        """A CANCELLED reservation for the same reader+book is not a duplicate."""
        svc, rp, _, _ = _res_svc(mocker)
        # find_active_by_book returns [] because cancelled items are not active
        rp.find_active_by_book.return_value = []
        assert svc.reserve("r1", "b1") is not None


class TestBlockedReaderCannotReserve:
    def test_blocked_reader_raises(self, mocker):
        svc, rp, br, rr = _res_svc(mocker)
        rr.get_by_id.return_value = _reader(is_blocked=True)
        with pytest.raises(ReaderBlockedError):
            svc.reserve("r1", "b1")


class TestEmptyReservationRepo:
    def test_get_next_in_queue_empty(self, mocker):
        svc, rp, _, _ = _res_svc(mocker)
        rp.find_active_by_book.return_value = []
        assert svc.get_next_in_queue("b1") is None

    def test_expire_old_empty(self, mocker):
        svc, rp, _, _ = _res_svc(mocker)
        rp.find_active.return_value = []
        assert svc.expire_old(as_of=_NOW) == []


# ═════════════════════════════════════════════════════════════════════════════
#  MembershipService
# ═════════════════════════════════════════════════════════════════════════════

class TestMembershipUnpaidFineThresholds:
    @pytest.mark.parametrize("unpaid,expected_blocked", [
        (Decimal("0.00"),  False),   # no fines
        (Decimal("9.99"),  False),   # just below threshold
        (Decimal("10.00"), True),    # exactly at threshold → blocked
        (Decimal("10.01"), True),    # just above
        (Decimal("100.00"), True),   # far above
    ])
    def test_fine_threshold(self, unpaid, expected_blocked, mocker):
        svc, rr, _ = _mem_svc(mocker, unpaid=unpaid)
        assert svc.evaluate("r1") == expected_blocked
        assert rr.get_by_id.return_value.is_blocked == expected_blocked


class TestMembershipOverdueCountThresholds:
    @pytest.mark.parametrize("overdue_count,expected_blocked", [
        (0, False),
        (1, False),
        (2, False),
        (3, True),    # at threshold
        (4, True),
        (10, True),
    ])
    def test_overdue_threshold(self, overdue_count, expected_blocked, mocker):
        svc, rr, _ = _mem_svc(mocker, overdue_count=overdue_count)
        assert svc.evaluate("r1") == expected_blocked

    def test_zero_overdue_zero_fine_does_not_block(self, mocker):
        svc, rr, _ = _mem_svc(mocker, unpaid=Decimal("0"), overdue_count=0)
        assert svc.evaluate("r1") is False
        assert rr.get_by_id.return_value.is_blocked is False


class TestMembershipCombinedThresholds:
    @pytest.mark.parametrize("unpaid,overdue_count,expected_blocked", [
        (Decimal("0"),  0, False),   # both clear
        (Decimal("0"),  3, True),    # only overdue triggers
        (Decimal("10"), 0, True),    # only fine triggers
        (Decimal("10"), 3, True),    # both trigger
        (Decimal("9.99"), 2, False), # both just below
    ])
    def test_combined(self, unpaid, overdue_count, expected_blocked, mocker):
        svc, *_ = _mem_svc(mocker, unpaid=unpaid, overdue_count=overdue_count)
        assert svc.evaluate("r1") == expected_blocked


class TestMembershipUnblocksBelowThreshold:
    @pytest.mark.parametrize("was_blocked,unpaid,overdue_count,still_blocked", [
        (True,  Decimal("0"),    0, False),  # was blocked, now clear → unblocked
        (True,  Decimal("10"),   0, True),   # still has fine → stays blocked
        (True,  Decimal("0"),    3, True),   # still overdue → stays blocked
        (False, Decimal("0"),    0, False),  # was fine, stays fine
    ])
    def test_evaluate_unblocks(
        self, was_blocked, unpaid, overdue_count, still_blocked, mocker
    ):
        reader = _reader(is_blocked=was_blocked, overdue_count=overdue_count)
        rr  = mocker.MagicMock(spec=ReaderRepository)
        fr  = mocker.MagicMock(spec=FineRepository)
        rr.get_by_id.return_value              = reader
        fr.total_unpaid_by_reader.return_value = unpaid
        svc = MembershipService(rr, fr,
                                 max_unpaid_amount=Decimal("10.00"),
                                 max_overdue_count=3)
        svc.evaluate("r1")
        assert reader.is_blocked == still_blocked
