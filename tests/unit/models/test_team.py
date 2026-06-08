import pytest
from models.team import Team


@pytest.fixture
def empty_team() -> Team:
    return Team(id="t1", name="Alpha", capacity=4)


@pytest.fixture
def team_with_members() -> Team:
    return Team(id="t2", name="Beta", capacity=3, member_ids=["s1", "s2"])


class TestTeamCreation:
    def test_all_fields_set(self, empty_team):
        assert empty_team.id == "t1"
        assert empty_team.name == "Alpha"
        assert empty_team.capacity == 4

    def test_default_member_ids_empty(self, empty_team):
        assert empty_team.member_ids == []

    def test_explicit_member_ids(self, team_with_members):
        assert team_with_members.member_ids == ["s1", "s2"]

    def test_capacity_one_is_valid(self):
        t = Team("t3", "Solo", 1)
        assert t.capacity == 1

    def test_team_at_capacity_valid(self):
        t = Team("t4", "Full", 2, member_ids=["s1", "s2"])
        assert len(t.member_ids) == 2


class TestTeamProperties:
    def test_is_full_false_when_space_available(self, team_with_members):
        assert team_with_members.is_full is False

    def test_is_full_true_when_at_capacity(self):
        t = Team("t5", "Full", 2, member_ids=["s1", "s2"])
        assert t.is_full is True

    def test_is_full_false_when_empty(self, empty_team):
        assert empty_team.is_full is False

    def test_available_spots_full_team(self, empty_team):
        assert empty_team.available_spots == 4

    def test_available_spots_partial(self, team_with_members):
        assert team_with_members.available_spots == 1

    def test_available_spots_zero_when_full(self):
        t = Team("t6", "Full", 2, member_ids=["s1", "s2"])
        assert t.available_spots == 0


class TestTeamIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Team("", "Alpha", 3)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Team("   ", "Alpha", 3)


class TestTeamNameValidation:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Team("t1", "", 3)

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Team("t1", "   ", 3)


class TestTeamCapacityValidation:
    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            Team("t1", "Alpha", 0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            Team("t1", "Alpha", -1)

    def test_members_exceed_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            Team("t1", "Alpha", 2, member_ids=["s1", "s2", "s3"])

    def test_members_equal_capacity_is_valid(self):
        t = Team("t1", "Alpha", 2, member_ids=["s1", "s2"])
        assert len(t.member_ids) == 2
