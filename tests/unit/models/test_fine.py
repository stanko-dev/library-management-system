import pytest
from decimal import Decimal
from models.fine import Fine


@pytest.fixture
def unpaid_fine() -> Fine:
    return Fine(id="f1", reader_id="r1", loan_id="l1", amount=Decimal("5.00"))


class TestFineCreation:
    def test_all_fields_set_correctly(self, unpaid_fine: Fine):
        assert unpaid_fine.id == "f1"
        assert unpaid_fine.reader_id == "r1"
        assert unpaid_fine.loan_id == "l1"
        assert unpaid_fine.amount == Decimal("5.00")

    def test_default_is_paid_false(self, unpaid_fine: Fine):
        assert unpaid_fine.is_paid is False

    def test_explicit_is_paid_true(self):
        fine = Fine("f2", "r1", "l1", Decimal("10.00"), is_paid=True)
        assert fine.is_paid is True

    def test_minimum_positive_amount_valid(self):
        fine = Fine("f3", "r1", "l1", Decimal("0.01"))
        assert fine.amount == Decimal("0.01")

    def test_large_amount_valid(self):
        fine = Fine("f4", "r1", "l1", Decimal("9999.99"))
        assert fine.amount == Decimal("9999.99")

    def test_integer_amount_valid(self):
        fine = Fine("f5", "r1", "l1", Decimal("50"))
        assert fine.amount == Decimal("50")

    def test_amount_precision_preserved(self):
        fine = Fine("f6", "r1", "l1", Decimal("1.50"))
        assert fine.amount == Decimal("1.50")


class TestFineIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Fine("", "r1", "l1", Decimal("5.00"))

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Fine("  ", "r1", "l1", Decimal("5.00"))

    def test_empty_reader_id_raises(self):
        with pytest.raises(ValueError, match="reader_id"):
            Fine("f1", "", "l1", Decimal("5.00"))

    def test_whitespace_reader_id_raises(self):
        with pytest.raises(ValueError, match="reader_id"):
            Fine("f1", "  ", "l1", Decimal("5.00"))

    def test_empty_loan_id_raises(self):
        with pytest.raises(ValueError, match="loan_id"):
            Fine("f1", "r1", "", Decimal("5.00"))

    def test_whitespace_loan_id_raises(self):
        with pytest.raises(ValueError, match="loan_id"):
            Fine("f1", "r1", "  ", Decimal("5.00"))


class TestFineAmountValidation:
    def test_zero_amount_raises(self):
        with pytest.raises(ValueError, match="amount"):
            Fine("f1", "r1", "l1", Decimal("0"))

    def test_negative_amount_raises(self):
        with pytest.raises(ValueError, match="amount"):
            Fine("f1", "r1", "l1", Decimal("-1.00"))

    def test_tiny_negative_amount_raises(self):
        with pytest.raises(ValueError, match="amount"):
            Fine("f1", "r1", "l1", Decimal("-0.01"))

    def test_large_negative_amount_raises(self):
        with pytest.raises(ValueError, match="amount"):
            Fine("f1", "r1", "l1", Decimal("-999.99"))
