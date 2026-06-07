"""Parametrized CRUD and query edge cases for all five in-memory repositories.

Uses real InMemory implementations (no mocks) because these tests exercise the
storage layer directly.  Edge cases covered:

  - empty repository for every query method
  - 0 / 1 / many item counts
  - full vs zero available copies
  - active vs returned loans, overdue vs on-time, boundary as_of timestamps
  - all four reservation statuses in find_active / find_active_by_book
  - unpaid-fine totals (0, partial, full, multiple readers)
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from models.book import Book
from models.fine import Fine
from models.loan import Loan
from models.reader import Reader
from models.reservation import Reservation
from models.enums import MembershipType, ReservationStatus
from storage.memory.book_repo import InMemoryBookRepository
from storage.memory.reader_repo import InMemoryReaderRepository
from storage.memory.loan_repo import InMemoryLoanRepository
from storage.memory.reservation_repo import InMemoryReservationRepository
from storage.memory.fine_repo import InMemoryFineRepository

# ── Shared constants ──────────────────────────────────────────────────────────

_ISSUED  = datetime(2025, 1, 1, 12, 0, 0)
_DUE     = _ISSUED + timedelta(days=14)
_CREATED = datetime(2025, 6, 1, 10, 0, 0)

# Pool of valid ISBNs for multi-book tests (10 or 13 stripped digits only)
_ISBNS = [
    "9780132350884", "047096890X", "0132350882", "9780201633610",
    "9780596007126", "9780471958697", "9781492056355", "9780134685991",
    "9780735619678", "9780201485677",
]

# ── Factories ─────────────────────────────────────────────────────────────────

def _book(idx: int = 0, available: int = 2) -> Book:
    return Book(f"b{idx}", f"Title {idx}", f"Author {idx}", _ISBNS[idx], 5, available)


def _reader(idx: int = 0, membership: MembershipType = MembershipType.STANDARD,
            blocked: bool = False) -> Reader:
    return Reader(f"r{idx}", f"Name {idx}", membership, is_blocked=blocked)


def _loan(idx: int = 0, book_id: str = "b0", reader_id: str = "r0",
          returned_at: datetime | None = None) -> Loan:
    return Loan(f"l{idx}", book_id, reader_id, _ISSUED, _DUE, returned_at=returned_at)


def _reservation(
    idx: int = 0,
    book_id: str = "b0",
    reader_id: str = "r0",
    status: ReservationStatus = ReservationStatus.ACTIVE,
    created_offset_days: int = 0,
) -> Reservation:
    created = _CREATED + timedelta(days=created_offset_days)
    return Reservation(
        f"res{idx}", book_id, reader_id, created,
        created + timedelta(days=3), status=status,
    )


def _fine(idx: int = 0, reader_id: str = "r0", loan_id: str = "l0",
          amount: Decimal = Decimal("5.00"), paid: bool = False) -> Fine:
    return Fine(f"f{idx}", reader_id, loan_id, amount, is_paid=paid)


# ═════════════════════════════════════════════════════════════════════════════
#  BookRepository
# ═════════════════════════════════════════════════════════════════════════════

class TestBookRepoEmpty:
    def test_list_all_empty(self):
        assert InMemoryBookRepository().list_all() == []

    def test_get_by_id_empty(self):
        assert InMemoryBookRepository().get_by_id("b0") is None

    def test_get_by_isbn_empty(self):
        assert InMemoryBookRepository().get_by_isbn("9780132350884") is None

    def test_find_by_title_empty(self):
        assert InMemoryBookRepository().find_by_title("python") == []

    def test_find_by_author_empty(self):
        assert InMemoryBookRepository().find_by_author("martin") == []

    def test_find_available_empty(self):
        assert InMemoryBookRepository().find_available() == []


class TestBookRepoSizes:
    @pytest.mark.parametrize("n", [1, 3, 5, 10])
    def test_list_all_n_books(self, n):
        repo = InMemoryBookRepository()
        for i in range(n):
            repo.add(_book(i))
        assert len(repo.list_all()) == n


class TestBookAvailableCopiesBoundaries:
    @pytest.mark.parametrize("available_counts,expected_available", [
        ([0],          0),
        ([1],          1),
        ([0, 1],       1),
        ([0, 0, 0],    0),
        ([1, 1, 1],    3),
        ([0, 2, 0, 3], 2),   # 2 books with available>0 out of 4
    ])
    def test_find_available_counts(self, available_counts, expected_available):
        repo = InMemoryBookRepository()
        for i, avail in enumerate(available_counts):
            repo.add(_book(i, available=avail))
        assert len(repo.find_available()) == expected_available


class TestBookTitleSearch:
    @pytest.mark.parametrize("query,expected_count", [
        ("python", 1),
        ("PYTHON", 1),     # case-insensitive
        ("Java",   1),
        ("code",   2),     # substring matches two titles
        ("rust",   0),     # no match
        ("",       3),     # empty string matches all
    ])
    def test_find_by_title(self, query, expected_count):
        repo = InMemoryBookRepository()
        repo.add(Book("b0", "Python Code",     "Author", _ISBNS[0], 1, 1))
        repo.add(Book("b1", "Java Code",       "Author", _ISBNS[1], 1, 1))
        repo.add(Book("b2", "Algorithms",      "Author", _ISBNS[2], 1, 1))
        assert len(repo.find_by_title(query)) == expected_count


class TestBookAuthorSearch:
    @pytest.mark.parametrize("query,expected_count", [
        ("martin",  3),   # "Robert Martin" ×2 and "Martin Fowler" all contain "martin"
        ("MARTIN",  3),   # case-insensitive — same result
        ("fowler",  1),   # only "Martin Fowler"
        ("robert",  2),   # only the two "Robert Martin" entries
        ("gamma",   0),   # no match
        ("",        3),   # empty string matches all
    ])
    def test_find_by_author(self, query, expected_count):
        repo = InMemoryBookRepository()
        repo.add(Book("b0", "Clean Code",         "Robert Martin",  _ISBNS[0], 1, 1))
        repo.add(Book("b1", "Clean Architecture", "Robert Martin",  _ISBNS[1], 1, 1))
        repo.add(Book("b2", "Refactoring",        "Martin Fowler",  _ISBNS[2], 1, 1))
        assert len(repo.find_by_author(query)) == expected_count


# ═════════════════════════════════════════════════════════════════════════════
#  ReaderRepository
# ═════════════════════════════════════════════════════════════════════════════

class TestReaderRepoEmpty:
    def test_list_all_empty(self):
        assert InMemoryReaderRepository().list_all() == []

    def test_get_by_id_empty(self):
        assert InMemoryReaderRepository().get_by_id("r0") is None

    def test_find_active_empty(self):
        assert InMemoryReaderRepository().find_active() == []

    def test_find_blocked_empty(self):
        assert InMemoryReaderRepository().find_blocked() == []

    def test_find_by_name_empty(self):
        assert InMemoryReaderRepository().find_by_name("alice") == []


class TestReaderActiveBlockedMix:
    @pytest.mark.parametrize("blocked_flags,expected_active,expected_blocked", [
        ([False],             1, 0),
        ([True],              0, 1),
        ([False, True],       1, 1),
        ([False, False, True, True], 2, 2),
        ([True, True, True],  0, 3),
    ])
    def test_active_blocked_split(
        self, blocked_flags, expected_active, expected_blocked
    ):
        repo = InMemoryReaderRepository()
        for i, blocked in enumerate(blocked_flags):
            repo.add(_reader(i, blocked=blocked))
        assert len(repo.find_active())  == expected_active
        assert len(repo.find_blocked()) == expected_blocked


class TestReaderNameSearch:
    @pytest.mark.parametrize("query,expected_count", [
        ("alice",   2),   # "Alice" and "Alice Smith"
        ("ALICE",   2),   # case-insensitive
        ("smith",   1),   # only "Alice Smith"
        ("bob",     1),
        ("charlie", 0),
        ("",        3),   # matches all
    ])
    def test_find_by_name(self, query, expected_count):
        repo = InMemoryReaderRepository()
        repo.add(Reader("r0", "Alice",       MembershipType.STANDARD))
        repo.add(Reader("r1", "Alice Smith", MembershipType.PREMIUM))
        repo.add(Reader("r2", "Bob Jones",   MembershipType.STANDARD))
        assert len(repo.find_by_name(query)) == expected_count


# ═════════════════════════════════════════════════════════════════════════════
#  LoanRepository
# ═════════════════════════════════════════════════════════════════════════════

class TestLoanRepoEmpty:
    def test_list_all_empty(self):
        assert InMemoryLoanRepository().list_all() == []

    def test_get_by_id_empty(self):
        assert InMemoryLoanRepository().get_by_id("l0") is None

    def test_find_active_empty(self):
        assert InMemoryLoanRepository().find_active() == []

    def test_find_by_reader_empty(self):
        assert InMemoryLoanRepository().find_by_reader("r0") == []

    def test_find_overdue_empty(self):
        assert InMemoryLoanRepository().find_overdue(_DUE + timedelta(days=1)) == []


class TestLoanActiveReturnedMix:
    @pytest.mark.parametrize("returned_flags,expected_active", [
        ([None],                        1),
        ([_DUE],                        0),
        ([None, _DUE],                  1),
        ([None, None, _DUE],            2),
        ([_DUE, _DUE, _DUE],           0),
    ])
    def test_find_active_count(self, returned_flags, expected_active):
        repo = InMemoryLoanRepository()
        for i, ret in enumerate(returned_flags):
            repo.add(_loan(i, returned_at=ret))
        assert len(repo.find_active()) == expected_active


class TestLoanOverdueBoundaries:
    @pytest.mark.parametrize("as_of_offset_days,expected_overdue", [
        (-1,  0),   # 1 day before due → not overdue
        (0,   0),   # exactly at due date → not overdue
        (1,   1),   # 1 day past due → overdue
        (7,   1),
        (30,  1),
    ])
    def test_single_loan_overdue_at_boundary(
        self, as_of_offset_days, expected_overdue
    ):
        repo = InMemoryLoanRepository()
        repo.add(_loan(0))   # open loan with _DUE due date
        as_of = _DUE + timedelta(days=as_of_offset_days)
        assert len(repo.find_overdue(as_of)) == expected_overdue

    def test_returned_loan_never_overdue(self):
        repo = InMemoryLoanRepository()
        repo.add(_loan(0, returned_at=_ISSUED + timedelta(days=1)))
        assert repo.find_overdue(_DUE + timedelta(days=100)) == []

    @pytest.mark.parametrize("n_overdue", [0, 1, 3, 5])
    def test_multiple_overdue_loans(self, n_overdue):
        repo = InMemoryLoanRepository()
        for i in range(n_overdue):
            repo.add(_loan(i, returned_at=None))      # all open → all overdue
        for j in range(3):                             # some returned ones
            repo.add(_loan(n_overdue + j,
                           returned_at=_ISSUED + timedelta(days=1)))
        as_of = _DUE + timedelta(days=1)
        assert len(repo.find_overdue(as_of)) == n_overdue


# ═════════════════════════════════════════════════════════════════════════════
#  ReservationRepository
# ═════════════════════════════════════════════════════════════════════════════

class TestReservationRepoEmpty:
    def test_list_all_empty(self):
        assert InMemoryReservationRepository().list_all() == []

    def test_find_active_empty(self):
        assert InMemoryReservationRepository().find_active() == []

    def test_find_active_by_book_empty(self):
        assert InMemoryReservationRepository().find_active_by_book("b0") == []

    def test_find_by_reader_empty(self):
        assert InMemoryReservationRepository().find_by_reader("r0") == []


class TestReservationStatusFiltering:
    @pytest.mark.parametrize("status,expected_in_active", [
        (ReservationStatus.ACTIVE,    True),
        (ReservationStatus.CANCELLED, False),
        (ReservationStatus.FULFILLED, False),
        (ReservationStatus.EXPIRED,   False),
    ])
    def test_find_active_filters_by_status(self, status, expected_in_active):
        repo = InMemoryReservationRepository()
        res = _reservation(status=status)
        repo.add(res)
        active = repo.find_active()
        if expected_in_active:
            assert res in active
        else:
            assert res not in active

    @pytest.mark.parametrize("status,expected_in_active_by_book", [
        (ReservationStatus.ACTIVE,    True),
        (ReservationStatus.CANCELLED, False),
        (ReservationStatus.FULFILLED, False),
        (ReservationStatus.EXPIRED,   False),
    ])
    def test_find_active_by_book_filters_status(
        self, status, expected_in_active_by_book
    ):
        repo = InMemoryReservationRepository()
        res = _reservation(status=status)
        repo.add(res)
        result = repo.find_active_by_book("b0")
        if expected_in_active_by_book:
            assert res in result
        else:
            assert result == []


class TestReservationQueueOrdering:
    @pytest.mark.parametrize("n_active", [0, 1, 3, 5])
    def test_find_active_by_book_count(self, n_active):
        repo = InMemoryReservationRepository()
        for i in range(n_active):
            repo.add(_reservation(i, reader_id=f"r{i}"))
        assert len(repo.find_active_by_book("b0")) == n_active


# ═════════════════════════════════════════════════════════════════════════════
#  FineRepository
# ═════════════════════════════════════════════════════════════════════════════

class TestFineRepoEmpty:
    def test_list_all_empty(self):
        assert InMemoryFineRepository().list_all() == []

    def test_find_unpaid_empty(self):
        assert InMemoryFineRepository().find_unpaid() == []

    def test_find_by_reader_empty(self):
        assert InMemoryFineRepository().find_by_reader("r0") == []

    def test_total_unpaid_empty_returns_zero(self):
        assert InMemoryFineRepository().total_unpaid_by_reader("r0") == Decimal("0")


class TestFineTotalUnpaidBoundaries:
    @pytest.mark.parametrize("amounts,paid_flags,expected_total", [
        # amounts, is_paid per fine, expected sum of unpaid
        ([Decimal("5")],             [False], Decimal("5")),
        ([Decimal("5")],             [True],  Decimal("0")),
        ([Decimal("3"), Decimal("2")], [False, False], Decimal("5")),
        ([Decimal("3"), Decimal("2")], [True,  False], Decimal("2")),
        ([Decimal("3"), Decimal("2")], [True,  True],  Decimal("0")),
        ([Decimal("0.01")],           [False], Decimal("0.01")),
        ([Decimal("999.99")],         [False], Decimal("999.99")),
    ])
    def test_total_unpaid(self, amounts, paid_flags, expected_total):
        repo = InMemoryFineRepository()
        for i, (amt, paid) in enumerate(zip(amounts, paid_flags)):
            repo.add(_fine(i, loan_id=f"l{i}", amount=amt, paid=paid))
        assert repo.total_unpaid_by_reader("r0") == expected_total


class TestFineUnpaidFiltering:
    @pytest.mark.parametrize("n_paid,n_unpaid", [
        (0, 0), (0, 1), (0, 3), (2, 0), (2, 3),
    ])
    def test_find_unpaid_counts(self, n_paid, n_unpaid):
        repo = InMemoryFineRepository()
        for i in range(n_paid):
            repo.add(_fine(i, loan_id=f"l{i}", paid=True))
        for j in range(n_unpaid):
            repo.add(_fine(n_paid + j, loan_id=f"l{n_paid + j}", paid=False))
        assert len(repo.find_unpaid()) == n_unpaid


class TestFineTotalIsolatedByReader:
    @pytest.mark.parametrize("r1_unpaid,r2_unpaid", [
        (Decimal("5"),  Decimal("10")),
        (Decimal("0"),  Decimal("10")),
        (Decimal("5"),  Decimal("0")),
    ])
    def test_total_unpaid_isolated(self, r1_unpaid, r2_unpaid):
        repo = InMemoryFineRepository()
        if r1_unpaid > 0:
            repo.add(Fine("f0", "r0", "l0", r1_unpaid))
        if r2_unpaid > 0:
            repo.add(Fine("f1", "r1", "l1", r2_unpaid))
        assert repo.total_unpaid_by_reader("r0") == r1_unpaid
        assert repo.total_unpaid_by_reader("r1") == r2_unpaid
