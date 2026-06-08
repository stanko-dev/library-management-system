from abc import ABC, abstractmethod
from datetime import datetime

from models.student import Student
from models.team import Team
from models.project import Project
from models.milestone import Milestone
from models.submission import Submission
from models.penalty import Penalty
from models.queue_request import QueueRequest
from models.enums import ProjectStatus, QueueRequestStatus


class StudentRepository(ABC):
    @abstractmethod
    def add(self, student: Student) -> None: ...

    @abstractmethod
    def get_by_id(self, student_id: str) -> Student | None: ...

    @abstractmethod
    def list_all(self) -> list[Student]: ...

    @abstractmethod
    def update(self, student: Student) -> None: ...

    @abstractmethod
    def delete(self, student_id: str) -> None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Student]: ...

    @abstractmethod
    def find_active(self) -> list[Student]: ...

    @abstractmethod
    def find_blocked(self) -> list[Student]: ...


class TeamRepository(ABC):
    @abstractmethod
    def add(self, team: Team) -> None: ...

    @abstractmethod
    def get_by_id(self, team_id: str) -> Team | None: ...

    @abstractmethod
    def list_all(self) -> list[Team]: ...

    @abstractmethod
    def update(self, team: Team) -> None: ...

    @abstractmethod
    def delete(self, team_id: str) -> None: ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Team]: ...


class ProjectRepository(ABC):
    @abstractmethod
    def add(self, project: Project) -> None: ...

    @abstractmethod
    def get_by_id(self, project_id: str) -> Project | None: ...

    @abstractmethod
    def list_all(self) -> list[Project]: ...

    @abstractmethod
    def update(self, project: Project) -> None: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...

    @abstractmethod
    def find_by_team(self, team_id: str) -> list[Project]: ...

    @abstractmethod
    def find_by_status(self, status: ProjectStatus) -> list[Project]: ...


class MilestoneRepository(ABC):
    @abstractmethod
    def add(self, milestone: Milestone) -> None: ...

    @abstractmethod
    def get_by_id(self, milestone_id: str) -> Milestone | None: ...

    @abstractmethod
    def list_all(self) -> list[Milestone]: ...

    @abstractmethod
    def update(self, milestone: Milestone) -> None: ...

    @abstractmethod
    def delete(self, milestone_id: str) -> None: ...

    @abstractmethod
    def find_by_project(self, project_id: str) -> list[Milestone]: ...

    @abstractmethod
    def find_pending(self) -> list[Milestone]: ...

    @abstractmethod
    def find_overdue(self, as_of: datetime) -> list[Milestone]: ...


class SubmissionRepository(ABC):
    @abstractmethod
    def add(self, submission: Submission) -> None: ...

    @abstractmethod
    def get_by_id(self, submission_id: str) -> Submission | None: ...

    @abstractmethod
    def list_all(self) -> list[Submission]: ...

    @abstractmethod
    def update(self, submission: Submission) -> None: ...

    @abstractmethod
    def delete(self, submission_id: str) -> None: ...

    @abstractmethod
    def find_by_milestone(self, milestone_id: str) -> list[Submission]: ...

    @abstractmethod
    def find_by_team(self, team_id: str) -> list[Submission]: ...


class PenaltyRepository(ABC):
    @abstractmethod
    def add(self, penalty: Penalty) -> None: ...

    @abstractmethod
    def get_by_id(self, penalty_id: str) -> Penalty | None: ...

    @abstractmethod
    def list_all(self) -> list[Penalty]: ...

    @abstractmethod
    def update(self, penalty: Penalty) -> None: ...

    @abstractmethod
    def delete(self, penalty_id: str) -> None: ...

    @abstractmethod
    def find_by_student(self, student_id: str) -> list[Penalty]: ...

    @abstractmethod
    def find_by_milestone(self, milestone_id: str) -> list[Penalty]: ...

    @abstractmethod
    def find_unresolved(self) -> list[Penalty]: ...

    @abstractmethod
    def find_unresolved_by_student(self, student_id: str) -> list[Penalty]: ...

    @abstractmethod
    def total_unresolved_by_student(self, student_id: str) -> int: ...


class QueueRequestRepository(ABC):
    @abstractmethod
    def add(self, request: QueueRequest) -> None: ...

    @abstractmethod
    def get_by_id(self, request_id: str) -> QueueRequest | None: ...

    @abstractmethod
    def list_all(self) -> list[QueueRequest]: ...

    @abstractmethod
    def update(self, request: QueueRequest) -> None: ...

    @abstractmethod
    def delete(self, request_id: str) -> None: ...

    @abstractmethod
    def find_by_student(self, student_id: str) -> list[QueueRequest]: ...

    @abstractmethod
    def find_by_team(self, team_id: str) -> list[QueueRequest]: ...

    @abstractmethod
    def find_pending(self) -> list[QueueRequest]: ...

    @abstractmethod
    def find_pending_by_team(self, team_id: str) -> list[QueueRequest]: ...
