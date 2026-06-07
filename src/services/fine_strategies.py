from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal


class FineStrategy(ABC):
    """Contract for all fine-calculation strategies."""

    @abstractmethod
    def calculate(self, due_date: date, return_date: date) -> Decimal:
        """Return the fine owed for a loan returned on return_date when due on due_date.

        Implementations must return Decimal("0") when return_date <= due_date.
        """
        ...


class FlatFineStrategy(FineStrategy):
    """Fixed amount charged for every calendar overdue day."""

    def __init__(self, daily_rate: Decimal) -> None:
        if daily_rate <= Decimal("0"):
            raise ValueError("daily_rate must be positive")
        self._daily_rate = daily_rate

    def calculate(self, due_date: date, return_date: date) -> Decimal:
        overdue_days = max(0, (return_date - due_date).days)
        return Decimal(overdue_days) * self._daily_rate


class ProgressiveFineStrategy(FineStrategy):
    """Daily rate increases linearly with each extra overdue day; total capped at ceiling.

    Day n cost  = base_rate + (n-1) * increment   (n starts at 1)
    Total       = sum of day costs, then min(total, cap)
    """

    def __init__(self, base_rate: Decimal, increment: Decimal, cap: Decimal) -> None:
        if base_rate <= Decimal("0"):
            raise ValueError("base_rate must be positive")
        if increment < Decimal("0"):
            raise ValueError("increment cannot be negative")
        if cap <= Decimal("0"):
            raise ValueError("cap must be positive")
        self._base_rate = base_rate
        self._increment = increment
        self._cap = cap

    def calculate(self, due_date: date, return_date: date) -> Decimal:
        overdue_days = max(0, (return_date - due_date).days)
        if overdue_days == 0:
            return Decimal("0")
        total = sum(
            self._base_rate + Decimal(n) * self._increment
            for n in range(overdue_days)   # n = 0 … overdue_days-1
        )
        return min(total, self._cap)


class WeekendExemptStrategy(FineStrategy):
    """Fixed rate per overdue day; Saturday and Sunday are not counted.

    The overdue period is the half-open interval (due_date, return_date].
    """

    def __init__(self, daily_rate: Decimal) -> None:
        if daily_rate <= Decimal("0"):
            raise ValueError("daily_rate must be positive")
        self._daily_rate = daily_rate

    def calculate(self, due_date: date, return_date: date) -> Decimal:
        if return_date <= due_date:
            return Decimal("0")
        weekday_count = 0
        current = due_date + timedelta(days=1)
        while current <= return_date:
            if current.weekday() < 5:   # 0 = Monday … 4 = Friday
                weekday_count += 1
            current += timedelta(days=1)
        return Decimal(weekday_count) * self._daily_rate


class CappedFineStrategy(FineStrategy):
    """Decorator: delegates to any inner strategy, then clamps the result to a ceiling.

    Compose this to add a hard cap to any existing strategy without changing it.
    """

    def __init__(self, inner: FineStrategy, cap: Decimal) -> None:
        if not isinstance(inner, FineStrategy):
            raise TypeError("inner must be a FineStrategy instance")
        if cap <= Decimal("0"):
            raise ValueError("cap must be positive")
        self._inner = inner
        self._cap = cap

    def calculate(self, due_date: date, return_date: date) -> Decimal:
        return min(self._inner.calculate(due_date, return_date), self._cap)


class FineStrategyFactory:
    """Creates FineStrategy instances by type.

    Use the named constructors (flat, progressive, weekend_exempt, capped) for
    type-safe construction, or from_name for configuration-driven selection.
    """

    @staticmethod
    def flat(daily_rate: Decimal) -> FlatFineStrategy:
        return FlatFineStrategy(daily_rate)

    @staticmethod
    def progressive(
        base_rate: Decimal, increment: Decimal, cap: Decimal
    ) -> ProgressiveFineStrategy:
        return ProgressiveFineStrategy(base_rate, increment, cap)

    @staticmethod
    def weekend_exempt(daily_rate: Decimal) -> WeekendExemptStrategy:
        return WeekendExemptStrategy(daily_rate)

    @staticmethod
    def capped(inner: FineStrategy, cap: Decimal) -> CappedFineStrategy:
        return CappedFineStrategy(inner, cap)

    @classmethod
    def from_name(cls, name: str, **kwargs: Decimal) -> FineStrategy:
        """Select a strategy by string name; raises ValueError for unknown names."""
        match name:
            case "flat":
                return cls.flat(kwargs["daily_rate"])
            case "progressive":
                return cls.progressive(
                    kwargs["base_rate"], kwargs["increment"], kwargs["cap"]
                )
            case "weekend_exempt":
                return cls.weekend_exempt(kwargs["daily_rate"])
            case _:
                raise ValueError(f"Unknown strategy type: {name!r}")
