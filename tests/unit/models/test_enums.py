import pytest
from models.enums import StudentRole, ProjectStatus, MilestoneStatus, QueueRequestStatus


class TestStudentRole:
    def test_leader_value(self):
        assert StudentRole.LEADER.value == "leader"

    def test_member_value(self):
        assert StudentRole.MEMBER.value == "member"

    def test_all_roles(self):
        assert set(StudentRole) == {StudentRole.LEADER, StudentRole.MEMBER}

    def test_from_value_leader(self):
        assert StudentRole("leader") == StudentRole.LEADER

    def test_from_value_member(self):
        assert StudentRole("member") == StudentRole.MEMBER

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            StudentRole("admin")


class TestProjectStatus:
    def test_draft_value(self):
        assert ProjectStatus.DRAFT.value == "draft"

    def test_active_value(self):
        assert ProjectStatus.ACTIVE.value == "active"

    def test_completed_value(self):
        assert ProjectStatus.COMPLETED.value == "completed"

    def test_archived_value(self):
        assert ProjectStatus.ARCHIVED.value == "archived"

    def test_all_statuses(self):
        assert set(ProjectStatus) == {
            ProjectStatus.DRAFT,
            ProjectStatus.ACTIVE,
            ProjectStatus.COMPLETED,
            ProjectStatus.ARCHIVED,
        }

    def test_from_value(self):
        assert ProjectStatus("active") == ProjectStatus.ACTIVE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ProjectStatus("unknown")


class TestMilestoneStatus:
    def test_pending_value(self):
        assert MilestoneStatus.PENDING.value == "pending"

    def test_submitted_value(self):
        assert MilestoneStatus.SUBMITTED.value == "submitted"

    def test_late_value(self):
        assert MilestoneStatus.LATE.value == "late"

    def test_missed_value(self):
        assert MilestoneStatus.MISSED.value == "missed"

    def test_all_statuses(self):
        assert set(MilestoneStatus) == {
            MilestoneStatus.PENDING,
            MilestoneStatus.SUBMITTED,
            MilestoneStatus.LATE,
            MilestoneStatus.MISSED,
        }

    def test_from_value(self):
        assert MilestoneStatus("late") == MilestoneStatus.LATE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MilestoneStatus("done")


class TestQueueRequestStatus:
    def test_pending_value(self):
        assert QueueRequestStatus.PENDING.value == "pending"

    def test_fulfilled_value(self):
        assert QueueRequestStatus.FULFILLED.value == "fulfilled"

    def test_expired_value(self):
        assert QueueRequestStatus.EXPIRED.value == "expired"

    def test_cancelled_value(self):
        assert QueueRequestStatus.CANCELLED.value == "cancelled"

    def test_all_statuses(self):
        assert set(QueueRequestStatus) == {
            QueueRequestStatus.PENDING,
            QueueRequestStatus.FULFILLED,
            QueueRequestStatus.EXPIRED,
            QueueRequestStatus.CANCELLED,
        }

    def test_from_value_cancelled(self):
        assert QueueRequestStatus("cancelled") == QueueRequestStatus.CANCELLED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            QueueRequestStatus("unknown")
