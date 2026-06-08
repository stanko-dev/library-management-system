import uuid
from collections.abc import Callable
from datetime import datetime

from models.milestone import Milestone
from models.submission import Submission
from models.penalty import Penalty
from models.enums import MilestoneStatus
from services.events import DeadlineSubject, MilestoneStatusChangedEvent
from services.penalty_strategies import PenaltyStrategy
from storage.interfaces import (
    MilestoneRepository, SubmissionRepository, PenaltyRepository,
    ProjectRepository, TeamRepository, StudentRepository,
)
from utils.exceptions import MilestoneNotFoundError, AlreadySubmittedError, ProjectNotFoundError


class MilestoneService:
    """Handles milestone lifecycle: creation, submission, penalty calculation."""

    def __init__(
        self,
        milestone_repo: MilestoneRepository,
        submission_repo: SubmissionRepository,
        penalty_repo: PenaltyRepository,
        project_repo: ProjectRepository,
        team_repo: TeamRepository,
        student_repo: StudentRepository,
        penalty_strategy: PenaltyStrategy,
        event_bus: DeadlineSubject,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._milestone_repo = milestone_repo
        self._submission_repo = submission_repo
        self._penalty_repo = penalty_repo
        self._project_repo = project_repo
        self._team_repo = team_repo
        self._student_repo = student_repo
        self._penalty_strategy = penalty_strategy
        self._event_bus = event_bus
        self._clock = clock

    def add_milestone(self, project_id: str, title: str, due_date: datetime) -> Milestone:
        """Add a new PENDING milestone to a project.

        Raises:
            ProjectNotFoundError: project does not exist.
        """
        if self._project_repo.get_by_id(project_id) is None:
            raise ProjectNotFoundError(f"Project not found: {project_id!r}")

        milestone = Milestone(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            due_date=due_date,
        )
        self._milestone_repo.add(milestone)
        return milestone

    def submit(self, milestone_id: str) -> tuple[Submission, list[Penalty]]:
        """Record a milestone submission, compute penalties if late, notify observers.

        Returns a (Submission, list[Penalty]) tuple.

        Raises:
            MilestoneNotFoundError: milestone does not exist.
            AlreadySubmittedError: milestone is already SUBMITTED or LATE.
        """
        milestone = self._milestone_repo.get_by_id(milestone_id)
        if milestone is None:
            raise MilestoneNotFoundError(f"Milestone not found: {milestone_id!r}")
        if milestone.status in (MilestoneStatus.SUBMITTED, MilestoneStatus.LATE):
            raise AlreadySubmittedError(f"Milestone already submitted: {milestone_id!r}")

        now = self._clock()
        milestone.submitted_at = now

        days_late = self._penalty_strategy.calculate(
            milestone.due_date.date(), now.date()
        )
        is_late = days_late > 0
        milestone.status = MilestoneStatus.LATE if is_late else MilestoneStatus.SUBMITTED
        self._milestone_repo.update(milestone)

        penalties = self._create_penalties(milestone, days_late) if is_late else []

        project = self._project_repo.get_by_id(milestone.project_id)
        team_id = project.team_id if project else None

        submission = Submission(
            id=str(uuid.uuid4()),
            milestone_id=milestone_id,
            team_id=team_id or "unknown",
            submitted_at=now,
        )
        self._submission_repo.add(submission)

        self._event_bus.notify_milestone_status(
            MilestoneStatusChangedEvent(milestone_id, milestone.status)
        )
        return submission, penalties

    def mark_missed(self, milestone_id: str) -> list[Penalty]:
        """Mark a milestone as MISSED and create penalties for all team members.

        Raises:
            MilestoneNotFoundError: milestone does not exist.
        """
        milestone = self._milestone_repo.get_by_id(milestone_id)
        if milestone is None:
            raise MilestoneNotFoundError(f"Milestone not found: {milestone_id!r}")

        now = self._clock()
        days_late = self._penalty_strategy.calculate(milestone.due_date.date(), now.date())
        milestone.status = MilestoneStatus.MISSED
        self._milestone_repo.update(milestone)

        penalties = self._create_penalties(milestone, days_late)
        self._event_bus.notify_milestone_status(
            MilestoneStatusChangedEvent(milestone_id, MilestoneStatus.MISSED)
        )
        return penalties

    def _create_penalties(self, milestone: Milestone, days_late: int) -> list[Penalty]:
        project = self._project_repo.get_by_id(milestone.project_id)
        if project is None or project.team_id is None:
            return []
        team = self._team_repo.get_by_id(project.team_id)
        if team is None:
            return []

        penalties = []
        for student_id in team.member_ids:
            penalty = Penalty(
                id=str(uuid.uuid4()),
                student_id=student_id,
                milestone_id=milestone.id,
                points=days_late,
            )
            self._penalty_repo.add(penalty)
            student = self._student_repo.get_by_id(student_id)
            if student is not None:
                student.missed_deadlines_count += 1
                self._student_repo.update(student)
            penalties.append(penalty)
        return penalties
