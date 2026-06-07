import pytest
from models.enums import BookStatus, MembershipType, ReservationStatus


class TestBookStatus:
    def test_available_value(self):
        assert BookStatus.AVAILABLE.value == "available"

    def test_unavailable_value(self):
        assert BookStatus.UNAVAILABLE.value == "unavailable"

    def test_reserved_value(self):
        assert BookStatus.RESERVED.value == "reserved"

    def test_lost_value(self):
        assert BookStatus.LOST.value == "lost"

    def test_maintenance_value(self):
        assert BookStatus.MAINTENANCE.value == "maintenance"

    def test_member_count(self):
        assert len(BookStatus) == 5

    def test_lookup_by_value(self):
        assert BookStatus("available") is BookStatus.AVAILABLE


class TestMembershipType:
    def test_premium_value(self):
        assert MembershipType.PREMIUM.value == "premium"

    def test_standard_value(self):
        assert MembershipType.STANDARD.value == "standard"

    def test_member_count(self):
        assert len(MembershipType) == 2

    def test_lookup_by_value(self):
        assert MembershipType("premium") is MembershipType.PREMIUM


class TestReservationStatus:
    def test_active_value(self):
        assert ReservationStatus.ACTIVE.value == "active"

    def test_fulfilled_value(self):
        assert ReservationStatus.FULFILLED.value == "fulfilled"

    def test_cancelled_value(self):
        assert ReservationStatus.CANCELLED.value == "cancelled"

    def test_expired_value(self):
        assert ReservationStatus.EXPIRED.value == "expired"

    def test_member_count(self):
        assert len(ReservationStatus) == 4

    def test_lookup_by_value(self):
        assert ReservationStatus("cancelled") is ReservationStatus.CANCELLED
