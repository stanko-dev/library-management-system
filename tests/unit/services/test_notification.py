"""TDD tests for StudentNotifier (concrete observer)."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.student import Student
from models.team import Team
from models.project import Project
from models.milestone import Milestone
from models.queue_request import QueueRequest
from models.enums import StudentRole, ProjectStatus, MilestoneStatus, QueueRequestStatus
from services.events import (
    MilestoneStatusChangedEvent, TeamSpotAvailableEvent, DeadlineObserver,
)
from services.notification import StudentNotifier, Notification
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.milestone_repo import InMemoryMilestoneRepository
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository

from datetime import timedelta

_NOW = datetime(2025, 9, 1, 10, 0)


def _make_student(sid="s1", active=0):
    return Student(sid, f"Student {sid}", StudentRole.MEMBER,
                   active_projects_count=active)


def _make_team(tid="t1", capacity=4, members=None):
    return Team(tid, f"Team {tid}", capacity, member_ids=members or [])


def _make_project(pid="p1", team_id="t1"):
    return Project(pid, "Project", "desc", ProjectStatus.ACTIVE,
                   team_id=team_id, created_at=_NOW)


def _make_milestone(mid="m1", project_id="p1"):
    return Milestone(mid, project_id, "Sprint", datetime(2025, 10, 15))


def _make_request(rid="qr1", student_id="s1", team_id="t1", active=0):
    return QueueRequest(rid, student_id, team_id, _NOW, _NOW + timedelta(days=7))


def _make_repos():
    return (
        InMemoryStudentRepository(),
        InMemoryTeamRepository(),
        InMemoryProjectRepository(),
        InMemoryMilestoneRepository(),
        InMemoryQueueRequestRepository(),
    )


def _make_notifier(student_repo=None, team_repo=None, project_repo=None,
                   milestone_repo=None, queue_repo=None):
    return StudentNotifier(
        milestone_repo or InMemoryMilestoneRepository(),
        project_repo or InMemoryProjectRepository(),
        team_repo or InMemoryTeamRepository(),
        queue_repo or InMemoryQueueRequestRepository(),
        student_repo or InMemoryStudentRepository(),
    )


class TestStudentNotifierIsObserver:
    def test_is_deadline_observer(self):
        assert isinstance(_make_notifier(), DeadlineObserver)


class TestStudentNotifierMilestoneNotifications:
    def test_milestone_with_team_notifies_all_members(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        p_repo = InMemoryProjectRepository()
        m_repo = InMemoryMilestoneRepository()

        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        team = _make_team("t1", members=["s1", "s2"])
        t_repo.add(team)
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))

        notifier = _make_notifier(s_repo, t_repo, p_repo, m_repo)
        event = MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE)
        notifier.on_milestone_status_changed(event)

        notes = notifier.get_notifications()
        notified_ids = {n.student_id for n in notes}
        assert notified_ids == {"s1", "s2"}

    def test_milestone_notifications_have_correct_milestone_id(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        p_repo = InMemoryProjectRepository()
        m_repo = InMemoryMilestoneRepository()

        s_repo.add(_make_student("s1"))
        t_repo.add(_make_team("t1", members=["s1"]))
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))

        notifier = _make_notifier(s_repo, t_repo, p_repo, m_repo)
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("m1", MilestoneStatus.MISSED))
        assert notifier.get_notifications()[0].milestone_id == "m1"

    def test_milestone_unknown_id_does_nothing(self):
        notifier = _make_notifier()
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("unknown", MilestoneStatus.LATE))
        assert notifier.get_notifications() == []

    def test_milestone_project_not_found_does_nothing(self):
        m_repo = InMemoryMilestoneRepository()
        m_repo.add(_make_milestone("m1", "no_project"))
        notifier = _make_notifier(milestone_repo=m_repo)
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        assert notifier.get_notifications() == []

    def test_milestone_project_no_team_does_nothing(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        m_repo.add(_make_milestone("m1", "p1"))
        p_repo.add(_make_project("p1", team_id=None))

        notifier = _make_notifier(project_repo=p_repo, milestone_repo=m_repo)
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        assert notifier.get_notifications() == []

    def test_milestone_team_not_found_does_nothing(self):
        m_repo = InMemoryMilestoneRepository()
        p_repo = InMemoryProjectRepository()
        m_repo.add(_make_milestone("m1", "p1"))
        p_repo.add(_make_project("p1", "no_team"))

        notifier = _make_notifier(project_repo=p_repo, milestone_repo=m_repo)
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        assert notifier.get_notifications() == []

    def test_get_notifications_for_student(self):
        s_repo = InMemoryStudentRepository()
        t_repo = InMemoryTeamRepository()
        p_repo = InMemoryProjectRepository()
        m_repo = InMemoryMilestoneRepository()

        s_repo.add(_make_student("s1"))
        s_repo.add(_make_student("s2"))
        t_repo.add(_make_team("t1", members=["s1", "s2"]))
        p_repo.add(_make_project("p1", "t1"))
        m_repo.add(_make_milestone("m1", "p1"))

        notifier = _make_notifier(s_repo, t_repo, p_repo, m_repo)
        notifier.on_milestone_status_changed(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        s1_notes = notifier.get_notifications_for_student("s1")
        assert len(s1_notes) == 1 and s1_notes[0].student_id == "s1"


class TestStudentNotifierTeamSpotNotifications:
    def test_team_spot_notifies_first_in_queue(self):
        s_repo = InMemoryStudentRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1", active=2))
        s_repo.add(_make_student("s2", active=0))
        q_repo.add(_make_request("qr1", "s1", "t1"))
        q_repo.add(_make_request("qr2", "s2", "t1"))

        notifier = _make_notifier(s_repo, queue_repo=q_repo)
        notifier.on_team_spot_available(TeamSpotAvailableEvent("t1"))
        notes = notifier.get_notifications()
        assert len(notes) == 1 and notes[0].student_id == "s2"
        assert notes[0].team_id == "t1"

    def test_team_spot_empty_queue_does_nothing(self):
        notifier = _make_notifier()
        notifier.on_team_spot_available(TeamSpotAvailableEvent("t1"))
        assert notifier.get_notifications() == []

    def test_team_spot_no_match_for_team_does_nothing(self):
        s_repo = InMemoryStudentRepository()
        q_repo = InMemoryQueueRequestRepository()
        s_repo.add(_make_student("s1"))
        q_repo.add(_make_request("qr1", "s1", "t2"))

        notifier = _make_notifier(s_repo, queue_repo=q_repo)
        notifier.on_team_spot_available(TeamSpotAvailableEvent("t1"))
        assert notifier.get_notifications() == []

    def test_get_notifications_returns_copy(self):
        notifier = _make_notifier()
        n1 = notifier.get_notifications()
        n2 = notifier.get_notifications()
        assert n1 is not n2


class TestNotificationDataclass:
    def test_milestone_notification_fields(self):
        n = Notification(student_id="s1", milestone_id="m1")
        assert n.student_id == "s1"
        assert n.milestone_id == "m1"
        assert n.team_id is None

    def test_team_spot_notification_fields(self):
        n = Notification(student_id="s1", team_id="t1")
        assert n.student_id == "s1"
        assert n.team_id == "t1"
        assert n.milestone_id is None
