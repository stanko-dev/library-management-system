# Architecture — In-Memory Student Project Support System

## Layer overview

```
models  →  storage  →  services  →  (CLI / tests)
```

Each layer depends only on the layer to its left via abstractions, never on concrete implementations.

---

## models/

**Responsibility:** pure data — no business logic, no I/O.

Contains dataclass entities:
- `Student` — id, name, role (LEADER/MEMBER), is_blocked, active_projects_count, missed_deadlines_count
- `Team` — id, name, capacity, member_ids
- `Project` — id, title, description, status (DRAFT/ACTIVE/COMPLETED/ARCHIVED), team_id, created_at
- `Milestone` — id, project_id, title, due_date, status (PENDING/SUBMITTED/LATE/MISSED), submitted_at
- `Submission` — id, milestone_id, team_id, submitted_at
- `Penalty` — id, student_id, milestone_id, points, is_resolved
- `QueueRequest` — id, student_id, team_id, created_at, expires_at, status (PENDING/FULFILLED/EXPIRED/CANCELLED)

Rules:
- All fields are typed.
- Validation (e.g. negative counts, empty id) raises `ValueError` in `__post_init__`, not a service exception.
- No imports from `storage` or `services`.

---

## storage/

**Responsibility:** data persistence — currently all in-memory via plain Python dicts.

### Sub-structure

```
storage/
  interfaces.py                  # abc.ABC repository contracts
  memory/
    student_repo.py
    team_repo.py
    project_repo.py
    milestone_repo.py
    submission_repo.py
    penalty_repo.py
    queue_request_repo.py
```

### Repository interfaces (interfaces.py)

Every repository is an `abc.ABC` with `@abstractmethod` operations:

```python
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
```

The same CRUD pattern applies to all seven repositories. Specialised query methods
(e.g. `find_pending_by_team`, `total_unresolved_by_student`, `find_overdue`) are
declared on the relevant ABCs only — Interface Segregation in practice.

### In-memory implementations

Concrete classes (e.g. `InMemoryStudentRepository(StudentRepository)`) store data in
`dict[str, Student]`. They import only from `models/`; they have no knowledge of services.

**Why ABCs decouple services from storage:**
Services receive a `StudentRepository` (the ABC) via constructor injection. The service
never calls `InMemoryStudentRepository()` directly. This means:
- The in-memory impl can be swapped for a SQL impl without touching services.
- Unit tests inject a `MagicMock` that satisfies the ABC interface.

---

## services/

**Responsibility:** all business logic — project lifecycle, milestone submissions, team
membership, penalty calculation, and student blocking.

### Key services

| Service | Depends on |
|---|---|
| `ProjectService` | `ProjectRepository`, `TeamRepository` |
| `MilestoneService` | `MilestoneRepository`, `SubmissionRepository`, `PenaltyRepository`, `ProjectRepository`, `TeamRepository`, `StudentRepository`, `PenaltyStrategy`, `DeadlineSubject` |
| `TeamService` | `TeamRepository`, `StudentRepository`, `QueueRequestRepository`, `DeadlineSubject` |
| `MembershipService` | `StudentRepository`, `PenaltyRepository` |

### Dependency Injection

All dependencies are injected through `__init__`:

```python
class MilestoneService:
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
        ...
```

A composition root (e.g. the integration-test `conftest.py`) wires concrete
implementations together and is the only place that calls `InMemory*` constructors.

---

## utils/

**Responsibility:** cross-cutting concerns that belong to no single layer.

- `exceptions.py` — domain exception hierarchy (`StudentNotFoundError`, `TeamFullError`,
  `InvalidStatusTransitionError`, `AlreadySubmittedError`, `DuplicateQueueRequestError`, …).

`utils/` imports nothing from `services/` or `storage/`.

---

## GoF Pattern locations

### Strategy — penalty calculation

```
services/penalty_strategies.py  → PenaltyStrategy(ABC)
                                → FlatPenaltyStrategy
                                → ProgressivePenaltyStrategy
                                → WeekendExemptPenaltyStrategy
                                → CappedPenaltyStrategy  (Decorator)
                                → PenaltyStrategyFactory
```

`MilestoneService` receives a `PenaltyStrategy` and calls
`strategy.calculate(due_date, submitted_date)`. Switching the penalty policy requires
only a different strategy object at the composition root, not a code change.

### Observer — milestone status and team-spot notifications

```
services/events.py        → DeadlineSubject(ABC), DeadlineObserver(ABC)
                          → EventBus (implements DeadlineSubject)
                          → MilestoneStatusChangedEvent, TeamSpotAvailableEvent
services/notification.py  → StudentNotifier (implements DeadlineObserver)
```

`MilestoneService` publishes `MilestoneStatusChangedEvent` after every status change.
`TeamService` publishes `TeamSpotAvailableEvent` after a member leaves. `StudentNotifier`
reacts by recording `Notification` objects — services have no knowledge of what happens
next (Open/Closed in action).

---

## Dependency direction summary

```
services  →  storage interfaces (ABC)  ←  storage implementations
services  →  models
services  →  utils (exceptions, events, penalty_strategies)
storage   →  models
utils     →  (nothing in src)
```

No circular imports. `models` is imported by every layer; it imports nothing.
