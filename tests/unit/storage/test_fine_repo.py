import pytest
from decimal import Decimal
from models.fine import Fine
from storage.memory.fine_repo import InMemoryFineRepository


def _fine(
    id_: str = "f1",
    reader_id: str = "r1",
    loan_id: str = "l1",
    amount: Decimal = Decimal("5.00"),
    is_paid: bool = False,
) -> Fine:
    return Fine(id=id_, reader_id=reader_id, loan_id=loan_id, amount=amount, is_paid=is_paid)


@pytest.fixture
def repo() -> InMemoryFineRepository:
    return InMemoryFineRepository()


@pytest.fixture
def fine() -> Fine:
    return _fine()


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_stores_fine(self, repo, fine):
        repo.add(fine)
        assert repo.get_by_id("f1") is fine

    def test_add_duplicate_id_raises(self, repo, fine):
        repo.add(fine)
        with pytest.raises(ValueError, match="f1"):
            repo.add(fine)

    def test_add_two_distinct_fines(self, repo):
        repo.add(_fine("f1"))
        repo.add(_fine("f2"))
        assert len(repo.list_all()) == 2


class TestGetById:
    def test_existing_id_returns_fine(self, repo, fine):
        repo.add(fine)
        assert repo.get_by_id("f1") is fine

    def test_missing_id_returns_none(self, repo):
        assert repo.get_by_id("ghost") is None


class TestListAll:
    def test_empty_repo_returns_empty_list(self, repo):
        assert repo.list_all() == []

    def test_returns_all_fines(self, repo):
        repo.add(_fine("f1"))
        repo.add(_fine("f2"))
        assert len(repo.list_all()) == 2

    def test_returns_defensive_copy(self, repo, fine):
        repo.add(fine)
        repo.list_all().clear()
        assert len(repo.list_all()) == 1


class TestUpdate:
    def test_update_marks_paid(self, repo, fine):
        repo.add(fine)
        fine.is_paid = True
        repo.update(fine)
        assert repo.get_by_id("f1").is_paid is True

    def test_update_nonexistent_raises(self, repo, fine):
        with pytest.raises(KeyError):
            repo.update(fine)


class TestDelete:
    def test_delete_removes_fine(self, repo, fine):
        repo.add(fine)
        repo.delete("f1")
        assert repo.get_by_id("f1") is None

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(KeyError):
            repo.delete("ghost")


# ── Query methods ─────────────────────────────────────────────────────────────

class TestFindByReader:
    def test_returns_fines_for_reader(self, repo):
        repo.add(_fine("f1", reader_id="r1"))
        repo.add(_fine("f2", reader_id="r2"))
        result = repo.find_by_reader("r1")
        assert len(result) == 1 and result[0].id == "f1"

    def test_no_match_returns_empty(self, repo, fine):
        repo.add(fine)
        assert repo.find_by_reader("r99") == []

    def test_returns_multiple_fines_for_reader(self, repo):
        repo.add(_fine("f1", reader_id="r1"))
        repo.add(_fine("f2", reader_id="r1"))
        assert len(repo.find_by_reader("r1")) == 2


class TestFindByLoan:
    def test_returns_fines_for_loan(self, repo):
        repo.add(_fine("f1", loan_id="l1"))
        repo.add(_fine("f2", loan_id="l2"))
        assert len(repo.find_by_loan("l1")) == 1

    def test_no_match_returns_empty(self, repo, fine):
        repo.add(fine)
        assert repo.find_by_loan("l99") == []


class TestFindUnpaid:
    def test_unpaid_fine_is_returned(self, repo, fine):
        repo.add(fine)
        assert len(repo.find_unpaid()) == 1

    def test_paid_fine_excluded(self, repo):
        repo.add(_fine("f1", is_paid=True))
        assert repo.find_unpaid() == []

    def test_mixed_returns_only_unpaid(self, repo):
        repo.add(_fine("f1", is_paid=False))
        repo.add(_fine("f2", is_paid=True))
        assert len(repo.find_unpaid()) == 1

    def test_empty_repo_returns_empty(self, repo):
        assert repo.find_unpaid() == []


class TestFindUnpaidByReader:
    def test_returns_unpaid_for_reader(self, repo):
        repo.add(_fine("f1", reader_id="r1", is_paid=False))
        repo.add(_fine("f2", reader_id="r1", is_paid=True))
        assert len(repo.find_unpaid_by_reader("r1")) == 1

    def test_excludes_other_readers(self, repo):
        repo.add(_fine("f1", reader_id="r2", is_paid=False))
        assert repo.find_unpaid_by_reader("r1") == []

    def test_no_fines_returns_empty(self, repo):
        assert repo.find_unpaid_by_reader("r1") == []


class TestTotalUnpaidByReader:
    def test_sums_unpaid_fines(self, repo):
        repo.add(_fine("f1", reader_id="r1", amount=Decimal("3.00")))
        repo.add(_fine("f2", reader_id="r1", amount=Decimal("2.50")))
        assert repo.total_unpaid_by_reader("r1") == Decimal("5.50")

    def test_excludes_paid_fines_from_total(self, repo):
        repo.add(_fine("f1", reader_id="r1", amount=Decimal("10.00"), is_paid=True))
        repo.add(_fine("f2", reader_id="r1", amount=Decimal("5.00"), is_paid=False))
        assert repo.total_unpaid_by_reader("r1") == Decimal("5.00")

    def test_returns_zero_when_no_fines(self, repo):
        assert repo.total_unpaid_by_reader("r1") == Decimal("0")

    def test_excludes_other_readers_from_total(self, repo):
        repo.add(_fine("f1", reader_id="r1", amount=Decimal("5.00")))
        repo.add(_fine("f2", reader_id="r2", amount=Decimal("99.00")))
        assert repo.total_unpaid_by_reader("r1") == Decimal("5.00")

    def test_all_paid_returns_zero(self, repo):
        repo.add(_fine("f1", reader_id="r1", amount=Decimal("7.00"), is_paid=True))
        assert repo.total_unpaid_by_reader("r1") == Decimal("0")
