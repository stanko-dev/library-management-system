import pytest
from datetime import datetime
from models.milestone import Milestone
from models.enums import MilestoneStatus
from storage.memory.milestone_repo import InMemoryMilestoneRepository


def make_milestone(mid: str = "m1", project_id: str = "p1",
                   due_date: datetime = datetime(2025, 10, 15),
                   status: MilestoneStatus = MilestoneStatus.PENDING) -> Milestone:
    return Milestone(id=mid, project_id=project_id, title=f"MS {mid}",
                     due_date=due_date, status=status)


class TestInMemoryMilestoneRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryMilestoneRepository()
        m = make_milestone()
        repo.add(m)
        assert repo.get_by_id("m1") is m

    def test_get_by_id_missing_returns_none(self):
        assert InMemoryMilestoneRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone())
        with pytest.raises(ValueError, match="m1"):
            repo.add(make_milestone())

    def test_list_all_empty(self):
        assert InMemoryMilestoneRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone("m1"))
        repo.add(make_milestone("m2"))
        assert len(repo.list_all()) == 2


class TestInMemoryMilestoneRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryMilestoneRepository()
        m = make_milestone()
        repo.add(m)
        m.status = MilestoneStatus.SUBMITTED
        repo.update(m)
        assert repo.get_by_id("m1").status == MilestoneStatus.SUBMITTED

    def test_update_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryMilestoneRepository().update(make_milestone())


class TestInMemoryMilestoneRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone())
        repo.delete("m1")
        assert repo.get_by_id("m1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryMilestoneRepository().delete("m999")


class TestInMemoryMilestoneRepositoryFind:
    def test_find_by_project(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone("m1", "p1"))
        repo.add(make_milestone("m2", "p1"))
        repo.add(make_milestone("m3", "p2"))
        result = repo.find_by_project("p1")
        assert len(result) == 2
        assert all(m.project_id == "p1" for m in result)

    def test_find_by_project_no_match(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone("m1", "p1"))
        assert repo.find_by_project("p99") == []

    def test_find_pending_returns_only_pending(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone("m1", status=MilestoneStatus.PENDING))
        repo.add(make_milestone("m2", status=MilestoneStatus.SUBMITTED))
        repo.add(make_milestone("m3", status=MilestoneStatus.LATE))
        result = repo.find_pending()
        assert len(result) == 1 and result[0].id == "m1"

    def test_find_pending_empty(self):
        repo = InMemoryMilestoneRepository()
        repo.add(make_milestone("m1", status=MilestoneStatus.SUBMITTED))
        assert repo.find_pending() == []

    def test_find_overdue_returns_pending_past_due(self):
        repo = InMemoryMilestoneRepository()
        past = datetime(2025, 9, 1)
        future = datetime(2025, 12, 31)
        repo.add(make_milestone("m1", due_date=past, status=MilestoneStatus.PENDING))
        repo.add(make_milestone("m2", due_date=future, status=MilestoneStatus.PENDING))
        as_of = datetime(2025, 10, 1)
        result = repo.find_overdue(as_of)
        assert len(result) == 1 and result[0].id == "m1"

    def test_find_overdue_excludes_already_submitted(self):
        repo = InMemoryMilestoneRepository()
        past = datetime(2025, 9, 1)
        repo.add(make_milestone("m1", due_date=past, status=MilestoneStatus.SUBMITTED))
        result = repo.find_overdue(datetime(2025, 10, 1))
        assert result == []

    def test_find_overdue_excludes_late(self):
        repo = InMemoryMilestoneRepository()
        past = datetime(2025, 9, 1)
        repo.add(make_milestone("m1", due_date=past, status=MilestoneStatus.LATE))
        result = repo.find_overdue(datetime(2025, 10, 1))
        assert result == []
