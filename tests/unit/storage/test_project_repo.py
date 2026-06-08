import pytest
from datetime import datetime
from models.project import Project
from models.enums import ProjectStatus
from storage.memory.project_repo import InMemoryProjectRepository


def make_project(pid: str = "p1", title: str = "AI Research",
                 status: ProjectStatus = ProjectStatus.DRAFT,
                 team_id: str | None = None) -> Project:
    return Project(id=pid, title=title, description="desc",
                   status=status, team_id=team_id,
                   created_at=datetime(2025, 9, 1))


class TestInMemoryProjectRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryProjectRepository()
        p = make_project()
        repo.add(p)
        assert repo.get_by_id("p1") is p

    def test_get_by_id_missing_returns_none(self):
        assert InMemoryProjectRepository().get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project())
        with pytest.raises(ValueError, match="p1"):
            repo.add(make_project())

    def test_list_all_empty(self):
        assert InMemoryProjectRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1"))
        repo.add(make_project("p2", "Web App"))
        assert len(repo.list_all()) == 2


class TestInMemoryProjectRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryProjectRepository()
        p = make_project()
        repo.add(p)
        p.status = ProjectStatus.ACTIVE
        repo.update(p)
        assert repo.get_by_id("p1").status == ProjectStatus.ACTIVE

    def test_update_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryProjectRepository().update(make_project())


class TestInMemoryProjectRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project())
        repo.delete("p1")
        assert repo.get_by_id("p1") is None

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError):
            InMemoryProjectRepository().delete("p999")


class TestInMemoryProjectRepositoryFind:
    def test_find_by_team(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", team_id="t1"))
        repo.add(make_project("p2", team_id="t2"))
        repo.add(make_project("p3", team_id="t1"))
        result = repo.find_by_team("t1")
        assert len(result) == 2
        assert all(p.team_id == "t1" for p in result)

    def test_find_by_team_no_match(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", team_id="t1"))
        assert repo.find_by_team("t99") == []

    def test_find_by_team_none_team_id_excluded(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", team_id=None))
        assert repo.find_by_team("t1") == []

    def test_find_by_status_draft(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", status=ProjectStatus.DRAFT))
        repo.add(make_project("p2", status=ProjectStatus.ACTIVE))
        result = repo.find_by_status(ProjectStatus.DRAFT)
        assert len(result) == 1 and result[0].id == "p1"

    def test_find_by_status_active(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", status=ProjectStatus.ACTIVE))
        repo.add(make_project("p2", status=ProjectStatus.ARCHIVED))
        result = repo.find_by_status(ProjectStatus.ACTIVE)
        assert len(result) == 1

    def test_find_by_status_empty(self):
        repo = InMemoryProjectRepository()
        repo.add(make_project("p1", status=ProjectStatus.DRAFT))
        assert repo.find_by_status(ProjectStatus.COMPLETED) == []
