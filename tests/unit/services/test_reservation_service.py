"""TDD unit tests for ReservationService — all repos mocked."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

from models.book import Book
from models.reader import Reader
from models.reservation import Reservation
from models.enums import MembershipType, ReservationStatus
from storage.interfaces import ReservationRepository, BookRepository, ReaderRepository
from services.reservation_service import ReservationService
from utils.exceptions import (
    ReaderNotFoundError, BookNotFoundError, ReaderBlockedError,
    DuplicateReservationError, ReservationNotFoundError,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_NOW = datetime(2025, 6, 1, 10, 0, 0)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _reader(
    reader_id: str = "r1",
    membership: MembershipType = MembershipType.STANDARD,
    is_blocked: bool = False,
) -> Reader:
    return Reader(reader_id, "Alice", membership, is_blocked=is_blocked)


def _book(book_id: str = "b1") -> Book:
    return Book(book_id, "Title", "Author", "9780132350884", 3, 0)


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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def res_repo(mocker):
    m = mocker.MagicMock(spec=ReservationRepository)
    m.find_active_by_book.return_value = []
    m.find_active.return_value = []
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
def svc(res_repo, book_repo, reader_repo) -> ReservationService:
    return ReservationService(res_repo, book_repo, reader_repo,
                              expiry_days=3, clock=lambda: _NOW)


# ── reserve() — validation ────────────────────────────────────────────────────

class TestReserveValidation:
    def test_reader_not_found_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = None
        with pytest.raises(ReaderNotFoundError):
            svc.reserve("r1", "b1")

    def test_reader_blocked_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = _reader(is_blocked=True)
        with pytest.raises(ReaderBlockedError):
            svc.reserve("r1", "b1")

    def test_book_not_found_raises(self, svc, book_repo):
        book_repo.get_by_id.return_value = None
        with pytest.raises(BookNotFoundError):
            svc.reserve("r1", "b1")

    def test_duplicate_active_reservation_raises(self, svc, res_repo):
        res_repo.find_active_by_book.return_value = [_reservation(reader_id="r1")]
        with pytest.raises(DuplicateReservationError):
            svc.reserve("r1", "b1")

    def test_existing_reservation_for_other_reader_does_not_block(self, svc, res_repo):
        res_repo.find_active_by_book.return_value = [_reservation(reader_id="r2")]
        assert svc.reserve("r1", "b1") is not None


# ── reserve() — success ───────────────────────────────────────────────────────

class TestReserveSuccess:
    def test_returns_reservation_with_correct_ids(self, svc):
        res = svc.reserve("r1", "b1")
        assert res.reader_id == "r1" and res.book_id == "b1"

    def test_created_at_from_clock(self, svc):
        assert svc.reserve("r1", "b1").created_at == _NOW

    def test_expires_at_is_clock_plus_expiry_days(self, svc):
        assert svc.reserve("r1", "b1").expires_at == _NOW + timedelta(days=3)

    def test_custom_expiry_days(self, res_repo, book_repo, reader_repo):
        svc7 = ReservationService(res_repo, book_repo, reader_repo,
                                   expiry_days=7, clock=lambda: _NOW)
        assert svc7.reserve("r1", "b1").expires_at == _NOW + timedelta(days=7)

    def test_status_is_active(self, svc):
        assert svc.reserve("r1", "b1").status == ReservationStatus.ACTIVE

    def test_reservation_added_to_repo(self, svc, res_repo):
        res = svc.reserve("r1", "b1")
        res_repo.add.assert_called_once_with(res)

    def test_non_empty_id_generated(self, svc):
        assert svc.reserve("r1", "b1").id.strip()


# ── cancel() ──────────────────────────────────────────────────────────────────

class TestCancel:
    def test_not_found_raises(self, svc, res_repo):
        res_repo.get_by_id.return_value = None
        with pytest.raises(ReservationNotFoundError):
            svc.cancel("res1")

    def test_sets_status_to_cancelled(self, svc, res_repo):
        res = _reservation()
        res_repo.get_by_id.return_value = res
        svc.cancel("res1")
        assert res.status == ReservationStatus.CANCELLED

    def test_repo_updated(self, svc, res_repo):
        res_repo.get_by_id.return_value = _reservation()
        svc.cancel("res1")
        res_repo.update.assert_called_once()


# ── expire_old() ──────────────────────────────────────────────────────────────

class TestExpireOld:
    def test_reservation_past_expiry_is_expired(self, svc, res_repo):
        expired_res = _reservation(created_at=_NOW - timedelta(days=10))
        # expires_at = created_at + 3 days = _NOW - 7 days → past
        res_repo.find_active.return_value = [expired_res]
        result = svc.expire_old(as_of=_NOW)
        assert expired_res.status == ReservationStatus.EXPIRED
        assert expired_res in result

    def test_reservation_not_yet_expired_stays_active(self, svc, res_repo):
        fresh = _reservation(created_at=_NOW)   # expires _NOW+3, checked at _NOW
        res_repo.find_active.return_value = [fresh]
        result = svc.expire_old(as_of=_NOW)
        assert fresh.status == ReservationStatus.ACTIVE
        assert fresh not in result

    def test_exactly_at_expiry_is_expired(self, svc, res_repo):
        res = _reservation(created_at=_NOW - timedelta(days=3))
        # expires_at = _NOW exactly
        res_repo.find_active.return_value = [res]
        result = svc.expire_old(as_of=_NOW)
        assert res.status == ReservationStatus.EXPIRED
        assert res in result

    def test_returns_only_newly_expired(self, svc, res_repo):
        old = _reservation("res1", created_at=_NOW - timedelta(days=10))
        new = _reservation("res2", created_at=_NOW)
        res_repo.find_active.return_value = [old, new]
        result = svc.expire_old(as_of=_NOW)
        assert len(result) == 1 and result[0] is old

    def test_uses_clock_when_as_of_not_provided(self, res_repo, book_repo, reader_repo):
        clock_time = _NOW
        svc = ReservationService(res_repo, book_repo, reader_repo,
                                  expiry_days=3, clock=lambda: clock_time)
        old_res = _reservation(created_at=clock_time - timedelta(days=10))
        res_repo.find_active.return_value = [old_res]
        result = svc.expire_old()   # no as_of — must use clock
        assert old_res in result

    def test_updates_repo_for_each_expired(self, svc, res_repo):
        r1 = _reservation("res1", created_at=_NOW - timedelta(days=10))
        r2 = _reservation("res2", created_at=_NOW - timedelta(days=10))
        res_repo.find_active.return_value = [r1, r2]
        svc.expire_old(as_of=_NOW)
        assert res_repo.update.call_count == 2

    def test_empty_list_returned_when_none_expired(self, svc, res_repo):
        res_repo.find_active.return_value = []
        assert svc.expire_old(as_of=_NOW) == []


# ── get_next_in_queue() ───────────────────────────────────────────────────────

class TestGetNextInQueue:
    def test_no_reservations_returns_none(self, svc, res_repo):
        res_repo.find_active_by_book.return_value = []
        assert svc.get_next_in_queue("b1") is None

    def test_single_active_reservation_returned(self, svc, res_repo, reader_repo):
        res = _reservation()
        res_repo.find_active_by_book.return_value = [res]
        reader_repo.get_by_id.return_value = _reader()
        assert svc.get_next_in_queue("b1") is res

    def test_premium_before_standard_regardless_of_age(self, res_repo, book_repo, reader_repo):
        """PREMIUM reader with newer reservation beats STANDARD with older one."""
        std_res = _reservation("res1", "r-std", created_at=_NOW)
        pre_res = _reservation("res2", "r-pre", created_at=_NOW + timedelta(hours=1))
        res_repo.find_active_by_book.return_value = [std_res, pre_res]
        reader_repo.get_by_id.side_effect = lambda rid: {
            "r-std": _reader("r-std", MembershipType.STANDARD),
            "r-pre": _reader("r-pre", MembershipType.PREMIUM),
        }.get(rid)
        svc = ReservationService(res_repo, book_repo, reader_repo,
                                  clock=lambda: _NOW)
        assert svc.get_next_in_queue("b1") is pre_res

    def test_oldest_first_within_standard(self, res_repo, book_repo, reader_repo):
        r1 = _reservation("res1", "r1", created_at=_NOW)
        r2 = _reservation("res2", "r2", created_at=_NOW + timedelta(hours=2))
        res_repo.find_active_by_book.return_value = [r2, r1]
        reader_repo.get_by_id.return_value = _reader(membership=MembershipType.STANDARD)
        svc = ReservationService(res_repo, book_repo, reader_repo, clock=lambda: _NOW)
        assert svc.get_next_in_queue("b1") is r1

    def test_oldest_first_within_premium(self, res_repo, book_repo, reader_repo):
        r1 = _reservation("res1", "r1", created_at=_NOW)
        r2 = _reservation("res2", "r2", created_at=_NOW + timedelta(hours=1))
        res_repo.find_active_by_book.return_value = [r2, r1]
        reader_repo.get_by_id.return_value = _reader(membership=MembershipType.PREMIUM)
        svc = ReservationService(res_repo, book_repo, reader_repo, clock=lambda: _NOW)
        assert svc.get_next_in_queue("b1") is r1

    def test_unknown_reader_defaults_to_standard_rank(self, res_repo, book_repo, reader_repo):
        ghost = _reservation("res1", "ghost", created_at=_NOW)
        premium = _reservation("res2", "r-pre", created_at=_NOW + timedelta(hours=1))
        res_repo.find_active_by_book.return_value = [ghost, premium]
        reader_repo.get_by_id.side_effect = lambda rid: (
            _reader(rid, MembershipType.PREMIUM) if rid == "r-pre" else None
        )
        svc = ReservationService(res_repo, book_repo, reader_repo, clock=lambda: _NOW)
        assert svc.get_next_in_queue("b1") is premium

    def test_queries_repo_with_correct_book_id(self, svc, res_repo, reader_repo):
        res_repo.find_active_by_book.return_value = []
        svc.get_next_in_queue("b99")
        res_repo.find_active_by_book.assert_called_once_with("b99")
