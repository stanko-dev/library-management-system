"""TDD tests for MembershipService."""
import pytest

from models.student import Student
from models.penalty import Penalty
from models.enums import StudentRole
from services.membership_service import MembershipService
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.penalty_repo import InMemoryPenaltyRepository
from utils.exceptions import StudentNotFoundError


def _make_student(sid="s1", missed=0, blocked=False):
    return Student(sid, f"S{sid}", StudentRole.MEMBER,
                   is_blocked=blocked, missed_deadlines_count=missed)


def _make_penalty(pid, student_id, points, is_resolved=False):
    return Penalty(pid, student_id, "m1", points, is_resolved=is_resolved)


def _svc(s_repo=None, pen_repo=None, max_points=10, max_missed=3):
    return MembershipService(
        s_repo or InMemoryStudentRepository(),
        pen_repo or InMemoryPenaltyRepository(),
        max_unresolved_points=max_points,
        max_missed_deadlines=max_missed,
    )


class TestMembershipServiceEvaluate:
    def test_no_violations_unblocks(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student(blocked=True))
        pen_repo = InMemoryPenaltyRepository()
        svc = _svc(s_repo, pen_repo)
        result = svc.evaluate("s1")
        assert result is False
        assert s_repo.get_by_id("s1").is_blocked is False

    def test_blocked_when_penalty_points_exceed_threshold(self):
        s_repo = InMemoryStudentRepository()
        pen_repo = InMemoryPenaltyRepository()
        s_repo.add(_make_student())
        pen_repo.add(_make_penalty("pen1", "s1", 5))
        pen_repo.add(_make_penalty("pen2", "s1", 6, False))
        svc = _svc(s_repo, pen_repo, max_points=10)
        result = svc.evaluate("s1")
        assert result is True
        assert s_repo.get_by_id("s1").is_blocked is True

    def test_blocked_at_exact_threshold(self):
        s_repo = InMemoryStudentRepository()
        pen_repo = InMemoryPenaltyRepository()
        s_repo.add(_make_student())
        pen_repo.add(_make_penalty("pen1", "s1", 10))
        svc = _svc(s_repo, pen_repo, max_points=10)
        result = svc.evaluate("s1")
        assert result is True

    def test_not_blocked_below_threshold(self):
        s_repo = InMemoryStudentRepository()
        pen_repo = InMemoryPenaltyRepository()
        s_repo.add(_make_student())
        pen_repo.add(_make_penalty("pen1", "s1", 9))
        svc = _svc(s_repo, pen_repo, max_points=10)
        result = svc.evaluate("s1")
        assert result is False

    def test_blocked_when_missed_deadlines_exceed_threshold(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student(missed=3))
        svc = _svc(s_repo, max_missed=3)
        result = svc.evaluate("s1")
        assert result is True

    def test_resolved_penalties_not_counted(self):
        s_repo = InMemoryStudentRepository()
        pen_repo = InMemoryPenaltyRepository()
        s_repo.add(_make_student())
        pen_repo.add(_make_penalty("pen1", "s1", 50, is_resolved=True))
        svc = _svc(s_repo, pen_repo, max_points=10)
        result = svc.evaluate("s1")
        assert result is False

    def test_evaluate_unknown_student_raises(self):
        svc = _svc()
        with pytest.raises(StudentNotFoundError):
            svc.evaluate("unknown")

    def test_blocked_clears_when_penalties_resolved(self):
        s_repo = InMemoryStudentRepository()
        pen_repo = InMemoryPenaltyRepository()
        s_repo.add(_make_student(blocked=True))
        p = _make_penalty("pen1", "s1", 20)
        pen_repo.add(p)
        svc = _svc(s_repo, pen_repo, max_points=10)
        svc.evaluate("s1")
        assert s_repo.get_by_id("s1").is_blocked is True
        p.is_resolved = True
        pen_repo.update(p)
        svc.evaluate("s1")
        assert s_repo.get_by_id("s1").is_blocked is False


class TestMembershipServiceBlock:
    def test_block_sets_is_blocked(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student())
        svc = _svc(s_repo)
        svc.block("s1")
        assert s_repo.get_by_id("s1").is_blocked is True

    def test_block_already_blocked_is_idempotent(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student(blocked=True))
        svc = _svc(s_repo)
        svc.block("s1")
        assert s_repo.get_by_id("s1").is_blocked is True

    def test_block_unknown_student_raises(self):
        svc = _svc()
        with pytest.raises(StudentNotFoundError):
            svc.block("unknown")


class TestMembershipServiceUnblock:
    def test_unblock_clears_is_blocked(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student(blocked=True))
        svc = _svc(s_repo)
        svc.unblock("s1")
        assert s_repo.get_by_id("s1").is_blocked is False

    def test_unblock_already_unblocked_is_idempotent(self):
        s_repo = InMemoryStudentRepository()
        s_repo.add(_make_student(blocked=False))
        svc = _svc(s_repo)
        svc.unblock("s1")
        assert s_repo.get_by_id("s1").is_blocked is False

    def test_unblock_unknown_student_raises(self):
        svc = _svc()
        with pytest.raises(StudentNotFoundError):
            svc.unblock("unknown")
