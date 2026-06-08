import pytest
from datetime import datetime, timedelta
from models.queue_request import QueueRequest
from models.enums import QueueRequestStatus


@pytest.fixture
def valid_request() -> QueueRequest:
    created = datetime(2025, 9, 1, 10, 0)
    return QueueRequest(
        id="qr1",
        student_id="s1",
        team_id="t1",
        created_at=created,
        expires_at=created + timedelta(days=7),
    )


class TestQueueRequestCreation:
    def test_all_fields_set(self, valid_request):
        assert valid_request.id == "qr1"
        assert valid_request.student_id == "s1"
        assert valid_request.team_id == "t1"

    def test_default_status_pending(self, valid_request):
        assert valid_request.status == QueueRequestStatus.PENDING

    def test_explicit_status_fulfilled(self):
        now = datetime(2025, 9, 1)
        r = QueueRequest("qr2", "s2", "t2", now, now + timedelta(days=7),
                         QueueRequestStatus.FULFILLED)
        assert r.status == QueueRequestStatus.FULFILLED

    def test_explicit_status_expired(self):
        now = datetime(2025, 9, 1)
        r = QueueRequest("qr3", "s3", "t3", now, now + timedelta(days=7),
                         QueueRequestStatus.EXPIRED)
        assert r.status == QueueRequestStatus.EXPIRED

    def test_explicit_status_cancelled(self):
        now = datetime(2025, 9, 1)
        r = QueueRequest("qr4", "s4", "t4", now, now + timedelta(days=7),
                         QueueRequestStatus.CANCELLED)
        assert r.status == QueueRequestStatus.CANCELLED

    def test_expires_at_stored_correctly(self, valid_request):
        expected = datetime(2025, 9, 1, 10, 0) + timedelta(days=7)
        assert valid_request.expires_at == expected


class TestQueueRequestIdValidation:
    def test_empty_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="id"):
            QueueRequest("", "s1", "t1", now, now + timedelta(days=7))

    def test_whitespace_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="id"):
            QueueRequest("   ", "s1", "t1", now, now + timedelta(days=7))


class TestQueueRequestStudentIdValidation:
    def test_empty_student_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="student_id"):
            QueueRequest("qr1", "", "t1", now, now + timedelta(days=7))

    def test_whitespace_student_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="student_id"):
            QueueRequest("qr1", "   ", "t1", now, now + timedelta(days=7))


class TestQueueRequestTeamIdValidation:
    def test_empty_team_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="team_id"):
            QueueRequest("qr1", "s1", "", now, now + timedelta(days=7))

    def test_whitespace_team_id_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="team_id"):
            QueueRequest("qr1", "s1", "   ", now, now + timedelta(days=7))


class TestQueueRequestExpiryValidation:
    def test_expires_at_equal_to_created_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="expires_at"):
            QueueRequest("qr1", "s1", "t1", now, now)

    def test_expires_at_before_created_raises(self):
        now = datetime(2025, 9, 1)
        with pytest.raises(ValueError, match="expires_at"):
            QueueRequest("qr1", "s1", "t1", now, now - timedelta(days=1))

    def test_expires_at_one_second_after_created_valid(self):
        now = datetime(2025, 9, 1)
        r = QueueRequest("qr1", "s1", "t1", now, now + timedelta(seconds=1))
        assert r.expires_at > r.created_at
