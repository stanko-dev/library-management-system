import pytest
from datetime import datetime
from models.submission import Submission
from storage.memory.submission_repo import InMemorySubmissionRepository


def make_submission(sid: str = "sub1", milestone_id: str = "m1",
                    team_id: str = "t1") -> Submission:
    return Submission(id=sid, milestone_id=milestone_id, team_id=team_id,
                      submitted_at=datetime(2025, 10, 14))


class TestInMemorySubmissionRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemorySubmissionRepository()
        s = make_submission()
        repo.add(s)
        assert repo.get_by_id("sub1") is s

    def test_get_by_id_missing_returns_none(self):
        assert InMemorySubmissionRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission())
        with pytest.raises(ValueError, match="sub1"):
            repo.add(make_submission())

    def test_list_all_empty(self):
        assert InMemorySubmissionRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission("sub1"))
        repo.add(make_submission("sub2", "m2"))
        assert len(repo.list_all()) == 2


class TestInMemorySubmissionRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemorySubmissionRepository()
        s = make_submission()
        repo.add(s)
        new_time = datetime(2025, 10, 20)
        s.submitted_at = new_time
        repo.update(s)
        assert repo.get_by_id("sub1").submitted_at == new_time

    def test_update_missing_raises(self):
        with pytest.raises(KeyError):
            InMemorySubmissionRepository().update(make_submission())


class TestInMemorySubmissionRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission())
        repo.delete("sub1")
        assert repo.get_by_id("sub1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemorySubmissionRepository().delete("sub999")


class TestInMemorySubmissionRepositoryFind:
    def test_find_by_milestone(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission("sub1", "m1", "t1"))
        repo.add(make_submission("sub2", "m1", "t2"))
        repo.add(make_submission("sub3", "m2", "t1"))
        result = repo.find_by_milestone("m1")
        assert len(result) == 2
        assert all(s.milestone_id == "m1" for s in result)

    def test_find_by_milestone_no_match(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission("sub1", "m1"))
        assert repo.find_by_milestone("m99") == []

    def test_find_by_team(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission("sub1", "m1", "t1"))
        repo.add(make_submission("sub2", "m2", "t1"))
        repo.add(make_submission("sub3", "m3", "t2"))
        result = repo.find_by_team("t1")
        assert len(result) == 2
        assert all(s.team_id == "t1" for s in result)

    def test_find_by_team_no_match(self):
        repo = InMemorySubmissionRepository()
        repo.add(make_submission("sub1", team_id="t1"))
        assert repo.find_by_team("t99") == []
