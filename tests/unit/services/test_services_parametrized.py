"""Parametrized cross-cutting tests for all services and the priority helper."""
import pytest
from datetime import datetime, timedelta, date

from models.student import Student
from models.team import Team
from models.project import Project
from models.milestone import Milestone
from models.queue_request import QueueRequest
from models.penalty import Penalty
from models.enums import StudentRole, ProjectStatus, QueueRequestStatus

from services.penalty_strategies import (
    FlatPenaltyStrategy, ProgressivePenaltyStrategy,
    WeekendExemptPenaltyStrategy, CappedPenaltyStrategy,
)
from services.priority import queue_priority_key
from services.events import EventBus, MilestoneStatusChangedEvent, TeamSpotAvailableEvent
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository

_NOW = datetime(2025, 9, 1)
_MON = date(2025, 1, 6)
_FRI = date(2025, 1, 10)
_SAT = date(2025, 1, 11)


# ── Strategy parametrize ──────────────────────────────────────────────────────

@pytest.mark.parametrize("days_late,expected", [
    (0, 0), (1, 3), (2, 6), (5, 15),
])
def test_flat_strategy_various_days(days_late, expected):
    s = FlatPenaltyStrategy(3)
    due = _MON
    ret = due + timedelta(days=days_late)
    assert s.calculate(due, ret) == expected


@pytest.mark.parametrize("days_late,expected", [
    (0, 0), (1, 2), (2, 6), (3, 12), (4, 20), (5, 20),
])
def test_progressive_strategy_various_days(days_late, expected):
    # base=2, increment=2, cap=20 → day costs: 2, 4, 6, 8, ...
    s = ProgressivePenaltyStrategy(2, 2, 20)
    due = _MON
    ret = due + timedelta(days=days_late)
    assert s.calculate(due, ret) == expected


@pytest.mark.parametrize("due_str,ret_str,expected", [
    ("2025-01-06", "2025-01-06", 0),  # on time
    ("2025-01-06", "2025-01-07", 1),  # Tue
    ("2025-01-06", "2025-01-10", 4),  # Tue-Fri
    ("2025-01-06", "2025-01-11", 4),  # Sat skipped
    ("2025-01-06", "2025-01-13", 5),  # Mon2 added
    ("2025-01-10", "2025-01-11", 0),  # Fri→Sat, weekend only
    ("2025-01-10", "2025-01-13", 1),  # Fri→Mon2, one weekday
])
def test_weekend_exempt_parametrized(due_str, ret_str, expected):
    s = WeekendExemptPenaltyStrategy(1)
    due = date.fromisoformat(due_str)
    ret = date.fromisoformat(ret_str)
    assert s.calculate(due, ret) == expected


@pytest.mark.parametrize("inner_days,cap,expected", [
    (2, 10, 4),
    (5, 5, 5),
    (3, 6, 6),
    (1, 100, 2),
])
def test_capped_strategy_parametrized(inner_days, cap, expected):
    inner = FlatPenaltyStrategy(2)
    capped = CappedPenaltyStrategy(inner, cap)
    due = _MON
    ret = due + timedelta(days=inner_days)
    assert capped.calculate(due, ret) == expected


# ── Priority key parametrize ─────────────────────────────────────────────────

@pytest.mark.parametrize("active1,active2,expected_first", [
    (0, 3, "s1"),
    (3, 0, "s2"),
    (2, 2, "s1"),  # same count → FIFO by created_at
])
def test_queue_priority_ordering(active1, active2, expected_first):
    s_repo = InMemoryStudentRepository()
    s_repo.add(Student("s1", "A", StudentRole.MEMBER, active_projects_count=active1))
    s_repo.add(Student("s2", "B", StudentRole.MEMBER, active_projects_count=active2))

    t = _NOW
    r1 = QueueRequest("qr1", "s1", "t1", t, t + timedelta(days=7))
    r2 = QueueRequest("qr2", "s2", "t1", t + timedelta(seconds=1), t + timedelta(days=7))

    first = min([r1, r2], key=lambda r: queue_priority_key(r, s_repo))
    assert first.student_id == expected_first


