"""TDD tests for ProjectService."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.project import Project
from models.team import Team
from models.enums import ProjectStatus
from services.project_service import ProjectService
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.team_repo import InMemoryTeamRepository
from utils.exceptions import (
    ProjectNotFoundError, TeamNotFoundError, InvalidStatusTransitionError,
)

_NOW = datetime(2025, 9, 1)


def _make_team(tid="t1"):
    return Team(tid, f"Team {tid}", 4)


def _svc(project_repo=None, team_repo=None):
    return ProjectService(
        project_repo or InMemoryProjectRepository(),
        team_repo or InMemoryTeamRepository(),
    )


class TestProjectServiceCreate:
    def test_create_returns_draft_project(self):
        svc = _svc()
        p = svc.create_project("AI Research", "desc")
        assert p.status == ProjectStatus.DRAFT
        assert p.title == "AI Research"

    def test_create_assigns_unique_id(self):
        svc = _svc()
        p1 = svc.create_project("A", "")
        p2 = svc.create_project("B", "")
        assert p1.id != p2.id

    def test_create_stored_in_repo(self):
        repo = InMemoryProjectRepository()
        svc = _svc(repo)
        p = svc.create_project("Title", "desc")
        assert repo.get_by_id(p.id) is p

    def test_create_with_team_id_succeeds(self):
        t_repo = InMemoryTeamRepository()
        t_repo.add(_make_team("t1"))
        svc = _svc(team_repo=t_repo)
        p = svc.create_project("Title", "desc", team_id="t1")
        assert p.team_id == "t1"

    def test_create_with_unknown_team_raises(self):
        svc = _svc()
        with pytest.raises(TeamNotFoundError):
            svc.create_project("Title", "desc", team_id="unknown")

    def test_create_without_team_team_id_is_none(self):
        svc = _svc()
        p = svc.create_project("Title", "desc")
        assert p.team_id is None


class TestProjectServiceAssignTeam:
    def test_assign_team_updates_project(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        p = svc.create_project("Title", "desc")
        t_repo.add(_make_team("t1"))
        result = svc.assign_team(p.id, "t1")
        assert result.team_id == "t1"
        assert p_repo.get_by_id(p.id).team_id == "t1"

    def test_assign_team_unknown_project_raises(self):
        t_repo = InMemoryTeamRepository()
        t_repo.add(_make_team("t1"))
        svc = _svc(team_repo=t_repo)
        with pytest.raises(ProjectNotFoundError):
            svc.assign_team("unknown", "t1")

    def test_assign_team_unknown_team_raises(self):
        p_repo = InMemoryProjectRepository()
        svc = _svc(p_repo)
        p = svc.create_project("Title", "desc")
        with pytest.raises(TeamNotFoundError):
            svc.assign_team(p.id, "unknown")

    def test_assign_team_to_archived_raises(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        p = svc.create_project("Title", "desc")
        p.status = ProjectStatus.ARCHIVED
        p_repo.update(p)
        t_repo.add(_make_team("t1"))
        with pytest.raises(InvalidStatusTransitionError):
            svc.assign_team(p.id, "t1")


class TestProjectServiceChangeStatus:
    def test_draft_to_active_with_team(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        result = svc.change_status(p.id, ProjectStatus.ACTIVE)
        assert result.status == ProjectStatus.ACTIVE

    def test_draft_to_active_without_team_raises(self):
        svc = _svc()
        p = svc.create_project("Title", "desc")
        with pytest.raises(InvalidStatusTransitionError, match="team"):
            svc.change_status(p.id, ProjectStatus.ACTIVE)

    def test_draft_to_archived(self):
        svc = _svc()
        p = svc.create_project("Title", "desc")
        result = svc.change_status(p.id, ProjectStatus.ARCHIVED)
        assert result.status == ProjectStatus.ARCHIVED

    def test_active_to_completed(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        svc.change_status(p.id, ProjectStatus.ACTIVE)
        result = svc.change_status(p.id, ProjectStatus.COMPLETED)
        assert result.status == ProjectStatus.COMPLETED

    def test_active_to_archived(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        svc.change_status(p.id, ProjectStatus.ACTIVE)
        result = svc.change_status(p.id, ProjectStatus.ARCHIVED)
        assert result.status == ProjectStatus.ARCHIVED

    def test_completed_to_archived(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        svc.change_status(p.id, ProjectStatus.ACTIVE)
        svc.change_status(p.id, ProjectStatus.COMPLETED)
        result = svc.change_status(p.id, ProjectStatus.ARCHIVED)
        assert result.status == ProjectStatus.ARCHIVED

    def test_archived_to_anything_raises(self):
        svc = _svc()
        p = svc.create_project("Title", "desc")
        svc.change_status(p.id, ProjectStatus.ARCHIVED)
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status(p.id, ProjectStatus.DRAFT)

    def test_completed_to_active_raises(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        svc.change_status(p.id, ProjectStatus.ACTIVE)
        svc.change_status(p.id, ProjectStatus.COMPLETED)
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status(p.id, ProjectStatus.ACTIVE)

    def test_change_status_unknown_project_raises(self):
        svc = _svc()
        with pytest.raises(ProjectNotFoundError):
            svc.change_status("unknown", ProjectStatus.ACTIVE)

    def test_draft_to_completed_raises(self):
        svc = _svc()
        p = svc.create_project("Title", "desc")
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status(p.id, ProjectStatus.COMPLETED)

    def test_active_to_draft_raises(self):
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        svc = _svc(p_repo, t_repo)
        t_repo.add(_make_team("t1"))
        p = svc.create_project("Title", "desc", team_id="t1")
        svc.change_status(p.id, ProjectStatus.ACTIVE)
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status(p.id, ProjectStatus.DRAFT)
