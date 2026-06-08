"""TDD tests for EventBus, observer ABCs, and event dataclasses."""
import pytest
from unittest.mock import MagicMock

from services.events import (
    MilestoneStatusChangedEvent,
    TeamSpotAvailableEvent,
    DeadlineObserver,
    DeadlineSubject,
    EventBus,
)
from models.enums import MilestoneStatus


# ── Event dataclasses ─────────────────────────────────────────────────────────

class TestMilestoneStatusChangedEvent:
    def test_fields_stored(self):
        e = MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE)
        assert e.milestone_id == "m1"
        assert e.new_status == MilestoneStatus.LATE

    def test_frozen(self):
        e = MilestoneStatusChangedEvent("m1", MilestoneStatus.SUBMITTED)
        with pytest.raises((AttributeError, TypeError)):
            e.milestone_id = "m2"  # type: ignore[misc]

    def test_empty_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            MilestoneStatusChangedEvent("", MilestoneStatus.LATE)

    def test_whitespace_milestone_id_raises(self):
        with pytest.raises(ValueError, match="milestone_id"):
            MilestoneStatusChangedEvent("   ", MilestoneStatus.LATE)


class TestTeamSpotAvailableEvent:
    def test_fields_stored(self):
        e = TeamSpotAvailableEvent("t1")
        assert e.team_id == "t1"

    def test_frozen(self):
        e = TeamSpotAvailableEvent("t1")
        with pytest.raises((AttributeError, TypeError)):
            e.team_id = "t2"  # type: ignore[misc]

    def test_empty_team_id_raises(self):
        with pytest.raises(ValueError, match="team_id"):
            TeamSpotAvailableEvent("")

    def test_whitespace_team_id_raises(self):
        with pytest.raises(ValueError, match="team_id"):
            TeamSpotAvailableEvent("   ")


# ── ABCs not instantiable ────────────────────────────────────────────────────

class TestAbstractClasses:
    def test_deadline_observer_not_instantiable(self):
        with pytest.raises(TypeError):
            DeadlineObserver()  # type: ignore[abstract]

    def test_deadline_subject_not_instantiable(self):
        with pytest.raises(TypeError):
            DeadlineSubject()  # type: ignore[abstract]


# ── EventBus ─────────────────────────────────────────────────────────────────

class TestEventBusSubscribe:
    def test_subscribe_once(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        event = MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE)
        bus.notify_milestone_status(event)
        obs.on_milestone_status_changed.assert_called_once_with(event)

    def test_subscribe_idempotent(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        bus.subscribe(obs)
        bus.notify_milestone_status(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        assert obs.on_milestone_status_changed.call_count == 1

    def test_multiple_observers_all_notified(self):
        bus = EventBus()
        obs1, obs2 = MagicMock(spec=DeadlineObserver), MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs1)
        bus.subscribe(obs2)
        event = MilestoneStatusChangedEvent("m1", MilestoneStatus.SUBMITTED)
        bus.notify_milestone_status(event)
        obs1.on_milestone_status_changed.assert_called_once()
        obs2.on_milestone_status_changed.assert_called_once()


class TestEventBusUnsubscribe:
    def test_unsubscribe_stops_notifications(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        bus.unsubscribe(obs)
        bus.notify_milestone_status(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        obs.on_milestone_status_changed.assert_not_called()

    def test_unsubscribe_non_subscribed_raises(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        with pytest.raises(ValueError, match="not subscribed"):
            bus.unsubscribe(obs)

    def test_unsubscribe_during_notify_safe(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)

        def side_effect(event):
            bus.unsubscribe(obs)

        obs.on_milestone_status_changed.side_effect = side_effect
        bus.subscribe(obs)
        bus.notify_milestone_status(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        # no RuntimeError raised


class TestEventBusNotifyMilestone:
    def test_notify_milestone_calls_on_milestone_status_changed(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        event = MilestoneStatusChangedEvent("m1", MilestoneStatus.MISSED)
        bus.notify_milestone_status(event)
        obs.on_milestone_status_changed.assert_called_once_with(event)

    def test_notify_milestone_does_not_call_team_spot(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        bus.notify_milestone_status(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))
        obs.on_team_spot_available.assert_not_called()

    def test_notify_no_observers_is_safe(self):
        bus = EventBus()
        bus.notify_milestone_status(MilestoneStatusChangedEvent("m1", MilestoneStatus.LATE))


class TestEventBusNotifyTeamSpot:
    def test_notify_team_spot_calls_on_team_spot_available(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        event = TeamSpotAvailableEvent("t1")
        bus.notify_team_spot(event)
        obs.on_team_spot_available.assert_called_once_with(event)

    def test_notify_team_spot_does_not_call_milestone(self):
        bus = EventBus()
        obs = MagicMock(spec=DeadlineObserver)
        bus.subscribe(obs)
        bus.notify_team_spot(TeamSpotAvailableEvent("t1"))
        obs.on_milestone_status_changed.assert_not_called()

    def test_notify_team_spot_no_observers_is_safe(self):
        EventBus().notify_team_spot(TeamSpotAvailableEvent("t1"))

    def test_event_bus_is_deadline_subject(self):
        assert isinstance(EventBus(), DeadlineSubject)
