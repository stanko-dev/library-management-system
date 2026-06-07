import pytest
from models.book import Book
from models.enums import BookStatus
from storage.memory.book_repo import InMemoryBookRepository


def _book(id_: str = "b1", isbn: str = "9780132350884", available: int = 2) -> Book:
    return Book(id=id_, title="Clean Code", author="Robert Martin",
                isbn=isbn, total_copies=3, available_copies=available)


@pytest.fixture
def repo() -> InMemoryBookRepository:
    return InMemoryBookRepository()


@pytest.fixture
def book() -> Book:
    return _book()


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_stores_book(self, repo, book):
        repo.add(book)
        assert repo.get_by_id("b1") is book

    def test_add_duplicate_id_raises(self, repo, book):
        repo.add(book)
        with pytest.raises(ValueError, match="b1"):
            repo.add(book)

    def test_add_two_distinct_books(self, repo):
        repo.add(_book("b1", "9780132350884"))
        repo.add(_book("b2", "047096890X"))
        assert len(repo.list_all()) == 2


class TestGetById:
    def test_existing_id_returns_book(self, repo, book):
        repo.add(book)
        assert repo.get_by_id("b1") is book

    def test_missing_id_returns_none(self, repo):
        assert repo.get_by_id("ghost") is None


class TestGetByIsbn:
    def test_existing_isbn_returns_book(self, repo, book):
        repo.add(book)
        assert repo.get_by_isbn("9780132350884") is book

    def test_missing_isbn_returns_none(self, repo):
        assert repo.get_by_isbn("0000000000000") is None

    def test_isbn_match_is_exact(self, repo):
        repo.add(_book("b1", "9780132350884"))
        assert repo.get_by_isbn("047096890X") is None


class TestListAll:
    def test_empty_repo_returns_empty_list(self, repo):
        assert repo.list_all() == []

    def test_returns_all_added_books(self, repo):
        repo.add(_book("b1", "9780132350884"))
        repo.add(_book("b2", "047096890X"))
        result = repo.list_all()
        assert len(result) == 2

    def test_returns_defensive_copy(self, repo, book):
        repo.add(book)
        repo.list_all().clear()
        assert len(repo.list_all()) == 1


class TestUpdate:
    def test_update_replaces_entry(self, repo, book):
        repo.add(book)
        book.available_copies = 0
        repo.update(book)
        assert repo.get_by_id("b1").available_copies == 0

    def test_update_nonexistent_raises(self, repo, book):
        with pytest.raises(KeyError):
            repo.update(book)

    def test_update_status(self, repo, book):
        repo.add(book)
        book.status = BookStatus.MAINTENANCE
        repo.update(book)
        assert repo.get_by_id("b1").status == BookStatus.MAINTENANCE


class TestDelete:
    def test_delete_removes_book(self, repo, book):
        repo.add(book)
        repo.delete("b1")
        assert repo.get_by_id("b1") is None

    def test_delete_reduces_list_size(self, repo):
        repo.add(_book("b1", "9780132350884"))
        repo.add(_book("b2", "047096890X"))
        repo.delete("b1")
        assert len(repo.list_all()) == 1

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError):
            repo.delete("ghost")


# ── Query methods ─────────────────────────────────────────────────────────────

class TestFindByTitle:
    def test_case_insensitive_full_match(self, repo, book):
        repo.add(book)
        assert len(repo.find_by_title("CLEAN CODE")) == 1

    def test_partial_substring_match(self, repo, book):
        repo.add(book)
        assert len(repo.find_by_title("clean")) == 1

    def test_no_match_returns_empty(self, repo, book):
        repo.add(book)
        assert repo.find_by_title("python") == []

    def test_matches_multiple_books(self, repo):
        repo.add(Book("b1", "Clean Code", "Martin", "9780132350884", 1, 1))
        repo.add(Book("b2", "Clean Architecture", "Martin", "047096890X", 1, 1))
        assert len(repo.find_by_title("clean")) == 2

    def test_empty_query_matches_all(self, repo):
        repo.add(_book("b1", "9780132350884"))
        repo.add(_book("b2", "047096890X"))
        assert len(repo.find_by_title("")) == 2


class TestFindByAuthor:
    def test_case_insensitive_full_match(self, repo, book):
        repo.add(book)
        assert len(repo.find_by_author("robert martin")) == 1

    def test_partial_match(self, repo, book):
        repo.add(book)
        assert len(repo.find_by_author("martin")) == 1

    def test_no_match_returns_empty(self, repo, book):
        repo.add(book)
        assert repo.find_by_author("fowler") == []

    def test_matches_multiple_books_by_same_author(self, repo):
        repo.add(Book("b1", "Clean Code", "Robert Martin", "9780132350884", 1, 1))
        repo.add(Book("b2", "Clean Architecture", "Robert Martin", "047096890X", 1, 1))
        assert len(repo.find_by_author("martin")) == 2


class TestFindAvailable:
    def test_book_with_copies_is_returned(self, repo):
        repo.add(_book("b1", available=1))
        assert len(repo.find_available()) == 1

    def test_book_with_zero_copies_excluded(self, repo):
        repo.add(_book("b1", available=0))
        assert repo.find_available() == []

    def test_mixed_returns_only_available(self, repo):
        repo.add(_book("b1", isbn="9780132350884", available=2))
        repo.add(_book("b2", isbn="047096890X", available=0))
        result = repo.find_available()
        assert len(result) == 1
        assert result[0].id == "b1"

    def test_empty_repo_returns_empty(self, repo):
        assert repo.find_available() == []
