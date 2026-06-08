import pytest
from models.team import Team
from storage.memory.team_repo import InMemoryTeamRepository


def make_team(tid: str = "t1", name: str = "Alpha", capacity: int = 4) -> Team:
    return Team(id=tid, name=name, capacity=capacity)


class TestInMemoryTeamRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryTeamRepository()
        t = make_team()
        repo.add(t)
        assert repo.get_by_id("t1") is t

    def test_get_by_id_missing_returns_none(self):
        assert InMemoryTeamRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team())
        with pytest.raises(ValueError, match="t1"):
            repo.add(make_team())

    def test_list_all_empty(self):
        assert InMemoryTeamRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team("t1", "Alpha"))
        repo.add(make_team("t2", "Beta"))
        ids = {t.id for t in repo.list_all()}
        assert ids == {"t1", "t2"}


class TestInMemoryTeamRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryTeamRepository()
        t = make_team()
        repo.add(t)
        t.member_ids.append("s1")
        repo.update(t)
        assert "s1" in repo.get_by_id("t1").member_ids

    def test_update_missing_raises(self):
        repo = InMemoryTeamRepository()
        with pytest.raises(KeyError):
            repo.update(make_team())


class TestInMemoryTeamRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team())
        repo.delete("t1")
        assert repo.get_by_id("t1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryTeamRepository().delete("t999")


class TestInMemoryTeamRepositoryFind:
    def test_find_by_name_exact(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team("t1", "Alpha Squad"))
        repo.add(make_team("t2", "Beta Group"))
        result = repo.find_by_name("Alpha")
        assert len(result) == 1

    def test_find_by_name_case_insensitive(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team("t1", "Alpha"))
        result = repo.find_by_name("alpha")
        assert len(result) == 1

    def test_find_by_name_no_match(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team("t1", "Alpha"))
        assert repo.find_by_name("Gamma") == []

    def test_find_by_name_multiple_matches(self):
        repo = InMemoryTeamRepository()
        repo.add(make_team("t1", "Alpha A"))
        repo.add(make_team("t2", "Alpha B"))
        repo.add(make_team("t3", "Beta"))
        assert len(repo.find_by_name("alpha")) == 2
