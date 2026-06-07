import pytest
from models.reader import Reader
from models.enums import MembershipType
from storage.memory.reader_repo import InMemoryReaderRepository


def _reader(
    id_: str = "r1",
    name: str = "Alice",
    membership: MembershipType = MembershipType.STANDARD,
    is_blocked: bool = False,
) -> Reader:
    return Reader(id=id_, name=name, membership=membership, is_blocked=is_blocked)


@pytest.fixture
def repo() -> InMemoryReaderRepository:
    return InMemoryReaderRepository()


@pytest.fixture
def reader() -> Reader:
    return _reader()


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_stores_reader(self, repo, reader):
        repo.add(reader)
        assert repo.get_by_id("r1") is reader

    def test_add_duplicate_id_raises(self, repo, reader):
        repo.add(reader)
        with pytest.raises(ValueError, match="r1"):
            repo.add(reader)

    def test_add_two_distinct_readers(self, repo):
        repo.add(_reader("r1"))
        repo.add(_reader("r2", name="Bob"))
        assert len(repo.list_all()) == 2


class TestGetById:
    def test_existing_id_returns_reader(self, repo, reader):
        repo.add(reader)
        assert repo.get_by_id("r1") is reader

    def test_missing_id_returns_none(self, repo):
        assert repo.get_by_id("ghost") is None


class TestListAll:
    def test_empty_repo_returns_empty_list(self, repo):
        assert repo.list_all() == []

    def test_returns_all_added_readers(self, repo):
        repo.add(_reader("r1"))
        repo.add(_reader("r2", name="Bob"))
        assert len(repo.list_all()) == 2

    def test_returns_defensive_copy(self, repo, reader):
        repo.add(reader)
        repo.list_all().clear()
        assert len(repo.list_all()) == 1


class TestUpdate:
    def test_update_modifies_stored_reader(self, repo, reader):
        repo.add(reader)
        reader.is_blocked = True
        repo.update(reader)
        assert repo.get_by_id("r1").is_blocked is True

    def test_update_increments_active_loans(self, repo, reader):
        repo.add(reader)
        reader.active_loans = 3
        repo.update(reader)
        assert repo.get_by_id("r1").active_loans == 3

    def test_update_nonexistent_raises(self, repo, reader):
        with pytest.raises(KeyError):
            repo.update(reader)


class TestDelete:
    def test_delete_removes_reader(self, repo, reader):
        repo.add(reader)
        repo.delete("r1")
        assert repo.get_by_id("r1") is None

    def test_delete_reduces_list_size(self, repo):
        repo.add(_reader("r1"))
        repo.add(_reader("r2", name="Bob"))
        repo.delete("r1")
        assert len(repo.list_all()) == 1

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError):
            repo.delete("ghost")


# ── Query methods ─────────────────────────────────────────────────────────────

class TestFindByName:
    def test_case_insensitive_match(self, repo, reader):
        repo.add(reader)
        assert len(repo.find_by_name("ALICE")) == 1

    def test_partial_substring_match(self, repo):
        repo.add(_reader("r1", name="Alice Wonderland"))
        assert len(repo.find_by_name("alice")) == 1

    def test_no_match_returns_empty(self, repo, reader):
        repo.add(reader)
        assert repo.find_by_name("charlie") == []

    def test_matches_multiple_readers(self, repo):
        repo.add(_reader("r1", name="Alice"))
        repo.add(_reader("r2", name="Alice Smith"))
        assert len(repo.find_by_name("alice")) == 2


class TestFindActive:
    def test_unblocked_reader_is_active(self, repo, reader):
        repo.add(reader)
        assert len(repo.find_active()) == 1

    def test_blocked_reader_excluded(self, repo):
        repo.add(_reader("r1", is_blocked=True))
        assert repo.find_active() == []

    def test_mixed_returns_only_unblocked(self, repo):
        repo.add(_reader("r1", is_blocked=False))
        repo.add(_reader("r2", name="Bob", is_blocked=True))
        result = repo.find_active()
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_empty_repo_returns_empty(self, repo):
        assert repo.find_active() == []


class TestFindBlocked:
    def test_blocked_reader_is_returned(self, repo):
        repo.add(_reader("r1", is_blocked=True))
        assert len(repo.find_blocked()) == 1

    def test_unblocked_reader_excluded(self, repo, reader):
        repo.add(reader)
        assert repo.find_blocked() == []

    def test_mixed_returns_only_blocked(self, repo):
        repo.add(_reader("r1", is_blocked=True))
        repo.add(_reader("r2", name="Bob", is_blocked=False))
        result = repo.find_blocked()
        assert len(result) == 1
        assert result[0].id == "r1"
