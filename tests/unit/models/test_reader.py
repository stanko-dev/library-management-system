import pytest
from models.reader import Reader
from models.enums import MembershipType


@pytest.fixture
def standard_reader() -> Reader:
    return Reader(id="r1", name="Alice", membership=MembershipType.STANDARD)


@pytest.fixture
def premium_reader() -> Reader:
    return Reader(id="r2", name="Bob", membership=MembershipType.PREMIUM)


class TestReaderCreation:
    def test_all_fields_set_correctly(self, standard_reader: Reader):
        assert standard_reader.id == "r1"
        assert standard_reader.name == "Alice"
        assert standard_reader.membership == MembershipType.STANDARD

    def test_premium_membership_stored(self, premium_reader: Reader):
        assert premium_reader.membership == MembershipType.PREMIUM

    def test_default_is_blocked_false(self, standard_reader: Reader):
        assert standard_reader.is_blocked is False

    def test_default_active_loans_zero(self, standard_reader: Reader):
        assert standard_reader.active_loans == 0

    def test_default_overdue_count_zero(self, standard_reader: Reader):
        assert standard_reader.overdue_count == 0

    def test_explicit_is_blocked_true(self):
        r = Reader("r3", "Carol", MembershipType.STANDARD, is_blocked=True)
        assert r.is_blocked is True

    def test_explicit_active_loans(self):
        r = Reader("r4", "Dave", MembershipType.PREMIUM, active_loans=2)
        assert r.active_loans == 2

    def test_explicit_overdue_count(self):
        r = Reader("r5", "Eve", MembershipType.STANDARD, overdue_count=1)
        assert r.overdue_count == 1

    def test_all_fields_explicit(self):
        r = Reader(
            id="r6",
            name="Frank",
            membership=MembershipType.PREMIUM,
            is_blocked=True,
            active_loans=3,
            overdue_count=2,
        )
        assert r.active_loans == 3
        assert r.overdue_count == 2
        assert r.is_blocked is True

    def test_active_loans_at_zero_boundary(self):
        r = Reader("r7", "Grace", MembershipType.STANDARD, active_loans=0)
        assert r.active_loans == 0

    def test_large_active_loans_value_valid(self):
        r = Reader("r8", "Hank", MembershipType.PREMIUM, active_loans=50)
        assert r.active_loans == 50


class TestReaderIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Reader("", "Alice", MembershipType.STANDARD)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Reader("  ", "Alice", MembershipType.STANDARD)


class TestReaderNameValidation:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Reader("r1", "", MembershipType.STANDARD)

    def test_whitespace_only_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Reader("r1", "   ", MembershipType.STANDARD)


class TestReaderCountersValidation:
    def test_negative_active_loans_raises(self):
        with pytest.raises(ValueError, match="active_loans"):
            Reader("r1", "Alice", MembershipType.STANDARD, active_loans=-1)

    def test_negative_overdue_count_raises(self):
        with pytest.raises(ValueError, match="overdue_count"):
            Reader("r1", "Alice", MembershipType.STANDARD, overdue_count=-1)

    def test_highly_negative_active_loans_raises(self):
        with pytest.raises(ValueError, match="active_loans"):
            Reader("r1", "Alice", MembershipType.STANDARD, active_loans=-100)
