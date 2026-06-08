"""Integration: team join, queue, leave, and spot notification workflow."""
import pytest
from datetime import datetime, timedelta

from models.team import Team
from models.queue_request import QueueRequest
from models.enums import QueueRequestStatus
from utils.exceptions import StudentBlockedError, DuplicateQueueRequestError
from tests.integration.conftest import make_student, make_team


class TestTeamJoinWorkflow:
    def test_join_adds_member_and_increments_counter(self, repos, svc):
        repos.students.add(make_student("s1"))
        repos.teams.add(make_team("t1", 3))
        svc.team.join_or_queue("s1", "t1")
        assert "s1" in repos.teams.get_by_id("t1").member_ids
        assert repos.students.get_by_id("s1").active_projects_count == 1

    def test_join_full_team_creates_queue_request(self, repos, svc):
        for i in range(4):
            repos.students.add(make_student(f"s{i}"))
        t = make_team("t1", 3)
        t.member_ids = ["s0", "s1", "s2"]
        repos.teams.add(t)
        result = svc.team.join_or_queue("s3", "t1")
        assert isinstance(result, QueueRequest)
        assert repos.queue_requests.find_pending_by_team("t1") != []

    def test_blocked_student_cannot_join(self, repos, svc):
        s = make_student("s1")
        s.is_blocked = True
        repos.students.add(s)
        repos.teams.add(make_team("t1"))
        with pytest.raises(StudentBlockedError):
            svc.team.join_or_queue("s1", "t1")

    def test_join_multiple_students_fills_team(self, repos, svc):
        for i in range(3):
            repos.students.add(make_student(f"s{i}"))
        repos.teams.add(make_team("t1", 3))
        for i in range(3):
            svc.team.join_or_queue(f"s{i}", "t1")
        team = repos.teams.get_by_id("t1")
        assert team.is_full
        assert len(team.member_ids) == 3


class TestTeamLeaveWorkflow:
    def test_leave_removes_member_fires_event(self, repos, svc):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 3)
        t.member_ids = ["s1", "s2"]
        repos.teams.add(t)
        svc.team.leave_team("s1", "t1")
        assert "s1" not in repos.teams.get_by_id("t1").member_ids

    def test_leave_notifies_queued_student(self, repos, svc):
        for i in range(5):
            repos.students.add(make_student(f"s{i}"))
        t = make_team("t1", 3)
        t.member_ids = ["s0", "s1", "s2"]
        repos.teams.add(t)
        svc.team.join_or_queue("s3", "t1")
        svc.team.leave_team("s0", "t1")
        notes = svc.notifier.get_notifications_for_student("s3")
        assert len(notes) == 1 and notes[0].team_id == "t1"

    def test_leave_decrements_active_project_count(self, repos, svc):
        s = make_student("s1")
        s.active_projects_count = 2
        repos.students.add(s)
        t = make_team("t1", 3)
        t.member_ids = ["s1"]
        repos.teams.add(t)
        svc.team.leave_team("s1", "t1")
        assert repos.students.get_by_id("s1").active_projects_count == 1


class TestQueuePriorityWorkflow:
    def test_lower_active_projects_serves_first(self, repos, svc, clock):
        # s1 has 3 active projects; s2 has 0 → s2 should be priority
        s1 = make_student("s1")
        s1.active_projects_count = 3
        s2 = make_student("s2")
        s2.active_projects_count = 0
        repos.students.add(s1)
        repos.students.add(s2)
        t = make_team("t1", 2)
        t.member_ids = ["x1", "x2"]
        repos.teams.add(t)
        svc.team.join_or_queue("s1", "t1")
        clock.advance(seconds=1)
        svc.team.join_or_queue("s2", "t1")

        next_req = svc.team.get_next_in_queue("t1")
        assert next_req.student_id == "s2"

    def test_fifo_within_same_priority(self, repos, svc, clock):
        s1 = make_student("s1")
        s2 = make_student("s2")
        repos.students.add(s1)
        repos.students.add(s2)
        t = make_team("t1", 1)
        t.member_ids = ["x1"]
        repos.teams.add(t)
        svc.team.join_or_queue("s1", "t1")
        clock.advance(seconds=1)
        svc.team.join_or_queue("s2", "t1")

        next_req = svc.team.get_next_in_queue("t1")
        assert next_req.student_id == "s1"


class TestQueueExpiryWorkflow:
    def test_expired_requests_not_served(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 1)
        t.member_ids = ["x1"]
        repos.teams.add(t)
        svc.team.join_or_queue("s1", "t1")

        clock.advance(days=100)
        expired = svc.team.expire_old()
        assert len(expired) == 1
        assert expired[0].status == QueueRequestStatus.EXPIRED

    def test_expire_only_old_requests(self, repos, svc, clock):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 1)
        t.member_ids = ["x1"]
        repos.teams.add(t)
        svc.team.join_or_queue("s1", "t1")

        clock.advance(days=1)
        expired = svc.team.expire_old()
        assert expired == []

    def test_duplicate_queue_request_raises(self, repos, svc):
        repos.students.add(make_student("s1"))
        t = make_team("t1", 1)
        t.member_ids = ["x1"]
        repos.teams.add(t)
        svc.team.join_or_queue("s1", "t1")
        with pytest.raises(DuplicateQueueRequestError):
            svc.team.join_or_queue("s1", "t1")
