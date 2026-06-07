"""TDD tests for fine calculation strategies.

Reference calendar (week of 2025-01-06):
    Mon 06 · Tue 07 · Wed 08 · Thu 09 · Fri 10 · Sat 11 · Sun 12
    Mon 13 · Tue 14 · Wed 15 · Thu 16 · Fri 17
"""
import pytest
from datetime import date
from decimal import Decimal

from services.fine_strategies import (
    FineStrategy,
    FlatFineStrategy,
    ProgressiveFineStrategy,
    WeekendExemptStrategy,
    CappedFineStrategy,
    FineStrategyFactory,
)

# ── Shared reference dates ────────────────────────────────────────────────────
_MON  = date(2025, 1, 6)   # Monday   — used as a typical due_date
_TUE  = date(2025, 1, 7)
_WED  = date(2025, 1, 8)
_THU  = date(2025, 1, 9)
_FRI  = date(2025, 1, 10)  # Friday
_SAT  = date(2025, 1, 11)  # Saturday
_SUN  = date(2025, 1, 12)  # Sunday
_MON2 = date(2025, 1, 13)  # Monday  (next week)
_FRI2 = date(2025, 1, 17)  # Friday  (next week)


# ── ABC ───────────────────────────────────────────────────────────────────────

class TestFineStrategyAbc:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            FineStrategy()  # type: ignore[abstract]


# ── FlatFineStrategy ──────────────────────────────────────────────────────────

class TestFlatFineStrategyCreation:
    def test_zero_daily_rate_raises(self):
        with pytest.raises(ValueError, match="daily_rate"):
            FlatFineStrategy(Decimal("0"))

    def test_negative_daily_rate_raises(self):
        with pytest.raises(ValueError, match="daily_rate"):
            FlatFineStrategy(Decimal("-1.00"))

    def test_valid_rate_constructs(self):
        s = FlatFineStrategy(Decimal("1.00"))
        assert s is not None


class TestFlatFineStrategyCalculate:
    @pytest.fixture
    def s(self) -> FlatFineStrategy:
        return FlatFineStrategy(Decimal("2.00"))

    def test_returned_on_due_date_is_zero(self, s):
        assert s.calculate(_MON, _MON) == Decimal("0")

    def test_returned_before_due_date_is_zero(self, s):
        assert s.calculate(_MON, _TUE - __import__("datetime").timedelta(days=5)) == Decimal("0")

    def test_one_day_overdue(self, s):
        assert s.calculate(_MON, _TUE) == Decimal("2.00")

    def test_three_days_overdue(self, s):
        assert s.calculate(_MON, _THU) == Decimal("6.00")

    def test_seven_days_overdue(self, s):
        assert s.calculate(_MON, _MON2) == Decimal("14.00")

    def test_result_scales_linearly_with_rate(self):
        cheap = FlatFineStrategy(Decimal("0.50"))
        expensive = FlatFineStrategy(Decimal("5.00"))
        assert expensive.calculate(_MON, _FRI) == cheap.calculate(_MON, _FRI) * 10

    def test_large_overdue_no_internal_cap(self, s):
        from datetime import timedelta
        far_future = _MON + __import__("datetime").timedelta(days=100)
        assert s.calculate(_MON, far_future) == Decimal("200.00")

    def test_fractional_rate(self):
        s = FlatFineStrategy(Decimal("0.25"))
        assert s.calculate(_MON, _WED) == Decimal("0.50")


# ── ProgressiveFineStrategy ───────────────────────────────────────────────────

class TestProgressiveFineStrategyCreation:
    def test_zero_base_rate_raises(self):
        with pytest.raises(ValueError, match="base_rate"):
            ProgressiveFineStrategy(Decimal("0"), Decimal("0.50"), Decimal("20"))

    def test_negative_base_rate_raises(self):
        with pytest.raises(ValueError, match="base_rate"):
            ProgressiveFineStrategy(Decimal("-1"), Decimal("0.50"), Decimal("20"))

    def test_negative_increment_raises(self):
        with pytest.raises(ValueError, match="increment"):
            ProgressiveFineStrategy(Decimal("1"), Decimal("-0.10"), Decimal("20"))

    def test_zero_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            ProgressiveFineStrategy(Decimal("1"), Decimal("0.50"), Decimal("0"))

    def test_negative_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            ProgressiveFineStrategy(Decimal("1"), Decimal("0.50"), Decimal("-5"))

    def test_valid_params_construct(self):
        s = ProgressiveFineStrategy(Decimal("1"), Decimal("0.50"), Decimal("20"))
        assert s is not None


