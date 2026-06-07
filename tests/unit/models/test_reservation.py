import pytest
from datetime import datetime, timedelta
from models.reservation import Reservation
from models.enums import ReservationStatus


_CREATED = datetime(2025, 6, 1, 10, 0, 0)
_EXPIRES = _CREATED + timedelta(days=3)


@pytest.fixture
def active_reservation() -> Reservation:
    return Reservation(
        id="res1",
        book_id="b1",
        reader_id="r1",
        created_at=_CREATED,
        expires_at=_EXPIRES,
    )


class TestReservationCreation:
    def test_all_fields_set_correctly(self, active_reservation: Reservation):
        assert active_reservation.id == "res1"
        assert active_reservation.book_id == "b1"
        assert active_reservation.reader_id == "r1"
        assert active_reservation.created_at == _CREATED
        assert active_reservation.expires_at == _EXPIRES

    def test_default_status_is_active(self, active_reservation: Reservation):
        assert active_reservation.status == ReservationStatus.ACTIVE

    def test_explicit_status_fulfilled(self):
        r = Reservation("res2", "b1", "r1", _CREATED, _EXPIRES, ReservationStatus.FULFILLED)
        assert r.status == ReservationStatus.FULFILLED

    def test_explicit_status_cancelled(self):
        r = Reservation("res3", "b1", "r1", _CREATED, _EXPIRES, ReservationStatus.CANCELLED)
        assert r.status == ReservationStatus.CANCELLED

    def test_explicit_status_expired(self):
        r = Reservation("res4", "b1", "r1", _CREATED, _EXPIRES, ReservationStatus.EXPIRED)
        assert r.status == ReservationStatus.EXPIRED

    def test_expires_one_second_after_created_is_valid(self):
        r = Reservation("res5", "b1", "r1", _CREATED, _CREATED + timedelta(seconds=1))
        assert r.expires_at == _CREATED + timedelta(seconds=1)

    def test_long_expiry_window_is_valid(self):
        r = Reservation("res6", "b1", "r1", _CREATED, _CREATED + timedelta(days=30))
        assert r.expires_at == _CREATED + timedelta(days=30)


class TestReservationIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Reservation("", "b1", "r1", _CREATED, _EXPIRES)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Reservation("  ", "b1", "r1", _CREATED, _EXPIRES)

    def test_empty_book_id_raises(self):
        with pytest.raises(ValueError, match="book_id"):
            Reservation("res1", "", "r1", _CREATED, _EXPIRES)

    def test_empty_reader_id_raises(self):
        with pytest.raises(ValueError, match="reader_id"):
            Reservation("res1", "b1", "", _CREATED, _EXPIRES)


class TestReservationDateValidation:
    def test_expires_before_created_raises(self):
        with pytest.raises(ValueError, match="expires_at"):
            Reservation("res1", "b1", "r1", _CREATED, _CREATED - timedelta(days=1))

    def test_expires_equal_to_created_raises(self):
        with pytest.raises(ValueError, match="expires_at"):
            Reservation("res1", "b1", "r1", _CREATED, _CREATED)

    def test_expires_one_second_before_created_raises(self):
        with pytest.raises(ValueError, match="expires_at"):
            Reservation("res1", "b1", "r1", _CREATED, _CREATED - timedelta(seconds=1))
