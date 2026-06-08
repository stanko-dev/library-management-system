from models.project import Project
from models.enums import ProjectStatus
from storage.interfaces import ProjectRepository


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self) -> None:
        self._store: dict[str, Project] = {}

    def add(self, project: Project) -> None:
        if project.id in self._store:
            raise ValueError(f"Project already exists: {project.id}")
        self._store[project.id] = project

    def get_by_id(self, project_id: str) -> Project | None:
        return self._store.get(project_id)

    def list_all(self) -> list[Project]:
        return list(self._store.values())

    def update(self, project: Project) -> None:
        if project.id not in self._store:
            raise KeyError(project.id)
        self._store[project.id] = project

    def delete(self, project_id: str) -> None:
        if project_id not in self._store:
            raise KeyError(project_id)
        del self._store[project_id]

    def find_by_team(self, team_id: str) -> list[Project]:
        return [p for p in self._store.values() if p.team_id == team_id]

    def find_by_status(self, status: ProjectStatus) -> list[Project]:
        return [p for p in self._store.values() if p.status == status]