class TestProgressiveFineStrategyCalculate:
    """base_rate=1.00, increment=0.50, cap=20.00
    Day costs: 1.00 · 1.50 · 2.00 · 2.50 · ...
    Cumulative: 1.00 · 2.50 · 4.50 · 7.00 · ...
    """

    @pytest.fixture
    def s(self) -> ProgressiveFineStrategy:
        return ProgressiveFineStrategy(Decimal("1.00"), Decimal("0.50"), Decimal("20.00"))

    def test_returned_on_due_date_is_zero(self, s):
        assert s.calculate(_MON, _MON) == Decimal("0")

    def test_returned_before_due_is_zero(self, s):
        from datetime import timedelta
        assert s.calculate(_MON, _MON - timedelta(days=1)) == Decimal("0")

    def test_one_day_equals_base_rate(self, s):
        assert s.calculate(_MON, _TUE) == Decimal("1.00")

    def test_two_days_cumulative(self, s):
        # 1.00 + 1.50 = 2.50
        assert s.calculate(_MON, _WED) == Decimal("2.50")

    def test_three_days_cumulative(self, s):
        # 1.00 + 1.50 + 2.00 = 4.50
        assert s.calculate(_MON, _THU) == Decimal("4.50")

    def test_four_days_cumulative(self, s):
        # 1.00 + 1.50 + 2.00 + 2.50 = 7.00
        assert s.calculate(_MON, _FRI) == Decimal("7.00")

    def test_cap_applied_when_exceeded(self):
        s = ProgressiveFineStrategy(Decimal("5.00"), Decimal("5.00"), Decimal("12.00"))
        # Day1=5, Day2=10 → total 15 → capped at 12
        assert s.calculate(_MON, _WED) == Decimal("12.00")

    def test_result_exactly_at_cap_boundary(self):
        # base=1, increment=0, cap=3 → 3 days = 3.00 (exactly cap)
        s = ProgressiveFineStrategy(Decimal("1.00"), Decimal("0"), Decimal("3.00"))
        assert s.calculate(_MON, _THU) == Decimal("3.00")

    def test_zero_increment_behaves_like_flat(self):
        # increment=0 means constant daily rate → same as FlatFineStrategy
        s_prog = ProgressiveFineStrategy(Decimal("2.00"), Decimal("0"), Decimal("100.00"))
        s_flat = FlatFineStrategy(Decimal("2.00"))
        assert s_prog.calculate(_MON, _FRI) == s_flat.calculate(_MON, _FRI)

    def test_cap_less_than_base_rate_clamps_from_day_one(self):
        s = ProgressiveFineStrategy(Decimal("5.00"), Decimal("1.00"), Decimal("3.00"))
        assert s.calculate(_MON, _TUE) == Decimal("3.00")


# ── WeekendExemptStrategy ─────────────────────────────────────────────────────

class TestWeekendExemptStrategyCreation:
    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="daily_rate"):
            WeekendExemptStrategy(Decimal("0"))

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="daily_rate"):
            WeekendExemptStrategy(Decimal("-0.50"))

    def test_valid_rate_constructs(self):
        assert WeekendExemptStrategy(Decimal("1.00")) is not None


