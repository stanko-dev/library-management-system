import pytest
from models.penalty import Penalty
from storage.memory.penalty_repo import InMemoryPenaltyRepository


def make_penalty(pid: str = "pen1", student_id: str = "s1",
                 milestone_id: str = "m1", points: int = 5,
                 is_resolved: bool = False) -> Penalty:
    return Penalty(id=pid, student_id=student_id, milestone_id=milestone_id,
                   points=points, is_resolved=is_resolved)


class TestInMemoryPenaltyRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryPenaltyRepository()
        p = make_penalty()
        repo.add(p)
        assert repo.get_by_id("pen1") is p

    def test_get_by_id_missing_returns_none(self):
        assert InMemoryPenaltyRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty())
        with pytest.raises(ValueError, match="pen1"):
            repo.add(make_penalty())

    def test_list_all_empty(self):
        assert InMemoryPenaltyRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1"))
        repo.add(make_penalty("pen2", "s2"))
        assert len(repo.list_all()) == 2


class TestInMemoryPenaltyRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryPenaltyRepository()
        p = make_penalty()
        repo.add(p)
        p.is_resolved = True
        repo.update(p)
        assert repo.get_by_id("pen1").is_resolved is True

    def test_update_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryPenaltyRepository().update(make_penalty())


class TestInMemoryPenaltyRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty())
        repo.delete("pen1")
        assert repo.get_by_id("pen1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryPenaltyRepository().delete("pen999")


class TestInMemoryPenaltyRepositoryFind:
    def test_find_by_student(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1"))
        repo.add(make_penalty("pen2", "s1", "m2"))
        repo.add(make_penalty("pen3", "s2"))
        result = repo.find_by_student("s1")
        assert len(result) == 2

    def test_find_by_student_no_match(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1"))
        assert repo.find_by_student("s99") == []

    def test_find_by_milestone(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1", "m1"))
        repo.add(make_penalty("pen2", "s2", "m1"))
        repo.add(make_penalty("pen3", "s3", "m2"))
        result = repo.find_by_milestone("m1")
        assert len(result) == 2

    def test_find_unresolved_returns_only_unresolved(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", is_resolved=False))
        repo.add(make_penalty("pen2", "s2", is_resolved=True))
        result = repo.find_unresolved()
        assert len(result) == 1 and result[0].id == "pen1"

    def test_find_unresolved_by_student(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1", is_resolved=False))
        repo.add(make_penalty("pen2", "s1", "m2", is_resolved=True))
        repo.add(make_penalty("pen3", "s2", is_resolved=False))
        result = repo.find_unresolved_by_student("s1")
        assert len(result) == 1 and result[0].id == "pen1"

    def test_total_unresolved_by_student(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1", points=3, is_resolved=False))
        repo.add(make_penalty("pen2", "s1", "m2", points=5, is_resolved=False))
        repo.add(make_penalty("pen3", "s1", "m3", points=10, is_resolved=True))
        assert repo.total_unresolved_by_student("s1") == 8

    def test_total_unresolved_by_student_zero_when_all_resolved(self):
        repo = InMemoryPenaltyRepository()
        repo.add(make_penalty("pen1", "s1", is_resolved=True))
        assert repo.total_unresolved_by_student("s1") == 0

    def test_total_unresolved_by_student_no_penalties(self):
        assert InMemoryPenaltyRepository().total_unresolved_by_student("s1") == 0
