from abc import ABC, abstractmethod
from datetime import date, timedelta


class PenaltyStrategy(ABC):
    """Contract for all late-submission penalty strategies."""

    @abstractmethod
    def calculate(self, due_date: date, submitted_date: date) -> int:
        """Return penalty points for a submission on submitted_date when due on due_date.

        Implementations must return 0 when submitted_date <= due_date.
        """
        ...


class FlatPenaltyStrategy(PenaltyStrategy):
    """Fixed points charged for every calendar day late."""

    def __init__(self, points_per_day: int) -> None:
        if points_per_day <= 0:
            raise ValueError("points_per_day must be positive")
        self._points_per_day = points_per_day

    def calculate(self, due_date: date, submitted_date: date) -> int:
        overdue = max(0, (submitted_date - due_date).days)
        return overdue * self._points_per_day


class ProgressivePenaltyStrategy(PenaltyStrategy):
    """Points grow linearly with each extra late day; total capped at max.

    Day n cost = base_points + (n-1) * increment   (n starts at 1)
    Total       = sum of day costs, then min(total, cap)
    """

    def __init__(self, base_points: int, increment: int, cap: int) -> None:
        if base_points <= 0:
            raise ValueError("base_points must be positive")
        if increment < 0:
            raise ValueError("increment cannot be negative")
        if cap <= 0:
            raise ValueError("cap must be positive")
        self._base = base_points
        self._increment = increment
        self._cap = cap

    def calculate(self, due_date: date, submitted_date: date) -> int:
        overdue = max(0, (submitted_date - due_date).days)
        if overdue == 0:
            return 0
        total = sum(
            self._base + n * self._increment
            for n in range(overdue)
        )
        return min(total, self._cap)


class WeekendExemptPenaltyStrategy(PenaltyStrategy):
    """Fixed points per late weekday; Saturday and Sunday are not counted.

    The overdue period is the half-open interval (due_date, submitted_date].
    """

    def __init__(self, points_per_day: int) -> None:
        if points_per_day <= 0:
            raise ValueError("points_per_day must be positive")
        self._points_per_day = points_per_day

    def calculate(self, due_date: date, submitted_date: date) -> int:
        if submitted_date <= due_date:
            return 0
        weekday_count = 0
        current = due_date + timedelta(days=1)
        while current <= submitted_date:
            if current.weekday() < 5:
                weekday_count += 1
            current += timedelta(days=1)
        return weekday_count * self._points_per_day


class CappedPenaltyStrategy(PenaltyStrategy):
    """Decorator: wraps any inner strategy and clamps its result to a ceiling."""

    def __init__(self, inner: PenaltyStrategy, cap: int) -> None:
        if not isinstance(inner, PenaltyStrategy):
            raise TypeError("inner must be a PenaltyStrategy instance")
        if cap <= 0:
            raise ValueError("cap must be positive")
        self._inner = inner
        self._cap = cap

    def calculate(self, due_date: date, submitted_date: date) -> int:
        return min(self._inner.calculate(due_date, submitted_date), self._cap)


class PenaltyStrategyFactory:
    """Creates PenaltyStrategy instances by type or name."""

    @staticmethod
    def flat(points_per_day: int) -> FlatPenaltyStrategy:
        return FlatPenaltyStrategy(points_per_day)

    @staticmethod
    def progressive(base_points: int, increment: int, cap: int) -> ProgressivePenaltyStrategy:
        return ProgressivePenaltyStrategy(base_points, increment, cap)

    @staticmethod
    def weekend_exempt(points_per_day: int) -> WeekendExemptPenaltyStrategy:
        return WeekendExemptPenaltyStrategy(points_per_day)

    @staticmethod
    def capped(inner: PenaltyStrategy, cap: int) -> CappedPenaltyStrategy:
        return CappedPenaltyStrategy(inner, cap)

    @classmethod
    def from_name(cls, name: str, **kwargs: int) -> PenaltyStrategy:
        """Select a strategy by string name; raises ValueError for unknown names."""
        match name:
            case "flat":
                return cls.flat(kwargs["points_per_day"])
            case "progressive":
                return cls.progressive(
                    kwargs["base_points"], kwargs["increment"], kwargs["cap"]
                )
            case "weekend_exempt":
                return cls.weekend_exempt(kwargs["points_per_day"])
            case _:
                raise ValueError(f"Unknown strategy type: {name!r}")
