import pytest
from models.student import Student
from models.enums import StudentRole


@pytest.fixture
def valid_student() -> Student:
    return Student(id="s1", name="Alice", role=StudentRole.LEADER)


class TestStudentCreation:
    def test_all_fields_set(self, valid_student):
        assert valid_student.id == "s1"
        assert valid_student.name == "Alice"
        assert valid_student.role == StudentRole.LEADER

    def test_defaults(self, valid_student):
        assert valid_student.is_blocked is False
        assert valid_student.active_projects_count == 0
        assert valid_student.missed_deadlines_count == 0

    def test_member_role(self):
        s = Student("s2", "Bob", StudentRole.MEMBER)
        assert s.role == StudentRole.MEMBER

    def test_explicit_blocked_true(self):
        s = Student("s3", "Carol", StudentRole.MEMBER, is_blocked=True)
        assert s.is_blocked is True

    def test_explicit_active_projects(self):
        s = Student("s4", "Dave", StudentRole.LEADER, active_projects_count=3)
        assert s.active_projects_count == 3

    def test_explicit_missed_deadlines(self):
        s = Student("s5", "Eve", StudentRole.MEMBER, missed_deadlines_count=2)
        assert s.missed_deadlines_count == 2

    def test_all_fields_explicit(self):
        s = Student("s6", "Frank", StudentRole.LEADER, True, 5, 1)
        assert s.active_projects_count == 5
        assert s.missed_deadlines_count == 1
        assert s.is_blocked is True


class TestStudentIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Student("", "Alice", StudentRole.LEADER)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Student("   ", "Alice", StudentRole.LEADER)


class TestStudentNameValidation:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Student("s1", "", StudentRole.LEADER)

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Student("s1", "   ", StudentRole.LEADER)


class TestStudentCountersValidation:
    def test_negative_active_projects_raises(self):
        with pytest.raises(ValueError, match="active_projects_count"):
            Student("s1", "Alice", StudentRole.LEADER, active_projects_count=-1)

    def test_zero_active_projects_is_valid(self):
        s = Student("s1", "Alice", StudentRole.LEADER, active_projects_count=0)
        assert s.active_projects_count == 0

    def test_negative_missed_deadlines_raises(self):
        with pytest.raises(ValueError, match="missed_deadlines_count"):
            Student("s1", "Alice", StudentRole.LEADER, missed_deadlines_count=-1)

    def test_zero_missed_deadlines_is_valid(self):
        s = Student("s1", "Alice", StudentRole.LEADER, missed_deadlines_count=0)
        assert s.missed_deadlines_count == 0

    def test_large_counts_valid(self):
        s = Student("s1", "Alice", StudentRole.MEMBER,
                    active_projects_count=100, missed_deadlines_count=50)
        assert s.active_projects_count == 100
