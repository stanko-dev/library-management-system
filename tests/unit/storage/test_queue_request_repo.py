import pytest
from datetime import datetime, timedelta
from models.queue_request import QueueRequest
from models.enums import QueueRequestStatus
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository


_BASE = datetime(2025, 9, 1, 10, 0)


def make_request(rid: str = "qr1", student_id: str = "s1", team_id: str = "t1",
                 status: QueueRequestStatus = QueueRequestStatus.PENDING) -> QueueRequest:
    return QueueRequest(id=rid, student_id=student_id, team_id=team_id,
                        created_at=_BASE, expires_at=_BASE + timedelta(days=7),
                        status=status)


class TestInMemoryQueueRequestRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryQueueRequestRepository()
        r = make_request()
        repo.add(r)
        assert repo.get_by_id("qr1") is r

    def test_get_by_id_missing_returns_none(self):
        assert InMemoryQueueRequestRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request())
        with pytest.raises(ValueError, match="qr1"):
            repo.add(make_request())

    def test_list_all_empty(self):
        assert InMemoryQueueRequestRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1"))
        repo.add(make_request("qr2", "s2"))
        assert len(repo.list_all()) == 2


class TestInMemoryQueueRequestRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryQueueRequestRepository()
        r = make_request()
        repo.add(r)
        r.status = QueueRequestStatus.FULFILLED
        repo.update(r)
        assert repo.get_by_id("qr1").status == QueueRequestStatus.FULFILLED

    def test_update_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryQueueRequestRepository().update(make_request())


class TestInMemoryQueueRequestRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request())
        repo.delete("qr1")
        assert repo.get_by_id("qr1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryQueueRequestRepository().delete("qr999")


class TestInMemoryQueueRequestRepositoryFind:
    def test_find_by_student(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", "s1", "t1"))
        repo.add(make_request("qr2", "s1", "t2"))
        repo.add(make_request("qr3", "s2", "t1"))
        result = repo.find_by_student("s1")
        assert len(result) == 2

    def test_find_by_team(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", "s1", "t1"))
        repo.add(make_request("qr2", "s2", "t1"))
        repo.add(make_request("qr3", "s3", "t2"))
        result = repo.find_by_team("t1")
        assert len(result) == 2

    def test_find_pending_returns_only_pending(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", status=QueueRequestStatus.PENDING))
        repo.add(make_request("qr2", "s2", status=QueueRequestStatus.FULFILLED))
        repo.add(make_request("qr3", "s3", status=QueueRequestStatus.EXPIRED))
        result = repo.find_pending()
        assert len(result) == 1 and result[0].id == "qr1"

    def test_find_pending_by_team(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", "s1", "t1", QueueRequestStatus.PENDING))
        repo.add(make_request("qr2", "s2", "t1", QueueRequestStatus.FULFILLED))
        repo.add(make_request("qr3", "s3", "t2", QueueRequestStatus.PENDING))
        result = repo.find_pending_by_team("t1")
        assert len(result) == 1 and result[0].id == "qr1"

    def test_find_pending_by_team_no_match(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", "s1", "t1"))
        assert repo.find_pending_by_team("t99") == []

    def test_find_pending_empty(self):
        repo = InMemoryQueueRequestRepository()
        repo.add(make_request("qr1", status=QueueRequestStatus.CANCELLED))
        assert repo.find_pending() == []