def test_queue_priority_unknown_student_defaults_to_large_rank():
    s_repo = InMemoryStudentRepository()
    s_repo.add(Student("s1", "A", StudentRole.MEMBER, active_projects_count=0))

    t = _NOW
    r_known = QueueRequest("qr1", "s1", "t1", t, t + timedelta(days=7))
    r_unknown = QueueRequest("qr2", "ghost", "t1", t - timedelta(seconds=1),
                              t + timedelta(days=7))

    first = min([r_known, r_unknown], key=lambda r: queue_priority_key(r, s_repo))
    assert first.student_id == "s1"


# ── EventBus: both event types ────────────────────────────────────────────────

from unittest.mock import MagicMock
from services.events import DeadlineObserver


@pytest.mark.parametrize("milestone_status", [
    "pending", "submitted", "late", "missed"
])
def test_eventbus_milestone_event_reaches_observer(milestone_status):
    from models.enums import MilestoneStatus
    bus = EventBus()
    obs = MagicMock(spec=DeadlineObserver)
    bus.subscribe(obs)
    status = MilestoneStatus(milestone_status)
    event = MilestoneStatusChangedEvent("m1", status)
    bus.notify_milestone_status(event)
    obs.on_milestone_status_changed.assert_called_once_with(event)


@pytest.mark.parametrize("team_id", ["t1", "team-alpha", "99"])
def test_eventbus_team_spot_event_reaches_observer(team_id):
    bus = EventBus()
    obs = MagicMock(spec=DeadlineObserver)
    bus.subscribe(obs)
    event = TeamSpotAvailableEvent(team_id)
    bus.notify_team_spot(event)
    obs.on_team_spot_available.assert_called_once_with(event)


# ── Membership blocking thresholds ────────────────────────────────────────────

from services.membership_service import MembershipService
from storage.memory.penalty_repo import InMemoryPenaltyRepository


@pytest.mark.parametrize("points,missed,max_pts,max_missed,expected_blocked", [
    (0, 0, 10, 3, False),
    (10, 0, 10, 3, True),
    (9, 0, 10, 3, False),
    (0, 3, 10, 3, True),
    (0, 2, 10, 3, False),
    (5, 3, 10, 3, True),
])
def test_membership_evaluate_parametrized(points, missed, max_pts, max_missed, expected_blocked):
    s_repo = InMemoryStudentRepository()
    pen_repo = InMemoryPenaltyRepository()
    s = Student("s1", "Alice", StudentRole.MEMBER, missed_deadlines_count=missed)
    s_repo.add(s)
    if points > 0:
        pen_repo.add(Penalty("pen1", "s1", "m1", points))
    svc = MembershipService(s_repo, pen_repo, max_pts, max_missed)
    result = svc.evaluate("s1")
    assert result is expected_blocked


# ── ProjectService status transitions ────────────────────────────────────────

from services.project_service import ProjectService
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.team_repo import InMemoryTeamRepository
from utils.exceptions import InvalidStatusTransitionError


@pytest.mark.parametrize("from_status,to_status,has_team,should_raise", [
    (ProjectStatus.DRAFT, ProjectStatus.ACTIVE, True, False),
    (ProjectStatus.DRAFT, ProjectStatus.ACTIVE, False, True),
    (ProjectStatus.DRAFT, ProjectStatus.ARCHIVED, False, False),
    (ProjectStatus.DRAFT, ProjectStatus.COMPLETED, False, True),
    (ProjectStatus.ACTIVE, ProjectStatus.COMPLETED, True, False),
    (ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED, True, False),
    (ProjectStatus.ACTIVE, ProjectStatus.DRAFT, True, True),
    (ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED, True, False),
    (ProjectStatus.COMPLETED, ProjectStatus.ACTIVE, True, True),
    (ProjectStatus.ARCHIVED, ProjectStatus.DRAFT, False, True),
])
def test_project_status_transitions(from_status, to_status, has_team, should_raise):
    p_repo = InMemoryProjectRepository()
    t_repo = InMemoryTeamRepository()
    team_id = None
    if has_team:
        t_repo.add(Team("t1", "Alpha", 3))
        team_id = "t1"
    p = Project("p1", "Title", "desc", status=from_status,
                team_id=team_id, created_at=_NOW)
    p_repo.add(p)
    svc = ProjectService(p_repo, t_repo)
    if should_raise:
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_status("p1", to_status)
    else:
        result = svc.change_status("p1", to_status)
        assert result.status == to_status
