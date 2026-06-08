"""TDD tests for MilestoneService."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from models.student import Student
from models.team import Team
from models.project import Project
from models.milestone import Milestone
from models.enums import StudentRole, ProjectStatus, MilestoneStatus
from services.milestone_service import MilestoneService
from services.penalty_strategies import FlatPenaltyStrategy
from services.events import EventBus
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.milestone_repo import InMemoryMilestoneRepository
from storage.memory.submission_repo import InMemorySubmissionRepository
from storage.memory.penalty_repo import InMemoryPenaltyRepository
from utils.exceptions import MilestoneNotFoundError, AlreadySubmittedError

_DUE = datetime(2025, 10, 15, 0, 0)


def _make_student(sid="s1"):
    return Student(sid, f"S{sid}", StudentRole.MEMBER)


def _make_team(tid="t1", members=None):
    return Team(tid, f"T{tid}", 4, member_ids=members or ["s1"])


def _make_project(pid="p1", team_id="t1"):
    return Project(pid, "Proj", "desc", ProjectStatus.ACTIVE,
                   team_id=team_id, created_at=datetime(2025, 9, 1))


def _make_milestone(mid="m1", project_id="p1", due=_DUE):
    return Milestone(mid, project_id, "Sprint 1", due)


def _make_all_repos():
    return (
        InMemoryMilestoneRepository(),
        InMemorySubmissionRepository(),
        InMemoryPenaltyRepository(),
        InMemoryProjectRepository(),
        InMemoryTeamRepository(),
        InMemoryStudentRepository(),
    )


def _make_svc(m_repo=None, sub_repo=None, pen_repo=None,
              p_repo=None, t_repo=None, s_repo=None,
              strategy=None, bus=None, clock=None):
    return MilestoneService(
        m_repo or InMemoryMilestoneRepository(),
        sub_repo or InMemorySubmissionRepository(),
        pen_repo or InMemoryPenaltyRepository(),
        p_repo or InMemoryProjectRepository(),
        t_repo or InMemoryTeamRepository(),
        s_repo or InMemoryStudentRepository(),
        strategy or FlatPenaltyStrategy(2),
        bus or EventBus(),
        clock=clock or (lambda: datetime(2025, 10, 15, 0, 0)),
    )


class TestMilestoneServiceAddMilestone:
    def test_add_milestone_returns_milestone(self):
        p_repo = InMemoryProjectRepository()
        p_repo.add(_make_project())
        m_repo = InMemoryMilestoneRepository()
        svc = _make_svc(m_repo=m_repo, p_repo=p_repo)
        m = svc.add_milestone("p1", "Sprint 1", _DUE)
        assert m.project_id == "p1"
        assert m.title == "Sprint 1"
        assert m.due_date == _DUE

    def test_add_milestone_stored(self):
        p_repo = InMemoryProjectRepository()
        p_repo.add(_make_project())
        m_repo = InMemoryMilestoneRepository()
        svc = _make_svc(m_repo=m_repo, p_repo=p_repo)
        m = svc.add_milestone("p1", "Sprint", _DUE)
        assert m_repo.get_by_id(m.id) is m

    def test_add_milestone_unknown_project_raises(self):
        svc = _make_svc()
        with pytest.raises(Exception):
            svc.add_milestone("unknown", "Sprint", _DUE)


class TestMilestoneServiceSubmit:
    def _full_setup(self):
        m_repo = InMemoryMilestoneRepository()
        sub_repo = InMemorySubmissionRepository()
        pen_repo = InMemoryPenaltyRepository()
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        s_repo = InMemoryStudentRepository()

        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        t_repo.add(_make_team("t1", ["s1", "s2"]))
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))

        return m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo

    def test_on_time_submit_creates_submission(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        clock = lambda: _DUE  # exactly on due date
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=clock)
        submission, penalties = svc.submit("m1")
        assert submission.milestone_id == "m1"
        assert submission.team_id == "t1"
        assert penalties == []

    def test_on_time_submit_updates_milestone_status(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE)
        svc.submit("m1")
        assert m_repo.get_by_id("m1").status == MilestoneStatus.SUBMITTED

    def test_late_submit_creates_penalties_for_each_member(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        late = _DUE + timedelta(days=3)
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        strategy=FlatPenaltyStrategy(2),
                        clock=lambda: late)
        submission, penalties = svc.submit("m1")
        assert len(penalties) == 2
        assert all(p.points == 6 for p in penalties)  # 3 days × 2
        student_ids = {p.student_id for p in penalties}
        assert student_ids == {"s1", "s2"}

    def test_late_submit_sets_milestone_status_late(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE + timedelta(days=1))
        svc.submit("m1")
        assert m_repo.get_by_id("m1").status == MilestoneStatus.LATE

    def test_late_submit_stores_penalties_in_repo(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE + timedelta(days=2))
        svc.submit("m1")
        all_penalties = pen_repo.list_all()
        assert len(all_penalties) == 2

    def test_submit_stores_submission_in_repo(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE)
        svc.submit("m1")
        assert len(sub_repo.list_all()) == 1

    def test_submit_fires_event(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        bus = MagicMock(spec=EventBus)
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        bus=bus, clock=lambda: _DUE)
        svc.submit("m1")
        bus.notify_milestone_status.assert_called_once()

    def test_submit_unknown_milestone_raises(self):
        svc = _make_svc()
        with pytest.raises(MilestoneNotFoundError):
            svc.submit("unknown")

    def test_submit_already_submitted_raises(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE)
        svc.submit("m1")
        with pytest.raises(AlreadySubmittedError):
            svc.submit("m1")

    def test_submit_increments_missed_deadlines_when_late(self):
        m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo = self._full_setup()
        svc = _make_svc(m_repo, sub_repo, pen_repo, p_repo, t_repo, s_repo,
                        clock=lambda: _DUE + timedelta(days=1))
        svc.submit("m1")
        assert s_repo.get_by_id("s1").missed_deadlines_count == 1
        assert s_repo.get_by_id("s2").missed_deadlines_count == 1

    def test_submit_team_not_in_repo_creates_no_penalties(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        p_repo.add(_make_project("p1", team_id="ghost_team"))
        m_repo.add(_make_milestone("m1", "p1"))
        svc = _make_svc(m_repo=m_repo, p_repo=p_repo,
                        clock=lambda: _DUE + timedelta(days=5))
        submission, penalties = svc.submit("m1")
        assert penalties == []

    def test_submit_team_member_not_in_student_repo_skips_counter(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        t_repo = InMemoryTeamRepository()
        # team member "ghost" is not in student_repo
        t_repo.add(_make_team("t1", members=["ghost"]))
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))
        svc = _make_svc(m_repo=m_repo, p_repo=p_repo, t_repo=t_repo,
                        clock=lambda: _DUE + timedelta(days=2))
        submission, penalties = svc.submit("m1")
        assert len(penalties) == 1  # penalty still created even without student record

    def test_submit_no_team_creates_no_penalties(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        p_repo.add(_make_project("p1", team_id=None))
        m_repo.add(_make_milestone("m1", "p1"))
        svc = _make_svc(m_repo=m_repo, p_repo=p_repo,
                        clock=lambda: _DUE + timedelta(days=5))
        submission, penalties = svc.submit("m1")
        assert penalties == []


class TestMilestoneServiceMarkMissed:
    def test_mark_missed_sets_status(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()

        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", ["s1"]))
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))

        svc = _make_svc(m_repo=m_repo, p_repo=p_repo,
                        t_repo=t_repo, s_repo=s_repo,
                        strategy=FlatPenaltyStrategy(2),
                        clock=lambda: _DUE + timedelta(days=5))
        penalties = svc.mark_missed("m1")
        assert m_repo.get_by_id("m1").status == MilestoneStatus.MISSED
        assert len(penalties) > 0

    def test_mark_missed_unknown_raises(self):
        svc = _make_svc()
        with pytest.raises(MilestoneNotFoundError):
            svc.mark_missed("unknown")
