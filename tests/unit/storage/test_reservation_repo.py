import pytest
from datetime import datetime, timedelta
from models.reservation import Reservation
from models.enums import ReservationStatus
from storage.memory.reservation_repo import InMemoryReservationRepository


_CREATED = datetime(2025, 6, 1, 10, 0, 0)
_EXPIRES = _CREATED + timedelta(days=3)


def _res(
    id_: str = "res1",
    book_id: str = "b1",
    reader_id: str = "r1",
    status: ReservationStatus = ReservationStatus.ACTIVE,
) -> Reservation:
    return Reservation(id=id_, book_id=book_id, reader_id=reader_id,
                       created_at=_CREATED, expires_at=_EXPIRES, status=status)


@pytest.fixture
def repo() -> InMemoryReservationRepository:
    return InMemoryReservationRepository()


@pytest.fixture
def reservation() -> Reservation:
    return _res()


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_stores_reservation(self, repo, reservation):
        repo.add(reservation)
        assert repo.get_by_id("res1") is reservation

    def test_add_duplicate_id_raises(self, repo, reservation):
        repo.add(reservation)
        with pytest.raises(ValueError, match="res1"):
            repo.add(reservation)

    def test_add_two_distinct_reservations(self, repo):
        repo.add(_res("res1"))
        repo.add(_res("res2"))
        assert len(repo.list_all()) == 2


class TestGetById:
    def test_existing_id_returns_reservation(self, repo, reservation):
        repo.add(reservation)
        assert repo.get_by_id("res1") is reservation

    def test_missing_id_returns_none(self, repo):
        assert repo.get_by_id("ghost") is None


class TestListAll:
    def test_empty_repo_returns_empty_list(self, repo):
        assert repo.list_all() == []

    def test_returns_all_reservations(self, repo):
        repo.add(_res("res1"))
        repo.add(_res("res2"))
        assert len(repo.list_all()) == 2

    def test_returns_defensive_copy(self, repo, reservation):
        repo.add(reservation)
        repo.list_all().clear()
        assert len(repo.list_all()) == 1


class TestUpdate:
    def test_update_changes_status(self, repo, reservation):
        repo.add(reservation)
        reservation.status = ReservationStatus.CANCELLED
        repo.update(reservation)
        assert repo.get_by_id("res1").status == ReservationStatus.CANCELLED

    def test_update_nonexistent_raises(self, repo, reservation):
        with pytest.raises(KeyError):
            repo.update(reservation)


class TestDelete:
    def test_delete_removes_reservation(self, repo, reservation):
        repo.add(reservation)
        repo.delete("res1")
        assert repo.get_by_id("res1") is None

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError):
            repo.delete("ghost")


# ── Query methods ─────────────────────────────────────────────────────────────

class TestFindByReader:
    def test_returns_reservations_for_reader(self, repo):
        repo.add(_res("res1", reader_id="r1"))
        repo.add(_res("res2", reader_id="r2"))
        result = repo.find_by_reader("r1")
        assert len(result) == 1 and result[0].id == "res1"

    def test_no_match_returns_empty(self, repo, reservation):
        repo.add(reservation)
        assert repo.find_by_reader("r99") == []

    def test_returns_all_statuses_for_reader(self, repo):
        repo.add(_res("res1", reader_id="r1", status=ReservationStatus.ACTIVE))
        repo.add(_res("res2", reader_id="r1", status=ReservationStatus.CANCELLED))
        assert len(repo.find_by_reader("r1")) == 2


class TestFindByBook:
    def test_returns_reservations_for_book(self, repo):
        repo.add(_res("res1", book_id="b1"))
        repo.add(_res("res2", book_id="b2"))
        assert len(repo.find_by_book("b1")) == 1

    def test_no_match_returns_empty(self, repo, reservation):
        repo.add(reservation)
        assert repo.find_by_book("b99") == []


class TestFindActive:
    def test_active_status_is_included(self, repo, reservation):
        repo.add(reservation)
        assert len(repo.find_active()) == 1

    def test_cancelled_is_excluded(self, repo):
        repo.add(_res("res1", status=ReservationStatus.CANCELLED))
        assert repo.find_active() == []

    def test_fulfilled_is_excluded(self, repo):
        repo.add(_res("res1", status=ReservationStatus.FULFILLED))
        assert repo.find_active() == []

    def test_expired_is_excluded(self, repo):
        repo.add(_res("res1", status=ReservationStatus.EXPIRED))
        assert repo.find_active() == []

    def test_mixed_returns_only_active(self, repo):
        repo.add(_res("res1", status=ReservationStatus.ACTIVE))
        repo.add(_res("res2", status=ReservationStatus.CANCELLED))
        assert len(repo.find_active()) == 1


class TestFindActiveByBook:
    def test_returns_active_for_book(self, repo):
        repo.add(_res("res1", book_id="b1"))
        repo.add(_res("res2", book_id="b2"))
        assert len(repo.find_active_by_book("b1")) == 1

    def test_excludes_non_active_for_book(self, repo):
        repo.add(_res("res1", book_id="b1", status=ReservationStatus.FULFILLED))
        repo.add(_res("res2", book_id="b1", status=ReservationStatus.EXPIRED))
        assert repo.find_active_by_book("b1") == []

    def test_no_match_returns_empty(self, repo):
        assert repo.find_active_by_book("b99") == []

    def test_does_not_include_active_for_other_book(self, repo):
        repo.add(_res("res1", book_id="b1"))
        repo.add(_res("res2", book_id="b2"))
        result = repo.find_active_by_book("b1")
        assert all(r.book_id == "b1" for r in result)
