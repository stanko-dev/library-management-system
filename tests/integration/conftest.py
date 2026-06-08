"""Shared fixtures for all integration tests.

Every fixture wires REAL in-memory repositories and services. No mocks.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from models.student import Student
from models.team import Team
from models.project import Project
from models.enums import StudentRole, ProjectStatus
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.milestone_repo import InMemoryMilestoneRepository
from storage.memory.submission_repo import InMemorySubmissionRepository
from storage.memory.penalty_repo import InMemoryPenaltyRepository
from storage.memory.queue_request_repo import InMemoryQueueRequestRepository
from services.events import EventBus
from services.penalty_strategies import FlatPenaltyStrategy
from services.notification import StudentNotifier
from services.project_service import ProjectService
from services.milestone_service import MilestoneService
from services.team_service import TeamService
from services.membership_service import MembershipService


class Clock:
    """Deterministic, manually-advanceable clock for injecting into services."""

    def __init__(self, start: datetime) -> None:
        self._dt = start

    def __call__(self) -> datetime:
        return self._dt

    def advance(self, **kwargs) -> None:
        self._dt += timedelta(**kwargs)

    def set(self, dt: datetime) -> None:
        self._dt = dt


@dataclass
class Repos:
    students: InMemoryStudentRepository
    teams: InMemoryTeamRepository
    projects: InMemoryProjectRepository
    milestones: InMemoryMilestoneRepository
    submissions: InMemorySubmissionRepository
    penalties: InMemoryPenaltyRepository
    queue_requests: InMemoryQueueRequestRepository


@dataclass
class Svc:
    project: ProjectService
    milestone: MilestoneService
    team: TeamService
    membership: MembershipService
    notifier: StudentNotifier
    bus: EventBus


@pytest.fixture
def clock() -> Clock:
    return Clock(datetime(2025, 10, 1, 9, 0, 0))


@pytest.fixture
def repos() -> Repos:
    return Repos(
        students=InMemoryStudentRepository(),
        teams=InMemoryTeamRepository(),
        projects=InMemoryProjectRepository(),
        milestones=InMemoryMilestoneRepository(),
        submissions=InMemorySubmissionRepository(),
        penalties=InMemoryPenaltyRepository(),
        queue_requests=InMemoryQueueRequestRepository(),
    )


@pytest.fixture
def svc(repos: Repos, clock: Clock) -> Svc:
    strategy = FlatPenaltyStrategy(2)
    bus = EventBus()
    notifier = StudentNotifier(
        repos.milestones, repos.projects, repos.teams,
        repos.queue_requests, repos.students,
    )
    bus.subscribe(notifier)

    return Svc(
        project=ProjectService(repos.projects, repos.teams),
        milestone=MilestoneService(
            repos.milestones, repos.submissions, repos.penalties,
            repos.projects, repos.teams, repos.students,
            strategy, bus, clock=clock,
        ),
        team=TeamService(
            repos.teams, repos.students, repos.queue_requests,
            bus, expiry_days=7, clock=clock,
        ),
        membership=MembershipService(
            repos.students, repos.penalties,
            max_unresolved_points=10,
            max_missed_deadlines=3,
        ),
        notifier=notifier,
        bus=bus,
    )


def make_student(sid: str = "s1", role: StudentRole = StudentRole.MEMBER) -> Student:
    return Student(sid, f"Student {sid}", role)


def make_team(tid: str = "t1", capacity: int = 4) -> Team:
    return Team(tid, f"Team {tid}", capacity)
