from dataclasses import dataclass

from storage.interfaces import (
    MilestoneRepository, ProjectRepository, TeamRepository,
    QueueRequestRepository, StudentRepository,
)
from services.events import (
    DeadlineObserver, MilestoneStatusChangedEvent, TeamSpotAvailableEvent,
)
from services.priority import queue_priority_key


@dataclass(frozen=True)
class Notification:
    """Immutable record that a student was alerted about a milestone or team spot."""

    student_id: str
    milestone_id: str | None = None
    team_id: str | None = None


class StudentNotifier(DeadlineObserver):
    """Concrete observer: records Notifications when events arrive.

    On milestone status change: notifies every member of the project's team.
    On team spot available: notifies the highest-priority student in the queue.
    """

    def __init__(
        self,
        milestone_repo: MilestoneRepository,
        project_repo: ProjectRepository,
        team_repo: TeamRepository,
        queue_request_repo: QueueRequestRepository,
        student_repo: StudentRepository,
    ) -> None:
        self._milestone_repo = milestone_repo
        self._project_repo = project_repo
        self._team_repo = team_repo
        self._queue_request_repo = queue_request_repo
        self._student_repo = student_repo
        self._notifications: list[Notification] = []

    def on_milestone_status_changed(self, event: MilestoneStatusChangedEvent) -> None:
        milestone = self._milestone_repo.get_by_id(event.milestone_id)
        if milestone is None:
            return
        project = self._project_repo.get_by_id(milestone.project_id)
        if project is None or project.team_id is None:
            return
        team = self._team_repo.get_by_id(project.team_id)
        if team is None:
            return
        for student_id in team.member_ids:
            self._notifications.append(
                Notification(student_id=student_id, milestone_id=event.milestone_id)
            )

    def on_team_spot_available(self, event: TeamSpotAvailableEvent) -> None:
        pending = self._queue_request_repo.find_pending_by_team(event.team_id)
        if not pending:
            return
        first = min(pending, key=lambda r: queue_priority_key(r, self._student_repo))
        self._notifications.append(
            Notification(student_id=first.student_id, team_id=event.team_id)
        )

    def get_notifications(self) -> list[Notification]:
        return list(self._notifications)

    def get_notifications_for_student(self, student_id: str) -> list[Notification]:
        return [n for n in self._notifications if n.student_id == student_id]
