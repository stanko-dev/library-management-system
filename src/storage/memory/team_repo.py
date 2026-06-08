from models.team import Team
from storage.interfaces import TeamRepository


class InMemoryTeamRepository(TeamRepository):
    def __init__(self) -> None:
        self._store: dict[str, Team] = {}

    def add(self, team: Team) -> None:
        if team.id in self._store:
            raise ValueError(f"Team already exists: {team.id}")
        self._store[team.id] = team

    def get_by_id(self, team_id: str) -> Team | None:
        return self._store.get(team_id)

    def list_all(self) -> list[Team]:
        return list(self._store.values())

    def update(self, team: Team) -> None:
        if team.id not in self._store:
            raise KeyError(team.id)
        self._store[team.id] = team

    def delete(self, team_id: str) -> None:
        if team_id not in self._store:
            raise KeyError(team_id)
        del self._store[team_id]

    def find_by_name(self, name: str) -> list[Team]:
        needle = name.lower()
        return [t for t in self._store.values() if needle in t.name.lower()]
