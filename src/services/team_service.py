import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from models.team import Team
from models.queue_request import QueueRequest
from models.enums import QueueRequestStatus
from services.events import DeadlineSubject, TeamSpotAvailableEvent
from services.priority import queue_priority_key
from storage.interfaces import TeamRepository, StudentRepository, QueueRequestRepository
from utils.exceptions import (
    StudentNotFoundError, TeamNotFoundError, StudentBlockedError,
    DuplicateQueueRequestError, StudentNotInTeamError,
)


class TeamService:
    """Manages team membership and join queue with priority ordering."""

    def __init__(
        self,
        team_repo: TeamRepository,
        student_repo: StudentRepository,
        queue_request_repo: QueueRequestRepository,
        event_bus: DeadlineSubject,
        expiry_days: int = 7,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._team_repo = team_repo
        self._student_repo = student_repo
        self._queue_request_repo = queue_request_repo
        self._event_bus = event_bus
        self._expiry_days = expiry_days
        self._clock = clock

    def create_team(self, team_id: str, name: str, capacity: int) -> Team:
        """Create a new empty team and store it."""
        team = Team(id=team_id, name=name, capacity=capacity)
        self._team_repo.add(team)
        return team

    def join_or_queue(self, student_id: str, team_id: str) -> Team | QueueRequest:
        """Add student to team if space available; otherwise add to queue.

        Raises:
            StudentNotFoundError: student does not exist.
            TeamNotFoundError: team does not exist.
            StudentBlockedError: student is blocked.
            DuplicateQueueRequestError: student already queued for this team.
        """
        student = self._student_repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student not found: {student_id!r}")
        if student.is_blocked:
            raise StudentBlockedError(f"Student is blocked: {student_id!r}")

        team = self._team_repo.get_by_id(team_id)
        if team is None:
            raise TeamNotFoundError(f"Team not found: {team_id!r}")

        if not team.is_full:
            team.member_ids.append(student_id)
            self._team_repo.update(team)
            student.active_projects_count += 1
            self._student_repo.update(student)
            return team

        pending = self._queue_request_repo.find_pending_by_team(team_id)
        if any(r.student_id == student_id for r in pending):
            raise DuplicateQueueRequestError(
                f"Student {student_id!r} already queued for team {team_id!r}"
            )

        now = self._clock()
        request = QueueRequest(
            id=str(uuid.uuid4()),
            student_id=student_id,
            team_id=team_id,
            created_at=now,
            expires_at=now + timedelta(days=self._expiry_days),
        )
        self._queue_request_repo.add(request)
        return request

    def leave_team(self, student_id: str, team_id: str) -> None:
        """Remove student from team and fire TeamSpotAvailableEvent.

        Raises:
            StudentNotFoundError: student does not exist.
            TeamNotFoundError: team does not exist.
            StudentNotInTeamError: student is not a member of the team.
        """
        student = self._student_repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student not found: {student_id!r}")

        team = self._team_repo.get_by_id(team_id)
        if team is None:
            raise TeamNotFoundError(f"Team not found: {team_id!r}")

        if student_id not in team.member_ids:
            raise StudentNotInTeamError(
                f"Student {student_id!r} is not in team {team_id!r}"
            )

        team.member_ids.remove(student_id)
        self._team_repo.update(team)

        student.active_projects_count = max(0, student.active_projects_count - 1)
        self._student_repo.update(student)

        self._event_bus.notify_team_spot(TeamSpotAvailableEvent(team_id))

    def expire_old(self, as_of: datetime | None = None) -> list[QueueRequest]:
        """Expire all PENDING requests whose expires_at <= as_of.

        Uses the injected clock when as_of is None.
        """
        reference = as_of if as_of is not None else self._clock()
        expired = []
        for req in self._queue_request_repo.find_pending():
            if req.expires_at <= reference:
                req.status = QueueRequestStatus.EXPIRED
                self._queue_request_repo.update(req)
                expired.append(req)
        return expired

    def get_next_in_queue(self, team_id: str) -> QueueRequest | None:
        """Return the highest-priority pending request for team_id, or None."""
        pending = self._queue_request_repo.find_pending_by_team(team_id)
        if not pending:
            return None
        return min(pending, key=lambda r: queue_priority_key(r, self._student_repo))
