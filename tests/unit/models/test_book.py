import pytest
from models.book import Book
from models.enums import BookStatus


@pytest.fixture
def valid_book() -> Book:
    return Book(
        id="b1",
        title="Clean Code",
        author="Robert Martin",
        isbn="9780132350884",
        total_copies=3,
        available_copies=2,
    )


class TestBookCreation:
    def test_all_fields_set_correctly(self, valid_book: Book):
        assert valid_book.id == "b1"
        assert valid_book.title == "Clean Code"
        assert valid_book.author == "Robert Martin"
        assert valid_book.isbn == "9780132350884"
        assert valid_book.total_copies == 3
        assert valid_book.available_copies == 2

    def test_default_status_is_available(self, valid_book: Book):
        assert valid_book.status == BookStatus.AVAILABLE

    def test_explicit_status_unavailable(self):
        book = Book("b2", "Title", "Author", "9780132350884", 1, 0, BookStatus.UNAVAILABLE)
        assert book.status == BookStatus.UNAVAILABLE

    def test_explicit_status_reserved(self):
        book = Book("b3", "Title", "Author", "9780132350884", 2, 1, BookStatus.RESERVED)
        assert book.status == BookStatus.RESERVED

    def test_explicit_status_lost(self):
        book = Book("b4", "Title", "Author", "9780132350884", 1, 0, BookStatus.LOST)
        assert book.status == BookStatus.LOST

    def test_explicit_status_maintenance(self):
        book = Book("b5", "Title", "Author", "9780132350884", 1, 0, BookStatus.MAINTENANCE)
        assert book.status == BookStatus.MAINTENANCE

    def test_available_equals_total_is_valid(self):
        book = Book("b6", "Title", "Author", "9780132350884", 5, 5)
        assert book.available_copies == 5

    def test_available_copies_zero_is_valid(self):
        book = Book("b7", "Title", "Author", "9780132350884", 5, 0)
        assert book.available_copies == 0

    def test_single_copy_book_is_valid(self):
        book = Book("b8", "Title", "Author", "9780132350884", 1, 1)
        assert book.total_copies == 1

    def test_isbn_13_no_hyphens(self):
        book = Book("b9", "Title", "Author", "9780132350884", 1, 1)
        assert book.isbn == "9780132350884"

    def test_isbn_13_with_hyphens(self):
        book = Book("b10", "Title", "Author", "978-0-13-235088-4", 1, 1)
        assert book.isbn == "978-0-13-235088-4"

    def test_isbn_10_digits_only(self):
        book = Book("b11", "Title", "Author", "0132350882", 1, 1)
        assert book.isbn == "0132350882"

    def test_isbn_10_with_x_checksum(self):
        book = Book("b12", "Title", "Author", "047096890X", 1, 1)
        assert book.isbn == "047096890X"

    def test_isbn_10_with_hyphens(self):
        book = Book("b13", "Title", "Author", "0-13-235088-2", 1, 1)
        assert book.isbn == "0-13-235088-2"

    def test_large_copy_count_is_valid(self):
        book = Book("b14", "Title", "Author", "9780132350884", 1000, 500)
        assert book.total_copies == 1000


class TestBookIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Book("", "Title", "Author", "9780132350884", 1, 1)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Book("   ", "Title", "Author", "9780132350884", 1, 1)


class TestBookTitleValidation:
    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Book("b1", "", "Author", "9780132350884", 1, 1)

    def test_whitespace_only_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Book("b1", "   ", "Author", "9780132350884", 1, 1)


class TestBookAuthorValidation:
    def test_empty_author_raises(self):
        with pytest.raises(ValueError, match="author"):
            Book("b1", "Title", "", "9780132350884", 1, 1)

    def test_whitespace_only_author_raises(self):
        with pytest.raises(ValueError, match="author"):
            Book("b1", "Title", "   ", "9780132350884", 1, 1)


class TestBookIsbnValidation:
    def test_empty_isbn_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "", 1, 1)

    def test_whitespace_only_isbn_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "   ", 1, 1)

    def test_isbn_too_short_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "12345", 1, 1)

    def test_isbn_11_digits_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "12345678901", 1, 1)

    def test_isbn_with_letters_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "978013235088Z", 1, 1)

    def test_isbn_with_lowercase_raises(self):
        with pytest.raises(ValueError, match="isbn"):
            Book("b1", "Title", "Author", "978013235088x", 1, 1)


class TestBookCopiesValidation:
    def test_total_copies_zero_raises(self):
        with pytest.raises(ValueError, match="total_copies"):
            Book("b1", "Title", "Author", "9780132350884", 0, 0)

    def test_total_copies_negative_raises(self):
        with pytest.raises(ValueError, match="total_copies"):
            Book("b1", "Title", "Author", "9780132350884", -1, 0)

    def test_available_copies_negative_raises(self):
        with pytest.raises(ValueError, match="available_copies"):
            Book("b1", "Title", "Author", "9780132350884", 3, -1)

    def test_available_copies_exceeds_total_raises(self):
        with pytest.raises(ValueError, match="available_copies"):
            Book("b1", "Title", "Author", "9780132350884", 3, 4)

    def test_available_exceeds_total_by_one_raises(self):
        with pytest.raises(ValueError, match="available_copies"):
            Book("b1", "Title", "Author", "9780132350884", 1, 2)
