import pytest
from models.penalty import Penalty


@pytest.fixture
def valid_penalty() -> Penalty:
    return Penalty(id="pen1", student_id="s1", milestone_id="m1", points=5)


class TestPenaltyCreation:
    def test_all_fields_set(self, valid_penalty):
        assert valid_penalty.id == "pen1"
        assert valid_penalty.student_id == "s1"
        assert valid_penalty.milestone_id == "m1"
        assert valid_penalty.points == 5

    def test_default_is_resolved_false(self, valid_penalty):
        assert valid_penalty.is_resolved is False

    def test_explicit_is_resolved_true(self):
        p = Penalty("pen2", "s2", "m2", 10, is_resolved=True)
        assert p.is_resolved is True

    def test_one_point_is_valid(self):
        p = Penalty("pen3", "s3", "m3", 1)
        assert p.points == 1

    def test_large_points_valid(self):
        p = Penalty("pen4", "s4", "m4", 100)
        assert p.points == 100


class TestPenaltyIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Penalty("", "s1", "m1", 5)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Penalty("   ", "s1", "m1", 5)


class TestPenaltyStudentIdValidation:
    def test_empty_student_id_raises(self):
        with pytest.raises(ValueError, match="student_id"):
            Penalty("pen1", "", "m1", 5)

    def test_whitespace_student_id_raises(self):
        with pytest.raises(ValueError, match="student_id"):
            Penalty("pen1", "   ", "m1", 5)


class TestPenaltyMilestoneIdValidation:
    def test_empty_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            Penalty("pen1", "s1", "", 5)

    def test_whitespace_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            Penalty("pen1", "s1", "   ", 5)


class TestPenaltyPointsValidation:
    def test_zero_points_raises(self):
        with pytest.raises(ValueError, match="points"):
            Penalty("pen1", "s1", "m1", 0)

    def test_negative_points_raises(self):
        with pytest.raises(ValueError, match="points"):
            Penalty("pen1", "s1", "m1", -5)
