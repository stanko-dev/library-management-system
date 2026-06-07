# Library Management System

<!-- ────────────────────────────────────────────────────────────────────────────
  BADGE INSTRUCTIONS
  ─────────────────
  Replace the three placeholder URLs below before publishing:

  1. CI badge
     GitHub → Actions tab → select the "CI" workflow → copy the badge Markdown
     from the "…" menu (top-right of the workflow page).
     Format: https://github.com/<OWNER>/<REPO>/actions/workflows/ci-pipeline.yml/badge.svg

  2. SonarCloud Quality Gate badge
     SonarCloud → your project → Project Information (bottom-left) →
     "Get project badges" → select "Quality Gate Status" → copy the Markdown.

  3. SonarCloud Coverage badge
     Same dialog as above → select "Coverage" → copy the Markdown.
──────────────────────────────────────────────────────────────────────────── -->

[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci-pipeline.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci-pipeline.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=stanko-dev_library-management-system&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=stanko-dev_library-management-system)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=stanko-dev_library-management-system&metric=coverage)](https://sonarcloud.io/summary/new_code?id=stanko-dev_library-management-system)

---

## Overview

An **in-memory Library Management System** written in Python 3.12. The system manages
book loans, reservations, reader accounts, and overdue fines without an external
database — all state lives in plain Python `dict`s for the lifetime of the process.

**Quality targets met:**

| Metric | Target | Achieved |
|---|---|---|
| Branch coverage | ≥ 85% | 100% |
| Tests | ≥ 200 | 703 |
| Bugs / vulnerabilities | 0 | 0 |
| Maintainability | A or B | A |

---

## Architecture

The codebase is split into four layers. Dependencies flow strictly downward; no layer
imports from a layer above it.

```
┌───────────────────────────────────────────────────┐
│                   services/                        │  Business logic
│  LoanService · ReturnService · ReservationService  │  (all deps injected)
│  MembershipService                                 │
└──────────────────┬────────────────────────────────┘
                   │ depends on ABCs only
┌──────────────────▼────────────────────────────────┐
│               storage/interfaces.py                │  Repository ABCs
│  BookRepository · ReaderRepository · LoanRepository│  (abc.ABC)
│  ReservationRepository · FineRepository            │
└──────────────────▲────────────────────────────────┘
                   │ implemented by
┌──────────────────┴────────────────────────────────┐
│             storage/memory/                        │  In-memory impls
│  InMemoryBookRepository · InMemoryReaderRepository │  (dict-backed)
│  InMemoryLoanRepository · …                        │
└───────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────┐
│                   models/                          │  Pure data
│  Book · Reader · Loan · Reservation · Fine         │  (dataclasses, no I/O)
└───────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────┐
│                   utils/                           │  Cross-cutting
│  exceptions.py                                     │  (no service imports)
└───────────────────────────────────────────────────┘
```

**Key principles applied:**

- **Dependency Inversion** — every service receives repository ABCs via constructor
  injection; it never calls `InMemory*` constructors directly.
- **Single Responsibility** — each service owns exactly one domain workflow.
- **Open/Closed** — new fine policies and new event observers are added by implementing
  an interface, not by editing existing classes.
- **Liskov Substitution** — every `InMemory*Repository` is a drop-in substitute for
  its ABC; the test suite exercises both with and without mocks.
- **Interface Segregation** — five focused repository ABCs rather than one monolithic
  data-access interface.

---

## Design Patterns

### Strategy — Fine Calculation

**Where:** `src/services/fine_strategies.py`

`ReturnService` receives a `FineStrategy` instance via its constructor. It calls
`strategy.calculate(due_date, return_date)` without knowing which algorithm is active.
Four concrete strategies ship out of the box:

| Strategy | Algorithm |
|---|---|
| `FlatFineStrategy` | `overdue_days × daily_rate` |
| `ProgressiveFineStrategy` | Day *n* costs `base_rate + (n−1) × increment`; total capped at `cap` |
| `WeekendExemptStrategy` | Weekdays only (Mon–Fri) in the overdue window × `daily_rate` |
| `CappedFineStrategy` | Decorator — wraps any inner strategy and clamps its result to a ceiling |

**Rationale:** Switching the fine policy for a deployment requires only passing a
different object at the composition root; no service code changes and no conditional
chains (`if policy == "flat": …`).

### Observer — Book-Availability Notifications

**Where:** `src/services/events.py` (bus), `src/services/notification.py` (observer)

`ReturnService` holds a reference to `BookAvailabilitySubject` (an ABC). After
recording a return it calls `event_bus.notify(BookAvailableEvent(book_id))`. Any
number of observers subscribed to the bus receive the event.

`ReaderNotifier` is the concrete observer: it looks up the highest-priority active
reservation for the returned book and records a `Notification` for that reader.

**Rationale:** `ReturnService` has no knowledge of notifications, reservation queues,
or email sending. Adding a new reaction to a book return (e.g., updating a search
index) means implementing `BookAvailabilityObserver` and subscribing it — zero changes
to existing code.

---

## Business Rules

### Loan Limits

| Membership tier | Maximum simultaneous active loans |
|---|---|
| Standard | 3 |
| Premium | 5 |

Default loan period: **14 days**.

### Fine Calculation

A fine is created only when `return_date > due_date`. The exact amount depends on the
configured `FineStrategy` (see Design Patterns above). A fine is stored as an unpaid
record on the reader's account.

### Reservation Queue Priority

When a copy becomes available the reservation queue is sorted by:

1. **Membership tier** — Premium readers (rank 0) are served before Standard readers (rank 1).
2. **Arrival time** — Within the same tier, the reader who reserved earliest wins (FIFO).

Reservations expire automatically **3 days** after they are created.

### Reader Blocking

A reader is **blocked** (cannot borrow or reserve) when either condition holds:

- Total unpaid fines ≥ **$10.00**, **or**
- Overdue-return count ≥ **3**

`MembershipService.evaluate()` recomputes the blocking status atomically. A librarian
can also force-block or force-unblock a reader regardless of thresholds via
`MembershipService.block()` / `MembershipService.unblock()`.

---

## Running Tests Locally

```bash
# 1. Create and activate a virtual environment (one-time setup)
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install the project in development mode
pip install -e ".[dev]"

# 3. Run all tests with branch coverage
pytest --cov=src --cov-branch --cov-report=term-missing

# 4. Full CI report (produces coverage.xml, junit.xml, htmlcov/)
pytest \
  --cov=src --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --junitxml=junit.xml
```

The test suite is split into two directories:

| Directory | Purpose |
|---|---|
| `tests/unit/` | Each class tested in isolation; all collaborators are mocked. |
| `tests/integration/` | Real in-memory repositories wired together; end-to-end workflows. |

---

## Coverage Report and CI Artifacts

### HTML report (local)

After running the full CI report command above, open `htmlcov/index.html` in any
browser. Line- and branch-level coverage is highlighted inline.

### GitHub Actions artifacts

Every CI run uploads a `test-reports` artifact containing:

| File | Consumer |
|---|---|
| `coverage.xml` | SonarCloud — branch coverage ingested automatically |
| `junit.xml` | GitHub Actions test-results panel |
| `htmlcov/` | Human review — download the artifact and open `index.html` |

To download: **Actions tab → select a run → Artifacts → test-reports**.

---

## Diagrams

All diagrams live in `docs/diagrams/` as GitHub-renderable Mermaid fenced code blocks.
Open any `.md` file directly on GitHub to see the rendered diagram.

| File | Diagram type | What it shows |
|---|---|---|
| `use-case.md` | Use Case | Actors (Reader, Librarian) and the 6 use cases with «include» relationships |
| `domain-model.md` | Class (domain model) | Entities, enumerations, and their multiplicities |
| `class-diagram.md` | Class (full) | All layers: models, repository ABCs, in-memory impls, Strategy hierarchy, Observer hierarchy, services, and dependency arrows |

For a narrative description of each use case (including main and alternative flows),
see [`docs/requirements.md`](docs/requirements.md).
