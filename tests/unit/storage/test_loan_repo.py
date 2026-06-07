import pytest
from datetime import datetime, timedelta
from models.loan import Loan
from storage.memory.loan_repo import InMemoryLoanRepository


_ISSUED = datetime(2025, 1, 1, 12, 0, 0)
_DUE = _ISSUED + timedelta(days=14)


def _loan(
    id_: str = "l1",
    book_id: str = "b1",
    reader_id: str = "r1",
    returned_at: datetime | None = None,
) -> Loan:
    return Loan(id=id_, book_id=book_id, reader_id=reader_id,
                issued_at=_ISSUED, due_date=_DUE, returned_at=returned_at)


@pytest.fixture
def repo() -> InMemoryLoanRepository:
    return InMemoryLoanRepository()


@pytest.fixture
def loan() -> Loan:
    return _loan()


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_stores_loan(self, repo, loan):
        repo.add(loan)
        assert repo.get_by_id("l1") is loan

    def test_add_duplicate_id_raises(self, repo, loan):
        repo.add(loan)
        with pytest.raises(ValueError, match="l1"):
            repo.add(loan)

    def test_add_two_distinct_loans(self, repo):
        repo.add(_loan("l1"))
        repo.add(_loan("l2"))
        assert len(repo.list_all()) == 2


class TestGetById:
    def test_existing_id_returns_loan(self, repo, loan):
        repo.add(loan)
        assert repo.get_by_id("l1") is loan

    def test_missing_id_returns_none(self, repo):
        assert repo.get_by_id("ghost") is None


class TestListAll:
    def test_empty_repo_returns_empty_list(self, repo):
        assert repo.list_all() == []

    def test_returns_all_loans(self, repo):
        repo.add(_loan("l1"))
        repo.add(_loan("l2"))
        assert len(repo.list_all()) == 2

    def test_returns_defensive_copy(self, repo, loan):
        repo.add(loan)
        repo.list_all().clear()
        assert len(repo.list_all()) == 1


class TestUpdate:
    def test_update_sets_returned_at(self, repo, loan):
        repo.add(loan)
        loan.returned_at = _ISSUED + timedelta(days=5)
        repo.update(loan)
        assert repo.get_by_id("l1").returned_at is not None

    def test_update_nonexistent_raises(self, repo, loan):
        with pytest.raises(KeyError):
            repo.update(loan)


class TestDelete:
    def test_delete_removes_loan(self, repo, loan):
        repo.add(loan)
        repo.delete("l1")
        assert repo.get_by_id("l1") is None

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError):
            repo.delete("ghost")


# ── Query methods ─────────────────────────────────────────────────────────────

class TestFindByReader:
    def test_returns_loans_for_reader(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r2"))
        result = repo.find_by_reader("r1")
        assert len(result) == 1
        assert result[0].id == "l1"

    def test_no_match_returns_empty(self, repo, loan):
        repo.add(loan)
        assert repo.find_by_reader("r99") == []

    def test_returns_all_loans_for_reader(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r1"))
        assert len(repo.find_by_reader("r1")) == 2

    def test_does_not_include_other_readers(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r2"))
        assert all(l.reader_id == "r1" for l in repo.find_by_reader("r1"))


class TestFindByBook:
    def test_returns_loans_for_book(self, repo):
        repo.add(_loan("l1", book_id="b1"))
        repo.add(_loan("l2", book_id="b2"))
        assert len(repo.find_by_book("b1")) == 1

    def test_no_match_returns_empty(self, repo, loan):
        repo.add(loan)
        assert repo.find_by_book("b99") == []

    def test_returns_all_loans_for_book(self, repo):
        repo.add(_loan("l1", book_id="b1"))
        repo.add(_loan("l2", book_id="b1"))
        assert len(repo.find_by_book("b1")) == 2


class TestFindActive:
    def test_open_loan_is_active(self, repo, loan):
        repo.add(loan)
        assert len(repo.find_active()) == 1

    def test_returned_loan_excluded(self, repo):
        repo.add(_loan("l1", returned_at=_ISSUED + timedelta(days=1)))
        assert repo.find_active() == []

    def test_mixed_returns_only_open(self, repo):
        repo.add(_loan("l1"))
        repo.add(_loan("l2", returned_at=_ISSUED + timedelta(days=1)))
        assert len(repo.find_active()) == 1

    def test_empty_repo_returns_empty(self, repo):
        assert repo.find_active() == []


class TestFindActiveByReader:
    def test_returns_open_loans_for_reader(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r2"))
        assert len(repo.find_active_by_reader("r1")) == 1

    def test_excludes_returned_loans_for_reader(self, repo):
        repo.add(_loan("l1", reader_id="r1", returned_at=_ISSUED + timedelta(days=1)))
        assert repo.find_active_by_reader("r1") == []

    def test_no_match_returns_empty(self, repo):
        assert repo.find_active_by_reader("r99") == []

    def test_mixes_open_and_returned_for_same_reader(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r1", returned_at=_ISSUED + timedelta(days=1)))
        assert len(repo.find_active_by_reader("r1")) == 1


class TestFindOverdue:
    def test_open_loan_past_due_is_overdue(self, repo, loan):
        result = repo.find_overdue(_DUE + timedelta(days=1))
        # loan not yet added
        assert result == []

    def test_returns_overdue_open_loan(self, repo, loan):
        repo.add(loan)
        result = repo.find_overdue(_DUE + timedelta(days=1))
        assert len(result) == 1

    def test_returned_loan_excluded_even_if_past_due(self, repo):
        repo.add(_loan("l1", returned_at=_ISSUED + timedelta(days=1)))
        assert repo.find_overdue(_DUE + timedelta(days=5)) == []

    def test_not_overdue_before_due_date(self, repo, loan):
        repo.add(loan)
        assert repo.find_overdue(_DUE - timedelta(days=1)) == []

    def test_not_overdue_exactly_at_due_date(self, repo, loan):
        repo.add(loan)
        assert repo.find_overdue(_DUE) == []

    def test_multiple_overdue_loans_returned(self, repo):
        repo.add(_loan("l1", reader_id="r1"))
        repo.add(_loan("l2", reader_id="r2"))
        assert len(repo.find_overdue(_DUE + timedelta(days=1))) == 2
