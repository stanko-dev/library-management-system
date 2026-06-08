"""Parametrized contract tests: every InMemory* repo satisfies its ABC."""
import pytest
from datetime import datetime, timedelta

from storage.interfaces import (
    StudentRepository, TeamRepository, ProjectRepository,
    MilestoneRepository, SubmissionRepository,
    PenaltyRepository, QueueRequestRepository,
)
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.milestone_repo import InMemoryMilestoneRepository
from storage.memory.submission_repo import InMemorySubmissionRepository
from storage.memory.penalty_repo import InMemoryPenaltyRepository
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository

from models.student import Student
from models.team import Team
from models.project import Project
from models.milestone import Milestone
from models.submission import Submission
from models.penalty import Penalty
from models.queue_request import QueueRequest
from models.enums import StudentRole, ProjectStatus, MilestoneStatus, QueueRequestStatus

_NOW = datetime(2025, 9, 1)


# ── Substitutability: InMemory* is subclass of ABC ────────────────────────────

class TestRepositorySubstitutability:
    def test_student_repo_is_abc(self):
        assert isinstance(InMemoryStudentRepository(), StudentRepository)

    def test_team_repo_is_abc(self):
        assert isinstance(InMemoryTeamRepository(), TeamRepository)

    def test_project_repo_is_abc(self):
        assert isinstance(InMemoryProjectRepository(), ProjectRepository)

    def test_milestone_repo_is_abc(self):
        assert isinstance(InMemoryMilestoneRepository(), MilestoneRepository)

    def test_submission_repo_is_abc(self):
        assert isinstance(InMemorySubmissionRepository(), SubmissionRepository)

    def test_penalty_repo_is_abc(self):
        assert isinstance(InMemoryPenaltyRepository(), PenaltyRepository)

    def test_queue_request_repo_is_abc(self):
        assert isinstance(InMemoryQueueRequestRepository(), QueueRequestRepository)


# ── ABC cannot be instantiated ───────────────────────────────────────────────

class TestAbcNotInstantiable:
    def test_student_repository_abstract(self):
        with pytest.raises(TypeError):
            StudentRepository()  # type: ignore[abstract]

    def test_team_repository_abstract(self):
        with pytest.raises(TypeError):
            TeamRepository()  # type: ignore[abstract]

    def test_project_repository_abstract(self):
        with pytest.raises(TypeError):
            ProjectRepository()  # type: ignore[abstract]

    def test_milestone_repository_abstract(self):
        with pytest.raises(TypeError):
            MilestoneRepository()  # type: ignore[abstract]

    def test_submission_repository_abstract(self):
        with pytest.raises(TypeError):
            SubmissionRepository()  # type: ignore[abstract]

    def test_penalty_repository_abstract(self):
        with pytest.raises(TypeError):
            PenaltyRepository()  # type: ignore[abstract]

    def test_queue_request_repository_abstract(self):
        with pytest.raises(TypeError):
            QueueRequestRepository()  # type: ignore[abstract]


# ── Each repo: add → get_by_id → list_all → update → delete ─────────────────

class TestStudentRepoContract:
    def _repo(self): return InMemoryStudentRepository()
    def _entity(self, eid="e1"): return Student(eid, "Alice", StudentRole.LEADER)

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e)
        assert repo.get_by_id("e1") is e
        assert e in repo.list_all()

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.is_blocked = True; repo.update(e)
        assert repo.get_by_id("e1").is_blocked is True

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1")
        assert repo.get_by_id("e1") is None
        assert repo.list_all() == []

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestTeamRepoContract:
    def _repo(self): return InMemoryTeamRepository()
    def _entity(self, eid="e1"): return Team(eid, "Alpha", 3)

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.member_ids.append("s1"); repo.update(e)
        assert "s1" in repo.get_by_id("e1").member_ids

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestProjectRepoContract:
    def _repo(self): return InMemoryProjectRepository()
    def _entity(self, eid="e1"):
        return Project(eid, "Title", "desc", created_at=_NOW)

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.status = ProjectStatus.ACTIVE; repo.update(e)
        assert repo.get_by_id("e1").status == ProjectStatus.ACTIVE

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestMilestoneRepoContract:
    def _repo(self): return InMemoryMilestoneRepository()
    def _entity(self, eid="e1"):
        return Milestone(eid, "p1", "Sprint", datetime(2025, 10, 15))

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.status = MilestoneStatus.SUBMITTED; repo.update(e)
        assert repo.get_by_id("e1").status == MilestoneStatus.SUBMITTED

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestSubmissionRepoContract:
    def _repo(self): return InMemorySubmissionRepository()
    def _entity(self, eid="e1"):
        return Submission(eid, "m1", "t1", _NOW)

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        new_time = _NOW + timedelta(days=1); e.submitted_at = new_time
        repo.update(e)
        assert repo.get_by_id("e1").submitted_at == new_time

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestPenaltyRepoContract:
    def _repo(self): return InMemoryPenaltyRepository()
    def _entity(self, eid="e1"):
        return Penalty(eid, "s1", "m1", 5)

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.is_resolved = True; repo.update(e)
        assert repo.get_by_id("e1").is_resolved is True

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")


class TestQueueRequestRepoContract:
    def _repo(self): return InMemoryQueueRequestRepository()
    def _entity(self, eid="e1"):
        return QueueRequest(eid, "s1", "t1", _NOW, _NOW + timedelta(days=7))

    def test_add_list_get(self):
        repo = self._repo(); e = self._entity()
        repo.add(e); assert repo.get_by_id("e1") is e

    def test_update_reflects_change(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        e.status = QueueRequestStatus.FULFILLED; repo.update(e)
        assert repo.get_by_id("e1").status == QueueRequestStatus.FULFILLED

    def test_delete_removes_entity(self):
        repo = self._repo(); e = self._entity(); repo.add(e)
        repo.delete("e1"); assert repo.get_by_id("e1") is None

    def test_add_duplicate_raises(self):
        repo = self._repo(); repo.add(self._entity())
        with pytest.raises(ValueError): repo.add(self._entity())

    def test_update_missing_raises(self):
        with pytest.raises(KeyError): self._repo().update(self._entity())

    def test_delete_missing_raises(self):
        with pytest.raises(KeyError): self._repo().delete("e1")
