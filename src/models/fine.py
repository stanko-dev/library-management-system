from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Fine:
    id: str
    reader_id: str
    loan_id: str
    amount: Decimal
    is_paid: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not self.reader_id or not self.reader_id.strip():
            raise ValueError("reader_id cannot be empty")
        if not self.loan_id or not self.loan_id.strip():
            raise ValueError("loan_id cannot be empty")
        if self.amount <= Decimal("0"):
            raise ValueError("amount must be positive (got {self.amount})")
