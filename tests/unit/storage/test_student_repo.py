import pytest
from models.student import Student
from models.enums import StudentRole
from storage.memory.student_repo import InMemoryStudentRepository


def make_student(sid: str = "s1", name: str = "Alice",
                 role: StudentRole = StudentRole.LEADER) -> Student:
    return Student(id=sid, name=name, role=role)


class TestInMemoryStudentRepositoryAdd:
    def test_add_and_get_by_id(self):
        repo = InMemoryStudentRepository()
        s = make_student()
        repo.add(s)
        assert repo.get_by_id("s1") is s

    def test_get_by_id_missing_returns_none(self):
        repo = InMemoryStudentRepository()
        assert repo.get_by_id("x") is None

    def test_add_duplicate_raises(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student())
        with pytest.raises(ValueError, match="s1"):
            repo.add(make_student())

    def test_list_all_empty(self):
        assert InMemoryStudentRepository().list_all() == []

    def test_list_all_returns_all(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student("s1", "Alice"))
        repo.add(make_student("s2", "Bob"))
        ids = {s.id for s in repo.list_all()}
        assert ids == {"s1", "s2"}


class TestInMemoryStudentRepositoryUpdate:
    def test_update_existing(self):
        repo = InMemoryStudentRepository()
        s = make_student()
        repo.add(s)
        s.is_blocked = True
        repo.update(s)
        assert repo.get_by_id("s1").is_blocked is True

    def test_update_missing_raises(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(KeyError):
            repo.update(make_student())


class TestInMemoryStudentRepositoryDelete:
    def test_delete_existing(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student())
        repo.delete("s1")
        assert repo.get_by_id("s1") is None

    def test_delete_missing_raises(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(KeyError):
            repo.delete("s999")

    def test_list_all_after_delete(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student("s1"))
        repo.add(make_student("s2", "Bob"))
        repo.delete("s1")
        assert len(repo.list_all()) == 1


class TestInMemoryStudentRepositoryFind:
    def test_find_by_name_exact(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student("s1", "Alice"))
        repo.add(make_student("s2", "Bob"))
        result = repo.find_by_name("Alice")
        assert len(result) == 1 and result[0].name == "Alice"

    def test_find_by_name_partial_case_insensitive(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student("s1", "Alice Smith"))
        repo.add(make_student("s2", "alicia"))
        result = repo.find_by_name("ali")
        assert len(result) == 2

    def test_find_by_name_no_match(self):
        repo = InMemoryStudentRepository()
        repo.add(make_student("s1", "Alice"))
        assert repo.find_by_name("xyz") == []

    def test_find_active_excludes_blocked(self):
        repo = InMemoryStudentRepository()
        repo.add(Student("s1", "Alice", StudentRole.LEADER, is_blocked=False))
        repo.add(Student("s2", "Bob", StudentRole.MEMBER, is_blocked=True))
        active = repo.find_active()
        assert len(active) == 1 and active[0].id == "s1"

    def test_find_blocked_returns_only_blocked(self):
        repo = InMemoryStudentRepository()
        repo.add(Student("s1", "Alice", StudentRole.LEADER, is_blocked=False))
        repo.add(Student("s2", "Bob", StudentRole.MEMBER, is_blocked=True))
        blocked = repo.find_blocked()
        assert len(blocked) == 1 and blocked[0].id == "s2"

    def test_find_active_empty_repo(self):
        assert InMemoryStudentRepository().find_active() == []

    def test_find_blocked_empty_repo(self):
        assert InMemoryStudentRepository().find_blocked() == []
