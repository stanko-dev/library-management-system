"""TDD tests for late-submission penalty strategies.

Reference calendar (week of 2025-01-06):
    Mon 06 · Tue 07 · Wed 08 · Thu 09 · Fri 10 · Sat 11 · Sun 12
    Mon 13 · Tue 14 · Wed 15 · Thu 16 · Fri 17
"""
import pytest
from datetime import date

from services.penalty_strategies import (
    PenaltyStrategy,
    FlatPenaltyStrategy,
    ProgressivePenaltyStrategy,
    WeekendExemptPenaltyStrategy,
    CappedPenaltyStrategy,
    PenaltyStrategyFactory,
)

_MON  = date(2025, 1, 6)
_TUE  = date(2025, 1, 7)
_WED  = date(2025, 1, 8)
_THU  = date(2025, 1, 9)
_FRI  = date(2025, 1, 10)
_SAT  = date(2025, 1, 11)
_SUN  = date(2025, 1, 12)
_MON2 = date(2025, 1, 13)
_FRI2 = date(2025, 1, 17)


class TestPenaltyStrategyAbc:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            PenaltyStrategy()  # type: ignore[abstract]


class TestFlatPenaltyStrategyCreation:
    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="points_per_day"):
            FlatPenaltyStrategy(0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="points_per_day"):
            FlatPenaltyStrategy(-1)

    def test_valid_rate_constructs(self):
        assert FlatPenaltyStrategy(2) is not None


class TestFlatPenaltyStrategyCalculate:
    @pytest.fixture
    def s(self) -> FlatPenaltyStrategy:
        return FlatPenaltyStrategy(2)

    def test_on_time_returns_zero(self, s):
        assert s.calculate(_MON, _MON) == 0

    def test_before_due_returns_zero(self, s):
        from datetime import timedelta
        assert s.calculate(_MON, _MON - timedelta(days=3)) == 0

    def test_one_day_late(self, s):
        assert s.calculate(_MON, _TUE) == 2

    def test_three_days_late(self, s):
        assert s.calculate(_MON, _THU) == 6

    def test_seven_days_late(self, s):
        assert s.calculate(_MON, _MON2) == 14

    def test_result_scales_with_rate(self):
        cheap = FlatPenaltyStrategy(1)
        expensive = FlatPenaltyStrategy(5)
        assert expensive.calculate(_MON, _FRI) == cheap.calculate(_MON, _FRI) * 5

    def test_100_day_overdue(self):
        s = FlatPenaltyStrategy(3)
        from datetime import timedelta
        assert s.calculate(_MON, _MON + timedelta(days=100)) == 300


class TestProgressivePenaltyStrategyCreation:
    def test_zero_base_raises(self):
        with pytest.raises(ValueError, match="base_points"):
            ProgressivePenaltyStrategy(0, 1, 50)

    def test_negative_base_raises(self):
        with pytest.raises(ValueError, match="base_points"):
            ProgressivePenaltyStrategy(-1, 1, 50)

    def test_negative_increment_raises(self):
        with pytest.raises(ValueError, match="increment"):
            ProgressivePenaltyStrategy(1, -1, 50)

    def test_zero_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            ProgressivePenaltyStrategy(1, 1, 0)

    def test_negative_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            ProgressivePenaltyStrategy(1, 1, -5)

    def test_valid_params_construct(self):
        assert ProgressivePenaltyStrategy(1, 1, 20) is not None


class TestProgressivePenaltyStrategyCalculate:
    """base=1, increment=1, cap=20.
    Day costs: 1, 2, 3, 4, ...
    Cumulative: 1, 3, 6, 10, ...
    """

    @pytest.fixture
    def s(self) -> ProgressivePenaltyStrategy:
        return ProgressivePenaltyStrategy(1, 1, 20)

    def test_on_time_returns_zero(self, s):
        assert s.calculate(_MON, _MON) == 0

    def test_before_due_returns_zero(self, s):
        from datetime import timedelta
        assert s.calculate(_MON, _MON - timedelta(days=1)) == 0

    def test_one_day_equals_base(self, s):
        assert s.calculate(_MON, _TUE) == 1

    def test_two_days_cumulative(self, s):
        assert s.calculate(_MON, _WED) == 3

    def test_three_days_cumulative(self, s):
        assert s.calculate(_MON, _THU) == 6

    def test_four_days_cumulative(self, s):
        assert s.calculate(_MON, _FRI) == 10

    def test_cap_applied(self):
        s = ProgressivePenaltyStrategy(5, 5, 12)
        assert s.calculate(_MON, _WED) == 12

    def test_cap_exact_boundary(self):
        s = ProgressivePenaltyStrategy(1, 0, 3)
        assert s.calculate(_MON, _THU) == 3

    def test_zero_increment_behaves_flat(self):
        prog = ProgressivePenaltyStrategy(2, 0, 100)
        flat = FlatPenaltyStrategy(2)
        assert prog.calculate(_MON, _FRI) == flat.calculate(_MON, _FRI)

    def test_cap_below_base_clamps_day_one(self):
        s = ProgressivePenaltyStrategy(10, 1, 3)
        assert s.calculate(_MON, _TUE) == 3


class TestWeekendExemptPenaltyStrategyCreation:
    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="points_per_day"):
            WeekendExemptPenaltyStrategy(0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="points_per_day"):
            WeekendExemptPenaltyStrategy(-2)

    def test_valid_constructs(self):
        assert WeekendExemptPenaltyStrategy(1) is not None


