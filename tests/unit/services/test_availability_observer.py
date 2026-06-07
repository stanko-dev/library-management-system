"""TDD tests for the Observer pattern — book availability notifications.

Structure under test:
    BookAvailableEvent          — immutable event DTO
    BookAvailabilityObserver    — ABC (observer interface)
    BookAvailabilitySubject     — ABC (subject interface)
    EventBus                    — concrete subject
    Notification                — immutable notification record
    ReaderNotifier              — concrete observer; picks by membership then wait time
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

from models.reader import Reader
from models.reservation import Reservation
from models.enums import MembershipType, ReservationStatus
from services.events import (
    BookAvailableEvent,
    BookAvailabilityObserver,
    BookAvailabilitySubject,
    EventBus,
)
from services.notification import Notification, ReaderNotifier


# ── Test doubles ──────────────────────────────────────────────────────────────

class _SpyObserver(BookAvailabilityObserver):
    def __init__(self) -> None:
        self.received: list[BookAvailableEvent] = []

    def on_book_available(self, event: BookAvailableEvent) -> None:
        self.received.append(event)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_T0 = datetime(2025, 3, 1, 9, 0, 0)


def _reservation(
    id_: str,
    reader_id: str,
    book_id: str = "b1",
    created_at: datetime = _T0,
) -> Reservation:
    return Reservation(
        id=id_, book_id=book_id, reader_id=reader_id,
        created_at=created_at, expires_at=created_at + timedelta(days=3),
        status=ReservationStatus.ACTIVE,
    )


def _reader(reader_id: str, membership: MembershipType = MembershipType.STANDARD) -> Reader:
    return Reader(id=reader_id, name="Test", membership=membership)


def _notifier(reservation_return_value, reader_side_effect=None) -> ReaderNotifier:
    """Helper: build a ReaderNotifier with pre-configured mocks."""
    res_repo = MagicMock()
    res_repo.find_active_by_book.return_value = reservation_return_value
    rdr_repo = MagicMock()
    if reader_side_effect is not None:
        rdr_repo.get_by_id.side_effect = reader_side_effect
    else:
        rdr_repo.get_by_id.return_value = None   # default → treated as STANDARD rank
    return ReaderNotifier(res_repo, rdr_repo)


# ── BookAvailableEvent ────────────────────────────────────────────────────────

class TestBookAvailableEvent:
    def test_book_id_stored(self):
        assert BookAvailableEvent(book_id="b1").book_id == "b1"

    def test_event_is_immutable(self):
        e = BookAvailableEvent(book_id="b1")
        with pytest.raises((AttributeError, TypeError)):
            e.book_id = "b2"  # type: ignore[misc]

    def test_empty_book_id_raises(self):
        with pytest.raises(ValueError, match="book_id"):
            BookAvailableEvent(book_id="")

    def test_whitespace_book_id_raises(self):
        with pytest.raises(ValueError, match="book_id"):
            BookAvailableEvent(book_id="   ")

    def test_equal_events_same_book(self):
        assert BookAvailableEvent("b1") == BookAvailableEvent("b1")

    def test_unequal_events_different_books(self):
        assert BookAvailableEvent("b1") != BookAvailableEvent("b2")


# ── Abstract base classes ─────────────────────────────────────────────────────

class TestAbstractClasses:
    def test_observer_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            BookAvailabilityObserver()  # type: ignore[abstract]

    def test_subject_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            BookAvailabilitySubject()  # type: ignore[abstract]


# ── EventBus — subscribe ──────────────────────────────────────────────────────

class TestEventBusSubscribe:
    def test_subscribe_registers_observer(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        bus.notify(BookAvailableEvent("b1"))
        assert len(spy.received) == 1

    def test_subscribing_twice_is_idempotent(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        bus.subscribe(spy)
        bus.notify(BookAvailableEvent("b1"))
        assert len(spy.received) == 1

    def test_multiple_distinct_observers_all_receive(self):
        bus = EventBus()
        spies = [_SpyObserver() for _ in range(3)]
        for s in spies:
            bus.subscribe(s)
        bus.notify(BookAvailableEvent("b1"))
        assert all(len(s.received) == 1 for s in spies)

    def test_subscribe_returns_none(self):
        assert EventBus().subscribe(_SpyObserver()) is None


# ── EventBus — unsubscribe ────────────────────────────────────────────────────

class TestEventBusUnsubscribe:
    def test_unsubscribe_stops_notifications(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        bus.unsubscribe(spy)
        bus.notify(BookAvailableEvent("b1"))
        assert spy.received == []

    def test_unsubscribe_non_subscribed_raises(self):
        with pytest.raises(ValueError):
            EventBus().unsubscribe(_SpyObserver())

    def test_unsubscribe_only_removes_target(self):
        bus = EventBus()
        spy_a, spy_b = _SpyObserver(), _SpyObserver()
        bus.subscribe(spy_a)
        bus.subscribe(spy_b)
        bus.unsubscribe(spy_a)
        bus.notify(BookAvailableEvent("b1"))
        assert spy_a.received == [] and len(spy_b.received) == 1

    def test_resubscribe_after_unsubscribe_works(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        bus.unsubscribe(spy)
        bus.subscribe(spy)
        bus.notify(BookAvailableEvent("b1"))
        assert len(spy.received) == 1

    def test_unsubscribe_returns_none(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        assert bus.unsubscribe(spy) is None


# ── EventBus — notify ─────────────────────────────────────────────────────────

class TestEventBusNotify:
    def test_no_observers_does_not_raise(self):
        EventBus().notify(BookAvailableEvent("b1"))

    def test_passes_exact_event_object(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        event = BookAvailableEvent("b99")
        bus.notify(event)
        assert spy.received[0] is event

    def test_dispatches_to_all_observers(self):
        bus = EventBus()
        spies = [_SpyObserver() for _ in range(4)]
        for s in spies:
            bus.subscribe(s)
        bus.notify(BookAvailableEvent("b1"))
        assert all(s.received for s in spies)

    def test_multiple_events_received_in_order(self):
        bus, spy = EventBus(), _SpyObserver()
        bus.subscribe(spy)
        e1, e2 = BookAvailableEvent("b1"), BookAvailableEvent("b2")
        bus.notify(e1)
        bus.notify(e2)
        assert spy.received == [e1, e2]

    def test_snapshot_prevents_mutation_crash(self):
        """Observer unsubscribing another during notify must not raise RuntimeError."""
        bus = EventBus()
        victim = _SpyObserver()

        class _Remover(BookAvailabilityObserver):
            def on_book_available(self, event: BookAvailableEvent) -> None:
                bus.unsubscribe(victim)

        bus.subscribe(_Remover())
        bus.subscribe(victim)
        bus.notify(BookAvailableEvent("b1"))  # must not raise

    def test_failing_observer_propagates_exception(self):
        bus = EventBus()

        class _Broken(BookAvailabilityObserver):
            def on_book_available(self, event: BookAvailableEvent) -> None:
                raise RuntimeError("boom")

        bus.subscribe(_Broken())
        with pytest.raises(RuntimeError, match="boom"):
            bus.notify(BookAvailableEvent("b1"))

    def test_mock_observer_called_once_with_event(self):
        bus = EventBus()
        mock_obs = MagicMock(spec=BookAvailabilityObserver)
        bus.subscribe(mock_obs)
        event = BookAvailableEvent("bX")
        bus.notify(event)
        mock_obs.on_book_available.assert_called_once_with(event)


# ── ReaderNotifier — on_book_available ───────────────────────────────────────

class TestReaderNotifierOnBookAvailable:
    def test_no_reservations_records_nothing(self):
        notifier = _notifier([])
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert notifier.get_notifications() == []

    def test_single_reservation_notifies_that_reader(self):
        notifier = _notifier([_reservation("res1", "r1")])
        notifier.on_book_available(BookAvailableEvent("b1"))
        n = notifier.get_notifications()
        assert len(n) == 1 and n[0].reader_id == "r1" and n[0].book_id == "b1"

    def test_oldest_created_at_wins_within_same_membership(self):
        notifier = _notifier([
            _reservation("res3", "r3", created_at=_T0 + timedelta(hours=2)),
            _reservation("res1", "r1", created_at=_T0),           # ← oldest
            _reservation("res2", "r2", created_at=_T0 + timedelta(hours=1)),
        ])
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert notifier.get_notifications()[0].reader_id == "r1"

    def test_premium_wins_over_standard_regardless_of_wait(self):
        """PREMIUM reader with newer reservation beats STANDARD with older one."""
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = [
            _reservation("res1", "r-std", created_at=_T0),              # STANDARD, oldest
            _reservation("res2", "r-pre", created_at=_T0 + timedelta(hours=1)),  # PREMIUM, newer
        ]
        rdr_repo = MagicMock()
        rdr_repo.get_by_id.side_effect = lambda rid: {
            "r-std": _reader("r-std", MembershipType.STANDARD),
            "r-pre": _reader("r-pre", MembershipType.PREMIUM),
        }.get(rid)
        notifier = ReaderNotifier(res_repo, rdr_repo)
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert notifier.get_notifications()[0].reader_id == "r-pre"

    def test_two_premium_oldest_wins(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = [
            _reservation("res2", "r2", created_at=_T0 + timedelta(hours=1)),
            _reservation("res1", "r1", created_at=_T0),   # older PREMIUM → wins
        ]
        rdr_repo = MagicMock()
        rdr_repo.get_by_id.return_value = _reader("rx", MembershipType.PREMIUM)
        notifier = ReaderNotifier(res_repo, rdr_repo)
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert notifier.get_notifications()[0].reader_id == "r1"

    def test_unknown_reader_treated_as_standard(self):
        """Reservation whose reader cannot be found falls back to lowest priority."""
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = [
            _reservation("res1", "ghost", created_at=_T0),
            _reservation("res2", "r-pre", created_at=_T0 + timedelta(hours=1)),
        ]
        rdr_repo = MagicMock()
        rdr_repo.get_by_id.side_effect = lambda rid: (
            _reader(rid, MembershipType.PREMIUM) if rid == "r-pre" else None
        )
        notifier = ReaderNotifier(res_repo, rdr_repo)
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert notifier.get_notifications()[0].reader_id == "r-pre"

    def test_queries_repo_with_correct_book_id(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = []
        notifier = ReaderNotifier(res_repo, MagicMock())
        notifier.on_book_available(BookAvailableEvent("book-XYZ"))
        res_repo.find_active_by_book.assert_called_once_with("book-XYZ")

    def test_notifications_accumulate_across_events(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.side_effect = [
            [_reservation("res1", "r1", book_id="b1")],
            [_reservation("res2", "r2", book_id="b2")],
        ]
        notifier = ReaderNotifier(res_repo, MagicMock())
        notifier.on_book_available(BookAvailableEvent("b1"))
        notifier.on_book_available(BookAvailableEvent("b2"))
        notifs = notifier.get_notifications()
        assert len(notifs) == 2
        assert notifs[0].book_id == "b1" and notifs[1].book_id == "b2"

    def test_only_first_in_queue_notified(self):
        notifier = _notifier([
            _reservation("res1", "r1", created_at=_T0),
            _reservation("res2", "r2", created_at=_T0 + timedelta(minutes=1)),
        ])
        notifier.on_book_available(BookAvailableEvent("b1"))
        assert len(notifier.get_notifications()) == 1


# ── ReaderNotifier — get_notifications ───────────────────────────────────────

class TestReaderNotifierGetNotifications:
    def test_initially_empty(self):
        assert ReaderNotifier(MagicMock(), MagicMock()).get_notifications() == []

    def test_returns_defensive_copy(self):
        notifier = _notifier([_reservation("r1", "r1")])
        notifier.on_book_available(BookAvailableEvent("b1"))
        notifier.get_notifications().clear()
        assert len(notifier.get_notifications()) == 1

    def test_get_notifications_for_reader_filters(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.side_effect = [
            [_reservation("res1", "r1", book_id="b1")],
            [_reservation("res2", "r2", book_id="b2")],
        ]
        notifier = ReaderNotifier(res_repo, MagicMock())
        notifier.on_book_available(BookAvailableEvent("b1"))
        notifier.on_book_available(BookAvailableEvent("b2"))
        assert len(notifier.get_notifications_for_reader("r1")) == 1
        assert notifier.get_notifications_for_reader("r99") == []

    def test_notification_is_immutable(self):
        n = Notification(reader_id="r1", book_id="b1")
        with pytest.raises((AttributeError, TypeError)):
            n.reader_id = "r2"  # type: ignore[misc]


# ── Full wiring: EventBus + ReaderNotifier ────────────────────────────────────

class TestEventBusWithReaderNotifier:
    def test_notifier_receives_event_published_through_bus(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = [_reservation("res1", "r1")]
        bus = EventBus()
        notifier = ReaderNotifier(res_repo, MagicMock())
        bus.subscribe(notifier)
        bus.notify(BookAvailableEvent("b1"))
        assert len(notifier.get_notifications()) == 1

    def test_unsubscribed_notifier_receives_nothing(self):
        res_repo = MagicMock()
        bus = EventBus()
        notifier = ReaderNotifier(res_repo, MagicMock())
        bus.subscribe(notifier)
        bus.unsubscribe(notifier)
        bus.notify(BookAvailableEvent("b1"))
        res_repo.find_active_by_book.assert_not_called()

    def test_independent_buses_do_not_cross_notify(self):
        res_repo = MagicMock()
        res_repo.find_active_by_book.return_value = [_reservation("res1", "r1")]
        bus_a, bus_b = EventBus(), EventBus()
        notifier = ReaderNotifier(res_repo, MagicMock())
        bus_a.subscribe(notifier)
        bus_b.notify(BookAvailableEvent("b1"))      # different bus — silent
        assert notifier.get_notifications() == []
        bus_a.notify(BookAvailableEvent("b1"))       # own bus — fires
        assert len(notifier.get_notifications()) == 1
