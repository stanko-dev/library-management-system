from models.reader import Reader
from storage.interfaces import ReaderRepository


class InMemoryReaderRepository(ReaderRepository):
    def __init__(self) -> None:
        self._store: dict[str, Reader] = {}

    def add(self, reader: Reader) -> None:
        if reader.id in self._store:
            raise ValueError(f"Reader already exists: {reader.id}")
        self._store[reader.id] = reader

    def get_by_id(self, reader_id: str) -> Reader | None:
        return self._store.get(reader_id)

    def list_all(self) -> list[Reader]:
        return list(self._store.values())

    def update(self, reader: Reader) -> None:
        if reader.id not in self._store:
            raise KeyError(reader.id)
        self._store[reader.id] = reader

    def delete(self, reader_id: str) -> None:
        if reader_id not in self._store:
            raise KeyError(reader_id)
        del self._store[reader_id]

    def find_by_name(self, name: str) -> list[Reader]:
        needle = name.lower()
        return [r for r in self._store.values() if needle in r.name.lower()]

    def find_active(self) -> list[Reader]:
        return [r for r in self._store.values() if not r.is_blocked]

    def find_blocked(self) -> list[Reader]:
        return [r for r in self._store.values() if r.is_blocked]
