import pytest
from datetime import datetime
from models.milestone import Milestone
from models.enums import MilestoneStatus


@pytest.fixture
def valid_milestone() -> Milestone:
    return Milestone(
        id="m1",
        project_id="p1",
        title="Sprint 1",
        due_date=datetime(2025, 10, 15),
    )


class TestMilestoneCreation:
    def test_all_fields_set(self, valid_milestone):
        assert valid_milestone.id == "m1"
        assert valid_milestone.project_id == "p1"
        assert valid_milestone.title == "Sprint 1"
        assert valid_milestone.due_date == datetime(2025, 10, 15)

    def test_default_status_pending(self, valid_milestone):
        assert valid_milestone.status == MilestoneStatus.PENDING

    def test_default_submitted_at_none(self, valid_milestone):
        assert valid_milestone.submitted_at is None

    def test_explicit_status_submitted(self):
        m = Milestone("m2", "p1", "Sprint 2", datetime(2025, 11, 1),
                      status=MilestoneStatus.SUBMITTED)
        assert m.status == MilestoneStatus.SUBMITTED

    def test_explicit_status_late(self):
        m = Milestone("m3", "p1", "Sprint 3", datetime(2025, 11, 1),
                      status=MilestoneStatus.LATE)
        assert m.status == MilestoneStatus.LATE

    def test_explicit_status_missed(self):
        m = Milestone("m4", "p1", "Sprint 4", datetime(2025, 11, 1),
                      status=MilestoneStatus.MISSED)
        assert m.status == MilestoneStatus.MISSED

    def test_submitted_at_on_time(self):
        due = datetime(2025, 10, 15)
        submitted = datetime(2025, 10, 14)
        m = Milestone("m5", "p1", "Early Submit", due, submitted_at=submitted)
        assert m.submitted_at == submitted

    def test_submitted_at_exactly_on_due(self):
        due = datetime(2025, 10, 15)
        m = Milestone("m6", "p1", "On Time", due, submitted_at=due)
        assert m.submitted_at == due

    def test_submitted_at_after_due_allowed(self):
        due = datetime(2025, 10, 15)
        submitted = datetime(2025, 10, 20)
        m = Milestone("m7", "p1", "Late Submit", due, submitted_at=submitted)
        assert m.submitted_at == submitted


class TestMilestoneIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Milestone("", "p1", "Sprint 1", datetime(2025, 10, 15))

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Milestone("   ", "p1", "Sprint 1", datetime(2025, 10, 15))


class TestMilestoneProjectIdValidation:
    def test_empty_project_id_raises(self):
        with pytest.raises(ValueError, match="project_id"):
            Milestone("m1", "", "Sprint 1", datetime(2025, 10, 15))

    def test_whitespace_project_id_raises(self):
        with pytest.raises(ValueError, match="project_id"):
            Milestone("m1", "   ", "Sprint 1", datetime(2025, 10, 15))


class TestMilestoneTitleValidation:
    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Milestone("m1", "p1", "", datetime(2025, 10, 15))

    def test_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Milestone("m1", "p1", "   ", datetime(2025, 10, 15))
