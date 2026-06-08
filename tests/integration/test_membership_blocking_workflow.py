"""Integration: penalty accumulation → blocking → unblocking workflow."""
import pytest
from datetime import datetime, timedelta

from models.enums import MilestoneStatus
from tests.integration.conftest import make_student, make_team

_DUE = datetime(2025, 10, 15, 0, 0)


class TestPenaltyToBlockingWorkflow:
    def test_accumulate_penalties_then_block(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")

        m1 = svc.milestone.add_milestone(p.id, "Sprint 1", _DUE)
        clock.set(_DUE + timedelta(days=3))
        svc.milestone.submit(m1.id)

        m2 = svc.milestone.add_milestone(p.id, "Sprint 2", _DUE)
        clock.set(_DUE + timedelta(days=4))
        svc.milestone.submit(m2.id)

        total = repos.penalties.total_unresolved_by_student("s1")
        assert total == 14  # 6 + 8

        blocked = svc.membership.evaluate("s1")
        assert blocked is True
        assert repos.students.get_by_id("s1").is_blocked is True

    def test_resolve_penalties_then_unblock(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")
        m = svc.milestone.add_milestone(p.id, "Sprint", _DUE)
        clock.set(_DUE + timedelta(days=6))
        svc.milestone.submit(m.id)

        svc.membership.evaluate("s1")
        assert repos.students.get_by_id("s1").is_blocked is True

        for pen in repos.penalties.find_unresolved_by_student("s1"):
            pen.is_resolved = True
            repos.penalties.update(pen)

        unblocked = svc.membership.evaluate("s1")
        assert unblocked is False
        assert repos.students.get_by_id("s1").is_blocked is False

    def test_force_block_prevents_team_join(self, repos, svc):
        repos.students.add(make_student("s1"))
        repos.teams.add(make_team("t1", 4))
        svc.membership.block("s1")
        from utils.exceptions import StudentBlockedError
        with pytest.raises(StudentBlockedError):
            svc.team.join_or_queue("s1", "t1")

    def test_block_by_missed_deadlines(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 4)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        p = svc.project.create_project("Project", "desc", team_id="t1")

        for i in range(3):
            m = svc.milestone.add_milestone(p.id, f"Sprint {i}", _DUE)
            clock.set(_DUE + timedelta(days=1))
            svc.milestone.submit(m.id)

        assert repos.students.get_by_id("s1").missed_deadlines_count == 3
        blocked = svc.membership.evaluate("s1")
        assert blocked is True

    def test_unblock_allows_team_join(self, repos, svc):
        s = make_student("s1")
        s.is_blocked = True
        repos.students.add(s)
        repos.teams.add(make_team("t1", 4))
        svc.membership.unblock("s1")
        result = svc.team.join_or_queue("s1", "t1")
        assert "s1" in repos.teams.get_by_id("t1").member_ids


class TestFullLifecycleWorkflow:
    def test_full_student_project_cycle(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        repos.students.add(make_student("s2"))
        repos.teams.add(make_team("t1", 2))

        svc.team.join_or_queue("s1", "t1")
        svc.team.join_or_queue("s2", "t1")

        p = svc.project.create_project("Capstone", "Final project", team_id="t1")
        from models.enums import ProjectStatus
        svc.project.change_status(p.id, ProjectStatus.ACTIVE)

        m = svc.milestone.add_milestone(p.id, "Prototype", _DUE)
        clock.set(_DUE)
        submission, penalties = svc.milestone.submit(m.id)

        assert penalties == []
        assert repos.milestones.get_by_id(m.id).status == MilestoneStatus.SUBMITTED
        assert len(repos.submissions.find_by_milestone(m.id)) == 1

        svc.project.change_status(p.id, ProjectStatus.COMPLETED)
        assert repos.projects.get_by_id(p.id).status == ProjectStatus.COMPLETED

    def test_queue_then_leave_notifies_queued_student(self, repos, svc, clock):
        for i in range(4):
            repos.students.add(make_student(f"s{i}"))

        repos.teams.add(make_team("t1", 2))
        svc.team.join_or_queue("s0", "t1")
        svc.team.join_or_queue("s1", "t1")
        svc.team.join_or_queue("s2", "t1")

        notes_before = svc.notifier.get_notifications_for_student("s2")
        assert notes_before == []

        svc.team.leave_team("s0", "t1")
        notes_after = svc.notifier.get_notifications_for_student("s2")
        assert len(notes_after) == 1
