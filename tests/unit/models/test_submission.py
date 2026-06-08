import pytest
from datetime import datetime
from models.submission import Submission


@pytest.fixture
def valid_submission() -> Submission:
    return Submission(
        id="sub1",
        milestone_id="m1",
        team_id="t1",
        submitted_at=datetime(2025, 10, 14, 12, 0),
    )


class TestSubmissionCreation:
    def test_all_fields_set(self, valid_submission):
        assert valid_submission.id == "sub1"
        assert valid_submission.milestone_id == "m1"
        assert valid_submission.team_id == "t1"
        assert valid_submission.submitted_at == datetime(2025, 10, 14, 12, 0)

    def test_submission_with_late_timestamp(self):
        s = Submission("sub2", "m2", "t2", datetime(2025, 11, 1))
        assert s.submitted_at == datetime(2025, 11, 1)


class TestSubmissionIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Submission("", "m1", "t1", datetime(2025, 10, 14))

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Submission("   ", "m1", "t1", datetime(2025, 10, 14))


class TestSubmissionMilestoneIdValidation:
    def test_empty_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            Submission("sub1", "", "t1", datetime(2025, 10, 14))

    def test_whitespace_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            Submission("sub1", "   ", "t1", datetime(2025, 10, 14))


class TestSubmissionTeamIdValidation:
    def test_empty_team_id_raises(self):
        with pytest.raises(ValueError, match="team_id"):
            Submission("sub1", "m1", "", datetime(2025, 10, 14))

    def test_whitespace_team_id_raises(self):
        with pytest.raises(ValueError, match="team_id"):
            Submission("sub1", "m1", "   ", datetime(2025, 10, 14))