class TestWeekendExemptPenaltyStrategyCalculate:
    @pytest.fixture
    def s(self) -> WeekendExemptPenaltyStrategy:
        return WeekendExemptPenaltyStrategy(1)

    def test_on_time_returns_zero(self, s):
        assert s.calculate(_MON, _MON) == 0

    def test_before_due_returns_zero(self, s):
        from datetime import timedelta
        assert s.calculate(_MON, _MON - timedelta(days=1)) == 0

    def test_one_weekday_late(self, s):
        assert s.calculate(_MON, _TUE) == 1

    def test_four_weekdays_same_week(self, s):
        assert s.calculate(_MON, _FRI) == 4

    def test_saturday_not_counted(self, s):
        assert s.calculate(_MON, _SAT) == 4

    def test_sunday_not_counted(self, s):
        assert s.calculate(_MON, _SUN) == 4

    def test_weekend_skipped_next_monday(self, s):
        assert s.calculate(_MON, _MON2) == 5

    def test_due_friday_return_saturday_zero(self, s):
        assert s.calculate(_FRI, _SAT) == 0

    def test_due_friday_return_sunday_zero(self, s):
        assert s.calculate(_FRI, _SUN) == 0

    def test_due_friday_return_next_monday_one(self, s):
        assert s.calculate(_FRI, _MON2) == 1

    def test_two_full_weeks(self, s):
        assert s.calculate(_MON, _FRI2) == 9

    def test_rate_multiplied(self):
        s = WeekendExemptPenaltyStrategy(3)
        assert s.calculate(_MON, _THU) == 9

    def test_all_weekend_returns_zero(self, s):
        assert s.calculate(_FRI, _SUN) == 0


class TestCappedPenaltyStrategyCreation:
    def test_zero_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            CappedPenaltyStrategy(FlatPenaltyStrategy(1), 0)

    def test_negative_cap_raises(self):
        with pytest.raises(ValueError, match="cap"):
            CappedPenaltyStrategy(FlatPenaltyStrategy(1), -5)

    def test_non_strategy_inner_raises(self):
        with pytest.raises(TypeError, match="inner"):
            CappedPenaltyStrategy("not a strategy", 10)  # type: ignore[arg-type]

    def test_valid_constructs(self):
        assert CappedPenaltyStrategy(FlatPenaltyStrategy(1), 10) is not None


class TestCappedPenaltyStrategyCalculate:
    @pytest.fixture
    def inner(self) -> FlatPenaltyStrategy:
        return FlatPenaltyStrategy(2)

    def test_below_cap_returns_inner(self, inner):
        s = CappedPenaltyStrategy(inner, 10)
        assert s.calculate(_MON, _WED) == 4

    def test_above_cap_returns_cap(self, inner):
        s = CappedPenaltyStrategy(inner, 5)
        assert s.calculate(_MON, _FRI) == 5

    def test_exactly_at_cap(self, inner):
        s = CappedPenaltyStrategy(inner, 6)
        assert s.calculate(_MON, _THU) == 6

    def test_zero_overdue_returns_zero(self, inner):
        s = CappedPenaltyStrategy(inner, 5)
        assert s.calculate(_MON, _MON) == 0

    def test_wraps_progressive(self):
        prog = ProgressivePenaltyStrategy(1, 1, 100)
        capped = CappedPenaltyStrategy(prog, 2)
        assert capped.calculate(_MON, _THU) == 2

    def test_wraps_weekend_exempt(self):
        we = WeekendExemptPenaltyStrategy(3)
        capped = CappedPenaltyStrategy(we, 5)
        assert capped.calculate(_MON, _FRI2) == 5

    def test_high_cap_has_no_effect(self, inner):
        s = CappedPenaltyStrategy(inner, 9999)
        assert s.calculate(_MON, _FRI) == inner.calculate(_MON, _FRI)


class TestPenaltyStrategyFactory:
    def test_flat_returns_flat_instance(self):
        s = PenaltyStrategyFactory.flat(2)
        assert isinstance(s, FlatPenaltyStrategy)
        assert s.calculate(_MON, _TUE) == 2

    def test_progressive_returns_progressive_instance(self):
        s = PenaltyStrategyFactory.progressive(1, 0, 10)
        assert isinstance(s, ProgressivePenaltyStrategy)

    def test_weekend_exempt_returns_correct_instance(self):
        s = PenaltyStrategyFactory.weekend_exempt(2)
        assert isinstance(s, WeekendExemptPenaltyStrategy)
        assert s.calculate(_FRI, _SAT) == 0

    def test_capped_returns_capped_instance(self):
        inner = FlatPenaltyStrategy(1)
        s = PenaltyStrategyFactory.capped(inner, 5)
        assert isinstance(s, CappedPenaltyStrategy)

    def test_from_name_flat(self):
        s = PenaltyStrategyFactory.from_name("flat", points_per_day=1)
        assert isinstance(s, FlatPenaltyStrategy)

    def test_from_name_progressive(self):
        s = PenaltyStrategyFactory.from_name(
            "progressive", base_points=1, increment=1, cap=20
        )
        assert isinstance(s, ProgressivePenaltyStrategy)

    def test_from_name_weekend_exempt(self):
        s = PenaltyStrategyFactory.from_name("weekend_exempt", points_per_day=1)
        assert isinstance(s, WeekendExemptPenaltyStrategy)

    def test_from_name_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown_type"):
            PenaltyStrategyFactory.from_name("unknown_type", points_per_day=1)
