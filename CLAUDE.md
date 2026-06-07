# Library Management System — Claude Code Context

## Project summary

An **in-memory** Library Management System written in **Python 3.12**.
No databases, no network, no file I/O. All persistence lives in plain Python dicts/lists.

## Directory layout

```
src/
  models/    — pure data entities (Book, Member, Loan, Fine)
  storage/   — ABC repository interfaces + InMemory implementations
  services/  — business logic (BookService, LoanService, FineService, …)
  utils/     — shared helpers, domain exceptions, EventBus, DI container
tests/
  unit/        — isolated tests with mocks
  integration/ — full-stack tests using real in-memory repos
docs/diagrams/ — UML / architecture diagrams
```

## Hard constraints

- **No concrete repo/strategy without its ABC first.** Define the `abc.ABC` interface before writing any implementation.
- **TDD only.** Write the failing test, then the implementation — never the other way around.
- **No external I/O.** No databases, HTTP calls, file reads, or third-party APIs anywhere in `src/`.
- **Constructor injection.** All dependencies are passed via `__init__`. No `import`-time instantiation of collaborators.

## Architecture

Dependency direction (one way only):

```
services  →  storage interfaces (ABC)  ←  storage implementations
services  →  models
services  →  utils
storage   →  models
```

`models/` imports nothing from this project. `utils/` imports nothing from `services/` or `storage/`.

## Required design patterns

| Pattern | Where |
|---|---|
| Strategy | `FineStrategy` ABC + concrete strategies; injected into `LoanService` |
| Observer | `EventBus` in `utils/events.py`; `LoanService` publishes `BookAvailableEvent` on return |

## Quality targets

| Metric | Target |
|---|---|
| Branch coverage | >= 85% |
| Total tests | >= 200 |
| Bugs / vulnerabilities | 0 |
| Maintainability | A or B |

## Test toolchain

```
pytest >= 8
pytest-cov >= 5
pytest-mock >= 3.14
```

Run all tests with coverage:

```bash
pytest --cov=src --cov-branch --cov-report=term-missing
```

Full CI report (produces `coverage.xml`, `junit.xml`, `htmlcov/`):

```bash
pytest \
  --cov=src --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --junitxml=junit.xml
```

## Naming conventions

- Test functions: `test_<method>_<scenario>_<expected_outcome>`
- Repository interface: `BookRepository` (ABC in `storage/interfaces.py`)
- In-memory impl: `InMemoryBookRepository` (in `storage/memory/book_repo.py`)
- Domain exceptions: defined in `utils/exceptions.py`, e.g. `BookNotFoundError`

## SOLID reminders

- **S** — each class has one reason to change.
- **O** — extend via new strategy/observer implementations, not `if` chains.
- **L** — every in-memory repo must be substitutable for its ABC.
- **I** — keep repository ABCs focused; don't bloat with unused methods.
- **D** — services depend on ABC interfaces, never on concrete classes.

## See also

- `.cursorrules` — condensed hard rules for AI agents.
- `.cursor/rules/architecture.md` — full layer and pattern description.
- `.cursor/rules/testing.md` / `.cursor/rules/testing_strategy.md` — TDD and coverage guide.
