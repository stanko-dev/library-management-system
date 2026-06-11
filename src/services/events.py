from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.enums import MilestoneStatus


@dataclass(frozen=True)
class MilestoneStatusChangedEvent:
    """Fired when a milestone's status changes (SUBMITTED, LATE, or MISSED)."""

    milestone_id: str
    new_status: MilestoneStatus

    def __post_init__(self) -> None:
        if not self.milestone_id or not self.milestone_id.strip():
            raise ValueError("milestone_id cannot be empty")


@dataclass(frozen=True)
class TeamSpotAvailableEvent:
    """Fired when a member leaves a team, freeing a spot."""

    team_id: str

    def __post_init__(self) -> None:
        if not self.team_id or not self.team_id.strip():
            raise ValueError("team_id cannot be empty")


class DeadlineObserver(ABC):
    """Receives deadline and team-spot events."""

    @abstractmethod
    def on_milestone_status_changed(self, event: MilestoneStatusChangedEvent) -> None: ...

    @abstractmethod
    def on_team_spot_available(self, event: TeamSpotAvailableEvent) -> None: ...


class DeadlineSubject(ABC):
    """Manages a set of observers and dispatches events to them."""

    @abstractmethod
    def subscribe(self, observer: DeadlineObserver) -> None: ...

    @abstractmethod
    def unsubscribe(self, observer: DeadlineObserver) -> None: ...

    @abstractmethod
    def notify_milestone_status(self, event: MilestoneStatusChangedEvent) -> None: ...

    @abstractmethod
    def notify_team_spot(self, event: TeamSpotAvailableEvent) -> None: ...


class EventBus(DeadlineSubject):
    """In-memory publish/subscribe bus.

    Guarantees:
    - Duplicate subscribe calls are idempotent.
    - notify iterates a snapshot so observers may unsubscribe mid-dispatch.
    - Unsubscribing an observer not registered raises ValueError.
    """

    def __init__(self) -> None:
        self._observers: list[DeadlineObserver] = []

    def subscribe(self, observer: DeadlineObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: DeadlineObserver) -> None:
        if observer not in self._observers:
            raise ValueError(f"Observer is not subscribed: {observer!r}")
        self._observers.remove(observer)

    def notify_milestone_status(self, event: MilestoneStatusChangedEvent) -> None:
        for observer in self._observers[:]:
            observer.on_milestone_status_changed(event)

    def notify_team_spot(self, event: TeamSpotAvailableEvent) -> None:
        for observer in self._observers[:]:
            observer.on_team_spot_available(event)
