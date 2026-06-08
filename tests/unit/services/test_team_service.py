"""TDD tests for TeamService."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from models.student import Student
from models.team import Team
from models.queue_request import QueueRequest
from models.enums import StudentRole, QueueRequestStatus
from services.team_service import TeamService
from services.events import EventBus
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository
from utils.exceptions import (
    StudentNotFoundError, TeamNotFoundError, StudentBlockedError,
    DuplicateQueueRequestError, StudentNotInTeamError,
)

_NOW = datetime(2025, 9, 1, 10, 0)


def _make_student(sid="s1", blocked=False, active=0):
    return Student(sid, f"S{sid}", StudentRole.MEMBER,
                   is_blocked=blocked, active_projects_count=active)


def _make_team(tid="t1", capacity=3, members=None):
    return Team(tid, f"T{tid}", capacity, member_ids=list(members or []))


def _svc(s_repo=None, t_repo=None, q_repo=None, bus=None, expiry_days=7, clock=None):
    return TeamService(
        t_repo or InMemoryTeamRepository(),
        s_repo or InMemoryStudentRepository(),
        q_repo or InMemoryQueueRequestRepository(),
        bus or EventBus(),
        expiry_days=expiry_days,
        clock=clock or (lambda: _NOW),
    )


class TestTeamServiceCreateTeam:
    def test_create_team_stores_in_repo(self):
        t_repo = InMemoryTeamRepository()
        svc = _svc(t_repo=t_repo)
        t = svc.create_team("t1", "Alpha", 4)
        assert t_repo.get_by_id("t1") is t

    def test_create_team_correct_capacity(self):
        svc = _svc()
        t = svc.create_team("t1", "Alpha", 4)
        assert t.capacity == 4

    def test_create_duplicate_team_raises(self):
        t_repo = InMemoryTeamRepository()
        svc = _svc(t_repo=t_repo)
        svc.create_team("t1", "Alpha", 4)
        with pytest.raises(ValueError):
            svc.create_team("t1", "Beta", 3)


class TestTeamServiceJoinOrQueue:
    def test_join_team_with_space(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", 3))
        svc = _svc(s_repo, t_repo)
        result = svc.join_or_queue("s1", "t1")
        assert isinstance(result, Team)
        assert "s1" in t_repo.get_by_id("t1").member_ids

    def test_queue_when_team_full(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        s_repo.add(_make_student("s3"))
        s_repo.add(_make_student("s4"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2", "s3"]))
        svc = _svc(s_repo, t_repo, q_repo)
        result = svc.join_or_queue("s4", "t1")
        assert isinstance(result, QueueRequest)
        assert q_repo.find_pending_by_team("t1") != []

    def test_join_unknown_student_raises(self):
        t_repo = InMemoryTeamRepository()
        t_repo.add(_make_team())
        svc = _svc(t_repo=t_repo)
        with pytest.raises(StudentNotFoundError):
            svc.join_or_queue("unknown", "t1")

    def test_join_unknown_team_raises(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student())
        svc = _svc(s_repo=s_repo)
        with pytest.raises(TeamNotFoundError):
            svc.join_or_queue("s1", "unknown")

    def test_join_blocked_student_raises(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1", blocked=True))
        t_repo.add(_make_team("t1", 3))
        svc = _svc(s_repo, t_repo)
        with pytest.raises(StudentBlockedError):
            svc.join_or_queue("s1", "t1")

    def test_duplicate_queue_request_raises(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        s_repo.add(_make_student("s3"))
        s_repo.add(_make_student("s4"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2", "s3"]))
        svc = _svc(s_repo, t_repo, q_repo)
        svc.join_or_queue("s4", "t1")
        with pytest.raises(DuplicateQueueRequestError):
            svc.join_or_queue("s4", "t1")

    def test_join_increments_active_projects_count(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", 3))
        svc = _svc(s_repo, t_repo)
        svc.join_or_queue("s1", "t1")
        assert s_repo.get_by_id("s1").active_projects_count == 1


class TestTeamServiceLeaveTeam:
    def test_leave_removes_from_team(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2"]))
        svc = _svc(s_repo, t_repo)
        svc.leave_team("s1", "t1")
        assert "s1" not in t_repo.get_by_id("t1").member_ids

    def test_leave_fires_team_spot_event(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", 3, ["s1"]))
        bus = MagicMock(spec=EventBus)
        svc = _svc(s_repo, t_repo, bus=bus)
        svc.leave_team("s1", "t1")
        bus.notify_team_spot.assert_called_once()

    def test_leave_unknown_student_raises(self):
        t_repo = InMemoryTeamRepository()
        t_repo.add(_make_team("t1", 3, []))
        svc = _svc(t_repo=t_repo)
        with pytest.raises(StudentNotFoundError):
            svc.leave_team("unknown", "t1")

    def test_leave_unknown_team_raises(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student())
        svc = _svc(s_repo=s_repo)
        with pytest.raises(TeamNotFoundError):
            svc.leave_team("s1", "unknown")

    def test_leave_student_not_in_team_raises(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", 3, ["s2"]))
        svc = _svc(s_repo, t_repo)
        with pytest.raises(StudentNotInTeamError):
            svc.leave_team("s1", "t1")

    def test_leave_decrements_active_projects_count(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s = _make_student("s1")
        s.active_projects_count = 1
        s_repo.add(s)
        t_repo.add(_make_team("t1", 3, ["s1"]))
        svc = _svc(s_repo, t_repo)
        svc.leave_team("s1", "t1")
        assert s_repo.get_by_id("s1").active_projects_count == 0

    def test_leave_active_count_does_not_go_below_zero(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        s = _make_student("s1")
        s.active_projects_count = 0
        s_repo.add(s)
        t_repo.add(_make_team("t1", 3, ["s1"]))
        svc = _svc(s_repo, t_repo)
        svc.leave_team("s1", "t1")
        assert s_repo.get_by_id("s1").active_projects_count == 0


class TestTeamServiceExpireOld:
    def test_expire_old_requests(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        s_repo.add(_make_student("s3"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2", "s3"]))  # full team
        svc = _svc(s_repo, t_repo, q_repo, expiry_days=3,
                   clock=lambda: _NOW)
        s_repo.add(_make_student("s4"))
        svc.join_or_queue("s4", "t1")

        future = _NOW + timedelta(days=10)
        expired = svc.expire_old(as_of=future)
        assert len(expired) == 1
        assert expired[0].status == QueueRequestStatus.EXPIRED


    def test_expire_old_does_not_expire_valid_requests(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        s_repo.add(_make_student("s3"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2", "s3"]))
        svc = _svc(s_repo, t_repo, q_repo, expiry_days=7, clock=lambda: _NOW)
        s_repo.add(_make_student("s4"))
        svc.join_or_queue("s4", "t1")

        not_yet = _NOW + timedelta(days=3)
        expired = svc.expire_old(as_of=not_yet)
        assert expired == []

    def test_expire_old_uses_clock_when_as_of_none(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        s_repo.add(_make_student("s3"))
        t_repo.add(_make_team("t1", 3, ["s1", "s2", "s3"]))
        far_future = _NOW + timedelta(days=100)
        svc = _svc(s_repo, t_repo, q_repo, expiry_days=1,
                   clock=lambda: far_future)
        s_repo.add(_make_student("s4"))
        svc2 = TeamService(
            t_repo, s_repo, q_repo, EventBus(),
            expiry_days=1, clock=lambda: _NOW,
        )
        svc2.join_or_queue("s4", "t1")

        expired = svc.expire_old()
        assert len(expired) == 1


class TestTeamServiceGetNextInQueue:
    def test_returns_highest_priority(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1", active=5))
        s_repo.add(_make_student("s2", active=0))
        t_repo.add(_make_team("t1", 3, ["x1", "x2", "x3"]))
        svc = _svc(s_repo, t_repo, q_repo)
        svc.join_or_queue("s1", "t1")

        t_repo2 = InMemoryTeamRepository()
        t_repo2.add(_make_team("t1", 3, ["x1", "x2", "x3"]))
        svc2 = TeamService(t_repo2, s_repo, q_repo, EventBus(),
                           expiry_days=7, clock=lambda: _NOW + timedelta(seconds=1))
        svc2.join_or_queue("s2", "t1")

        result = svc.get_next_in_queue("t1")
        assert result is not None
        assert result.student_id == "s2"

    def test_returns_none_when_queue_empty(self):
        svc = _svc()
        assert svc.get_next_in_queue("t1") is None
