import pytest
from datetime import datetime, timedelta
from models.loan import Loan


_ISSUED = datetime(2025, 1, 1, 12, 0, 0)
_DUE = _ISSUED + timedelta(days=14)


@pytest.fixture
def active_loan() -> Loan:
    return Loan(id="l1", book_id="b1", reader_id="r1", issued_at=_ISSUED, due_date=_DUE)


@pytest.fixture
def returned_loan() -> Loan:
    return Loan(
        id="l2",
        book_id="b1",
        reader_id="r1",
        issued_at=_ISSUED,
        due_date=_DUE,
        returned_at=_ISSUED + timedelta(days=7),
    )


class TestLoanCreation:
    def test_all_fields_set_correctly(self, active_loan: Loan):
        assert active_loan.id == "l1"
        assert active_loan.book_id == "b1"
        assert active_loan.reader_id == "r1"
        assert active_loan.issued_at == _ISSUED
        assert active_loan.due_date == _DUE

    def test_returned_at_defaults_to_none(self, active_loan: Loan):
        assert active_loan.returned_at is None

    def test_returned_at_set_explicitly(self, returned_loan: Loan):
        assert returned_loan.returned_at == _ISSUED + timedelta(days=7)

    def test_returned_at_equal_to_issued_is_valid(self):
        loan = Loan("l3", "b1", "r1", _ISSUED, _DUE, returned_at=_ISSUED)
        assert loan.returned_at == _ISSUED

    def test_returned_at_after_due_date_is_valid(self):
        overdue_return = _DUE + timedelta(days=5)
        loan = Loan("l4", "b1", "r1", _ISSUED, _DUE, returned_at=overdue_return)
        assert loan.returned_at == overdue_return

    def test_due_date_one_second_after_issued_is_valid(self):
        loan = Loan("l5", "b1", "r1", _ISSUED, _ISSUED + timedelta(seconds=1))
        assert loan.due_date == _ISSUED + timedelta(seconds=1)

    def test_long_loan_period_is_valid(self):
        loan = Loan("l6", "b1", "r1", _ISSUED, _ISSUED + timedelta(days=365))
        assert loan.due_date == _ISSUED + timedelta(days=365)


class TestLoanIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Loan("", "b1", "r1", _ISSUED, _DUE)

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Loan("  ", "b1", "r1", _ISSUED, _DUE)

    def test_empty_book_id_raises(self):
        with pytest.raises(ValueError, match="book_id"):
            Loan("l1", "", "r1", _ISSUED, _DUE)

    def test_whitespace_book_id_raises(self):
        with pytest.raises(ValueError, match="book_id"):
            Loan("l1", "  ", "r1", _ISSUED, _DUE)

    def test_empty_reader_id_raises(self):
        with pytest.raises(ValueError, match="reader_id"):
            Loan("l1", "b1", "", _ISSUED, _DUE)

    def test_whitespace_reader_id_raises(self):
        with pytest.raises(ValueError, match="reader_id"):
            Loan("l1", "b1", "  ", _ISSUED, _DUE)


class TestLoanDateValidation:
    def test_due_date_before_issued_raises(self):
        with pytest.raises(ValueError, match="due_date"):
            Loan("l1", "b1", "r1", _ISSUED, _ISSUED - timedelta(days=1))

    def test_due_date_equal_to_issued_raises(self):
        with pytest.raises(ValueError, match="due_date"):
            Loan("l1", "b1", "r1", _ISSUED, _ISSUED)

    def test_due_date_one_second_before_issued_raises(self):
        with pytest.raises(ValueError, match="due_date"):
            Loan("l1", "b1", "r1", _ISSUED, _ISSUED - timedelta(seconds=1))

    def test_returned_at_one_second_before_issued_raises(self):
        with pytest.raises(ValueError, match="returned_at"):
            Loan("l1", "b1", "r1", _ISSUED, _DUE, returned_at=_ISSUED - timedelta(seconds=1))


class TestLoanIsActiveProperty:
    def test_is_active_true_when_not_returned(self, active_loan: Loan):
        assert active_loan.is_active is True

    def test_is_active_false_when_returned(self, returned_loan: Loan):
        assert returned_loan.is_active is False


class TestLoanIsOverdueMethod:
    def test_not_overdue_before_due_date(self, active_loan: Loan):
        assert active_loan.is_overdue(_DUE - timedelta(days=1)) is False

    def test_not_overdue_exactly_at_due_date(self, active_loan: Loan):
        assert active_loan.is_overdue(_DUE) is False

    def test_overdue_one_second_past_due(self, active_loan: Loan):
        assert active_loan.is_overdue(_DUE + timedelta(seconds=1)) is True

    def test_overdue_many_days_past_due(self, active_loan: Loan):
        assert active_loan.is_overdue(_DUE + timedelta(days=30)) is True

    def test_not_overdue_when_returned_even_past_due(self, returned_loan: Loan):
        assert returned_loan.is_overdue(_DUE + timedelta(days=10)) is False
