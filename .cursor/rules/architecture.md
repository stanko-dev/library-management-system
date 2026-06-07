# Architecture — In-Memory Library Management System

## Layer overview

```
models  →  storage  →  services  →  (CLI / tests)
```

Each layer depends only on the layer to its left via abstractions, never on concrete implementations.

---

## models/

**Responsibility:** pure data — no business logic, no I/O.

Contains dataclass or plain-class entities:
- `Book` — isbn, title, author, year, total_copies, available_copies
- `Member` — member_id, name, email, active
- `Loan` — loan_id, book_isbn, member_id, loan_date, due_date, return_date
- `Fine` — fine_id, loan_id, amount, paid

Rules:
- All fields are typed.
- Validation (e.g. negative copies) raises `ValueError`, not a service exception.
- No imports from `storage` or `services`.

---

## storage/

**Responsibility:** data persistence — currently all in-memory via plain Python dicts/lists.

### Sub-structure

```
storage/
  interfaces.py   # abc.ABC repository contracts
  memory/
    book_repo.py
    member_repo.py
    loan_repo.py
    fine_repo.py
```

### Repository interfaces (interfaces.py)

Every repository is an `abc.ABC` with `@abstractmethod` operations:

```python
class BookRepository(ABC):
    @abstractmethod
    def add(self, book: Book) -> None: ...
    @abstractmethod
    def get_by_isbn(self, isbn: str) -> Book | None: ...
    @abstractmethod
    def list_all(self) -> list[Book]: ...
    @abstractmethod
    def update(self, book: Book) -> None: ...
    @abstractmethod
    def delete(self, isbn: str) -> None: ...
```

The same pattern applies to `MemberRepository`, `LoanRepository`, and `FineRepository`.

### In-memory implementations

Concrete classes (e.g. `InMemoryBookRepository(BookRepository)`) store data in `dict[str, Book]`.
They import only from `models/`; they have no knowledge of services.

**Why ABCs decouple services from storage:**
Services receive a `BookRepository` (the ABC) via constructor injection. The service never calls
`InMemoryBookRepository()` directly. This means:
- The in-memory impl can be swapped for a SQL impl without touching services.
- Unit tests inject a `MagicMock` that satisfies the ABC interface.

---

## services/

**Responsibility:** all business logic — borrowing, returning, searching, fine calculation.

### Key services

| Service | Depends on |
|---|---|
| `BookService` | `BookRepository` |
| `MemberService` | `MemberRepository` |
| `LoanService` | `LoanRepository`, `BookRepository`, `MemberRepository`, `FineStrategy`, `EventBus` |
| `FineService` | `FineRepository`, `FineStrategy` |
| `SearchService` | `BookRepository`, `MemberRepository` |

### Dependency Injection

All dependencies are injected through `__init__`:

```python
class LoanService:
    def __init__(
        self,
        loan_repo: LoanRepository,
        book_repo: BookRepository,
        member_repo: MemberRepository,
        fine_strategy: FineStrategy,
        event_bus: EventBus,
    ) -> None:
        self._loan_repo = loan_repo
        ...
```

A factory or composition root (e.g. `utils/container.py`) wires concrete implementations
together and is the only place that calls `InMemory*` constructors.

---

## utils/

**Responsibility:** cross-cutting concerns that belong to no single layer.

- `date_utils.py` — date arithmetic helpers (due-date calculation, days-overdue).
- `validators.py` — shared string/format validators (ISBN format, email format).
- `container.py` — composition root; builds the full object graph for production use.
- `exceptions.py` — domain exception hierarchy (`BookNotFoundError`, `MemberNotActiveError`, …).

---

## GoF Pattern locations

### Strategy — fine calculation

```
storage/interfaces.py        → FineStrategy(ABC)
src/services/fine_strategies.py → PerDayFineStrategy, TieredFineStrategy, ...
```

`LoanService` receives a `FineStrategy` and calls `strategy.calculate(days_overdue)`.
Switching the fine policy requires only a different strategy object, not a code change.

### Observer — book availability notification

```
utils/events.py   → EventBus, BookAvailableEvent
services/         → LoanService publishes BookAvailableEvent on book return
                  → NotificationService subscribes and records notifications
```

`LoanService` holds an `EventBus` reference. On `return_book`, it publishes
`BookAvailableEvent(isbn)`. `NotificationService` (or any subscriber) reacts without
`LoanService` knowing what happens next — Open/Closed in action.

---

## Dependency direction summary

```
services  →  storage interfaces (ABC)  ←  storage implementations
services  →  models
services  →  utils (exceptions, events)
storage   →  models
utils     →  (nothing in src)
```

No circular imports. `models` is imported by every layer; it imports nothing.
