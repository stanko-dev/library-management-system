import uuid
from datetime import datetime

from models.project import Project
from models.enums import ProjectStatus
from storage.interfaces import ProjectRepository, TeamRepository
from utils.exceptions import (
    ProjectNotFoundError, TeamNotFoundError, InvalidStatusTransitionError,
)

_VALID_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT: {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}


class ProjectService:
    """Manages project lifecycle: creation, team assignment, and status transitions."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        team_repo: TeamRepository,
    ) -> None:
        self._project_repo = project_repo
        self._team_repo = team_repo

    def create_project(
        self, title: str, description: str, team_id: str | None = None
    ) -> Project:
        """Create a DRAFT project.

        Raises:
            TeamNotFoundError: team_id given but does not exist.
        """
        if team_id is not None and self._team_repo.get_by_id(team_id) is None:
            raise TeamNotFoundError(f"Team not found: {team_id!r}")

        project = Project(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            team_id=team_id,
            created_at=datetime.now(),
        )
        self._project_repo.add(project)
        return project

    def assign_team(self, project_id: str, team_id: str) -> Project:
        """Assign or reassign a team to a project.

        Raises:
            ProjectNotFoundError: project does not exist.
            TeamNotFoundError: team does not exist.
            InvalidStatusTransitionError: project is ARCHIVED.
        """
        project = self._project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project not found: {project_id!r}")
        if project.status == ProjectStatus.ARCHIVED:
            raise InvalidStatusTransitionError(
                f"Cannot assign team to an ARCHIVED project: {project_id!r}"
            )
        if self._team_repo.get_by_id(team_id) is None:
            raise TeamNotFoundError(f"Team not found: {team_id!r}")

        project.team_id = team_id
        self._project_repo.update(project)
        return project

    def change_status(self, project_id: str, new_status: ProjectStatus) -> Project:
        """Change project status following allowed transitions.

        Raises:
            ProjectNotFoundError: project does not exist.
            InvalidStatusTransitionError: transition not allowed.
        """
        project = self._project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project not found: {project_id!r}")

        allowed = _VALID_TRANSITIONS[project.status]
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition {project.status.value!r} → {new_status.value!r}"
                + (" (team must be assigned)" if new_status == ProjectStatus.ACTIVE
                   and project.team_id is None else "")
            )
        if new_status == ProjectStatus.ACTIVE and project.team_id is None:
            raise InvalidStatusTransitionError(
                "Cannot activate project without a team assigned"
            )

        project.status = new_status
        self._project_repo.update(project)
        return project