class TestWeekendExemptStrategyCalculate:
    """
    due=Monday(6-Jan). Overdue period = day AFTER due_date up to return_date inclusive.

    Cases:
        due=Mon, return=Mon  → 0 days overdue
        due=Mon, return=Tue  → 1 weekday  (Tue)
        due=Mon, return=Fri  → 4 weekdays (Tue–Fri)
        due=Mon, return=Sat  → 4 weekdays (Tue–Fri; Sat skipped)
        due=Mon, return=Sun  → 4 weekdays (Tue–Fri; Sat,Sun skipped)
        due=Mon, return=Mon2 → 5 weekdays (Tue–Fri + Mon2)
        due=Fri, return=Sat  → 0 weekdays (only Sat in overdue period)
        due=Fri, return=Sun  → 0 weekdays (Sat+Sun)
        due=Fri, return=Mon2 → 1 weekday  (Mon2)
        due=Sat, return=Mon2 → 1 weekday  (Sun skipped, Mon2 counted)
        due=Mon, return=Fri2 → 9 weekdays (Tue–Fri + Mon2–Fri2)
    """

    @pytest.fixture
    def s(self) -> WeekendExemptStrategy:
        return WeekendExemptStrategy(Decimal("1.00"))

    def test_returned_on_due_date_is_zero(self, s):
        assert s.calculate(_MON, _MON) == Decimal("0")

    def test_returned_before_due_is_zero(self, s):
        from datetime import timedelta
        assert s.calculate(_MON, _MON - timedelta(days=1)) == Decimal("0")

    def test_one_weekday_overdue(self, s):
        assert s.calculate(_MON, _TUE) == Decimal("1.00")

    def test_four_weekdays_in_same_week(self, s):
        # due Mon, return Fri → Tue Wed Thu Fri = 4 weekdays
        assert s.calculate(_MON, _FRI) == Decimal("4.00")

    def test_saturday_not_counted(self, s):
        # due Mon, return Sat → Tue Wed Thu Fri Sat → 4 weekdays
        assert s.calculate(_MON, _SAT) == Decimal("4.00")

    def test_sunday_not_counted(self, s):
        # due Mon, return Sun → Tue Wed Thu Fri Sat Sun → 4 weekdays
        assert s.calculate(_MON, _SUN) == Decimal("4.00")

    def test_full_weekend_skipped_next_monday(self, s):
        # due Mon, return Mon2 → Tue-Fri + Mon2 = 5 weekdays
        assert s.calculate(_MON, _MON2) == Decimal("5.00")

    def test_due_friday_returned_saturday_is_zero(self, s):
        # only Sat in overdue period → 0 weekdays
        assert s.calculate(_FRI, _SAT) == Decimal("0")

    def test_due_friday_returned_sunday_is_zero(self, s):
        # Sat + Sun in overdue period → 0 weekdays
        assert s.calculate(_FRI, _SUN) == Decimal("0")

    def test_due_friday_returned_next_monday_one_weekday(self, s):
        # overdue period: Sat Sun Mon2 → 1 weekday
        assert s.calculate(_FRI, _MON2) == Decimal("1.00")

    def test_due_saturday_returned_next_monday_one_weekday(self, s):
        # overdue period: Sun Mon2 → Sun skipped, Mon2 counted = 1 weekday
        assert s.calculate(_SAT, _MON2) == Decimal("1.00")

    def test_due_sunday_returned_next_monday_one_weekday(self, s):
        # overdue period: Mon2 only → 1 weekday
        assert s.calculate(_SUN, _MON2) == Decimal("1.00")

    def test_two_full_weeks_nine_weekdays(self, s):
        # due Mon, return Fri2 → Tue–Fri (4) + Mon2–Fri2 (5) = 9 weekdays
        assert s.calculate(_MON, _FRI2) == Decimal("9.00")

    def test_rate_multiplied_correctly(self):
        s = WeekendExemptStrategy(Decimal("3.50"))
        # due Mon, return Thu → Tue Wed Thu = 3 weekdays × 3.50 = 10.50
        assert s.calculate(_MON, _THU) == Decimal("10.50")

    def test_all_overdue_days_weekend_returns_zero(self, s):
        # due Fri, return Sun → Sat Sun → 0 weekdays
        assert s.calculate(_FRI, _SUN) == Decimal("0")


# ── CappedFineStrategy ────────────────────────────────────────────────────────

class TestCappedFineStrategyCreation:
    def test_zero_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            CappedFineStrategy(FlatFineStrategy(Decimal("1")), Decimal("0"))

    def test_negative_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            CappedFineStrategy(FlatFineStrategy(Decimal("1")), Decimal("-5"))

    def test_non_strategy_inner_raises(self):
        with pytest.raises(TypeError, match="inner"):
            CappedFineStrategy("not a strategy", Decimal("10"))  # type: ignore[arg-type]

    def test_valid_args_construct(self):
        s = CappedFineStrategy(FlatFineStrategy(Decimal("1")), Decimal("10"))
        assert s is not None


