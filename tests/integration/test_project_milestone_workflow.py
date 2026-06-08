"""Integration: full project → milestone → submission → penalty → notification workflow."""
import pytest
from datetime import datetime, timedelta

from models.enums import ProjectStatus, MilestoneStatus
from utils.exceptions import AlreadySubmittedError, MilestoneNotFoundError
from tests.integration.conftest import make_student, make_team

_DUE = datetime(2025, 10, 15, 0, 0)


class TestOnTimeSubmissionWorkflow:
    def test_on_time_submit_no_penalties(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("AI Research", "desc", team_id="t1")
        svc.project.change_status(p.id, ProjectStatus.ACTIVE)
        m = svc.milestone.add_milestone(p.id, "Sprint 1", _DUE)

        clock.set(_DUE)
        submission, penalties = svc.milestone.submit(m.id)
        assert penalties == []
        assert repos.milestones.get_by_id(m.id).status == MilestoneStatus.SUBMITTED

    def test_on_time_submit_creates_submission_record(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE)
        svc.milestone.submit(m.id)
        assert len(repos.submissions.find_by_milestone(m.id)) == 1

    def test_submit_fires_milestone_notification(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE)
        svc.milestone.submit(m.id)
        notes = svc.notifier.get_notifications_for_student("s1")
        assert len(notes) == 1


class TestLateSubmissionWorkflow:
    def test_late_submit_creates_penalty_per_member(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        repos.students.add(make_student("s2"))
        t = make_team("t1", 4)
        t.member_ids = ["s1", "s2"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint 1", _DUE)

        clock.set(_DUE + timedelta(days=3))
        submission, penalties = svc.milestone.submit(m.id)
        assert len(penalties) == 2
        assert all(pen.points == 6 for pen in penalties)  # 3 days × 2 pts

    def test_late_submit_sets_milestone_late(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint 1", _DUE)
        clock.set(_DUE + timedelta(days=1))
        svc.milestone.submit(m.id)
        assert repos.milestones.get_by_id(m.id).status == MilestoneStatus.LATE

    def test_late_submit_increments_missed_deadlines(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE + timedelta(days=2))
        svc.milestone.submit(m.id)
        assert repos.students.get_by_id("s1").missed_deadlines_count == 1

    def test_late_submit_stores_penalties_in_repo(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE + timedelta(days=4))
        svc.milestone.submit(m.id)
        stored = repos.penalties.find_by_student("s1")
        assert len(stored) == 1 and stored[0].points == 8

    def test_double_submit_raises(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE)
        svc.milestone.submit(m.id)
        with pytest.raises(AlreadySubmittedError):
            svc.milestone.submit(m.id)


class TestMissedMilestoneWorkflow:
    def test_mark_missed_sets_status_and_penalties(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE + timedelta(days=7))
        penalties = svc.milestone.mark_missed(m.id)
        assert repos.milestones.get_by_id(m.id).status == MilestoneStatus.MISSED
        assert len(penalties) == 1
        assert penalties[0].points == 14

    def test_mark_missed_fires_notification(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE + timedelta(days=5))
        svc.milestone.mark_missed(m.id)
        notes = svc.notifier.get_notifications_for_student("s1")
        assert len(notes) == 1


class TestProjectStatusWorkflow:
    def test_full_project_lifecycle(self, repos, svc):
        repos.teams.add(make_team("t1"))
        p = svc.project.create_project("Project", "desc")
        assert p.status == ProjectStatus.DRAFT
        svc.project.assign_team(p.id, "t1")
        svc.project.change_status(p.id, ProjectStatus.ACTIVE)
        assert repos.projects.get_by_id(p.id).status == ProjectStatus.ACTIVE
        svc.project.change_status(p.id, ProjectStatus.COMPLETED)
        assert repos.projects.get_by_id(p.id).status == ProjectStatus.COMPLETED
        svc.project.change_status(p.id, ProjectStatus.ARCHIVED)
        assert repos.projects.get_by_id(p.id).status == ProjectStatus.ARCHIVED

    def test_multiple_milestones_tracked(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m1 = svc.milestone.add_milestone(p.id, "Sprint 1", _DUE)
        m2 = svc.milestone.add_milestone(p.id, "Sprint 2", _DUE + timedelta(weeks=2))
        clock.set(_DUE)
        svc.milestone.submit(m1.id)
        milestones = repos.milestones.find_by_project(p.id)
        assert len(milestones) == 2
        assert repos.milestones.get_by_id(m1.id).status == MilestoneStatus.SUBMITTED
        assert repos.milestones.get_by_id(m2.id).status == MilestoneStatus.PENDING