class TestCappedFineStrategyCalculate:
    @pytest.fixture
    def inner(self) -> FlatFineStrategy:
        return FlatFineStrategy(Decimal("2.00"))  # 2.00 / day

    def test_below_cap_returns_inner_result(self, inner):
        # 2 days × 2.00 = 4.00; cap=10.00 → 4.00
        s = CappedFineStrategy(inner, Decimal("10.00"))
        assert s.calculate(_MON, _WED) == Decimal("4.00")

    def test_above_cap_returns_cap(self, inner):
        # 4 days × 2.00 = 8.00; cap=5.00 → 5.00
        s = CappedFineStrategy(inner, Decimal("5.00"))
        assert s.calculate(_MON, _FRI) == Decimal("5.00")

    def test_exactly_at_cap_returns_cap(self, inner):
        # 3 days × 2.00 = 6.00; cap=6.00 → 6.00
        s = CappedFineStrategy(inner, Decimal("6.00"))
        assert s.calculate(_MON, _THU) == Decimal("6.00")

    def test_zero_overdue_returns_zero(self, inner):
        s = CappedFineStrategy(inner, Decimal("5.00"))
        assert s.calculate(_MON, _MON) == Decimal("0")

    def test_wraps_progressive_strategy(self):
        prog = ProgressiveFineStrategy(Decimal("1.00"), Decimal("0.50"), Decimal("100"))
        capped = CappedFineStrategy(prog, Decimal("2.00"))
        # 3 days progressive = 4.50 → capped to 2.00
        assert capped.calculate(_MON, _THU) == Decimal("2.00")

    def test_wraps_weekend_exempt_strategy(self):
        we = WeekendExemptStrategy(Decimal("3.00"))
        capped = CappedFineStrategy(we, Decimal("5.00"))
        # due Mon, return Fri2 → 9 weekdays × 3.00 = 27.00 → capped at 5.00
        assert capped.calculate(_MON, _FRI2) == Decimal("5.00")

    def test_cap_above_max_possible_fine_has_no_effect(self, inner):
        s = CappedFineStrategy(inner, Decimal("9999.00"))
        assert s.calculate(_MON, _FRI) == inner.calculate(_MON, _FRI)


# ── FineStrategyFactory ───────────────────────────────────────────────────────

class TestFineStrategyFactory:
    def test_flat_returns_flat_instance(self):
        s = FineStrategyFactory.flat(Decimal("1.50"))
        assert isinstance(s, FlatFineStrategy)
        assert s.calculate(_MON, _TUE) == Decimal("1.50")

    def test_progressive_returns_progressive_instance(self):
        s = FineStrategyFactory.progressive(Decimal("1"), Decimal("0"), Decimal("10"))
        assert isinstance(s, ProgressiveFineStrategy)

    def test_weekend_exempt_returns_correct_instance(self):
        s = FineStrategyFactory.weekend_exempt(Decimal("2.00"))
        assert isinstance(s, WeekendExemptStrategy)
        assert s.calculate(_FRI, _SAT) == Decimal("0")

    def test_capped_returns_capped_instance(self):
        inner = FlatFineStrategy(Decimal("1.00"))
        s = FineStrategyFactory.capped(inner, Decimal("5.00"))
        assert isinstance(s, CappedFineStrategy)

    def test_from_name_flat(self):
        s = FineStrategyFactory.from_name("flat", daily_rate=Decimal("1.00"))
        assert isinstance(s, FlatFineStrategy)

    def test_from_name_progressive(self):
        s = FineStrategyFactory.from_name(
            "progressive",
            base_rate=Decimal("1.00"),
            increment=Decimal("0.50"),
            cap=Decimal("20.00"),
        )
        assert isinstance(s, ProgressiveFineStrategy)

    def test_from_name_weekend_exempt(self):
        s = FineStrategyFactory.from_name("weekend_exempt", daily_rate=Decimal("1.00"))
        assert isinstance(s, WeekendExemptStrategy)

    def test_from_name_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown_type"):
            FineStrategyFactory.from_name("unknown_type", daily_rate=Decimal("1"))
