# Student Project Support System

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

[![CI](https://github.com/stanko-dev/library-management-system/actions/workflows/ci-pipeline.yml/badge.svg)](https://github.com/stanko-dev/library-management-system/actions/workflows/ci-pipeline.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=stanko-dev_library-management-system&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=stanko-dev_library-management-system)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=stanko-dev_library-management-system&metric=coverage)](https://sonarcloud.io/summary/new_code?id=stanko-dev_library-management-system)

---

## Overview

An **in-memory Student Project Support System** written in Python 3.12. The system
manages student projects, team membership, milestone submissions, and penalty enforcement
without an external database — all state lives in plain Python `dict`s for the lifetime
of the process.

**Quality targets met:**

| Metric | Target | Achieved |
|---|---|---|
| Branch coverage | ≥ 85% | 100% |
| Tests | ≥ 200 | 541 |
| Bugs / vulnerabilities | 0 | 0 |
| Maintainability | A or B | A |

---

## Architecture

The codebase is split into four layers. Dependencies flow strictly downward; no layer
imports from a layer above it.

```
┌────────────────────────────────────────────────────────────┐
│                       services/                             │  Business logic
│  ProjectService · MilestoneService · TeamService            │  (all deps injected)
│  MembershipService                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ depends on ABCs only
┌──────────────────────▼──────────────────────────────────────┐
│               storage/interfaces.py                          │  Repository ABCs
│  StudentRepository · TeamRepository · ProjectRepository      │  (abc.ABC)
│  MilestoneRepository · SubmissionRepository                  │
│  PenaltyRepository · QueueRequestRepository                  │
└──────────────────────▲──────────────────────────────────────┘
                       │ implemented by
┌──────────────────────┴──────────────────────────────────────┐
│             storage/memory/                                  │  In-memory impls
│  InMemoryStudentRepository · InMemoryTeamRepository          │  (dict-backed)
│  InMemoryProjectRepository · InMemoryMilestoneRepository     │
│  InMemorySubmissionRepository · InMemoryPenaltyRepository    │
│  InMemoryQueueRequestRepository                              │
└────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────┐
│                     models/                                 │  Pure data
│  Student · Team · Project · Milestone                       │  (dataclasses, no I/O)
│  Submission · Penalty · QueueRequest                        │
└────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────┐
│                     utils/                                  │  Cross-cutting
│  exceptions.py                                              │  (no service imports)
└────────────────────────────────────────────────────────────┘
```

**Key principles applied:**

- **Dependency Inversion** — every service receives repository ABCs via constructor
  injection; it never calls `InMemory*` constructors directly.
- **Single Responsibility** — each service owns exactly one domain workflow.
- **Open/Closed** — new penalty strategies and new event observers are added by
  implementing an interface, not by editing existing classes.
- **Liskov Substitution** — every `InMemory*Repository` is a drop-in substitute for
  its ABC; the test suite exercises both with and without mocks.
- **Interface Segregation** — seven focused repository ABCs rather than one monolithic
  data-access interface.

---

## Design Patterns

### Strategy — Penalty Calculation

**Where:** `src/services/penalty_strategies.py`

`MilestoneService` receives a `PenaltyStrategy` instance via its constructor. It calls
`strategy.calculate(due_date, submitted_date)` without knowing which algorithm is active.
Four concrete strategies ship out of the box:

| Strategy | Algorithm |
|---|---|
| `FlatPenaltyStrategy` | `overdue_days × points_per_day` |
| `ProgressivePenaltyStrategy` | Day *n* costs `base_points + (n−1) × increment`; total capped at `cap` |
| `WeekendExemptPenaltyStrategy` | Weekdays only (Mon–Fri) in the overdue window × `points_per_day` |
| `CappedPenaltyStrategy` | Decorator — wraps any inner strategy and clamps its result to a ceiling |

**Rationale:** Switching the penalty policy for a course requires only passing a
different object at the composition root; no service code changes and no conditional
chains (`if policy == "flat": …`).

### Observer — Milestone Status and Team-Spot Notifications

**Where:** `src/services/events.py` (bus), `src/services/notification.py` (observer)

`MilestoneService` and `TeamService` both hold a reference to `DeadlineSubject` (an ABC).

- After recording a submission or marking a milestone missed, `MilestoneService` calls
  `event_bus.notify_milestone_status(MilestoneStatusChangedEvent(...))`.
- After a member leaves a team, `TeamService` calls
  `event_bus.notify_team_spot(TeamSpotAvailableEvent(...))`.

`StudentNotifier` is the concrete observer:
- On a `MilestoneStatusChangedEvent`: looks up all team members of the affected project
  and records a `Notification` for each.
- On a `TeamSpotAvailableEvent`: finds the highest-priority pending queue request for the
  team (fewest active projects first, then FIFO) and records a `Notification` for that
  student.

**Rationale:** `MilestoneService` and `TeamService` have no knowledge of notifications,
queue lookups, or messaging. Adding a new reaction to a milestone change (e.g., sending
an email) means implementing `DeadlineObserver` and subscribing it — zero changes to
existing code.

---

## Business Rules

### Student Blocking

A student is **blocked** (cannot join teams) when either condition holds (thresholds are
configurable at the composition root; integration tests use 10 points and 3 deadlines):

- Total **unresolved penalty points** ≥ `max_unresolved_points`, **or**
- **Missed deadlines count** ≥ `max_missed_deadlines`

`MembershipService.evaluate()` recomputes the blocking status atomically. A coordinator
can also force-block or force-unblock a student regardless of thresholds via
`MembershipService.block()` / `MembershipService.unblock()`.

### Team-Join Priority Queue

When a team is full, join requests are queued. When a spot opens up, the student with
the **lowest `active_projects_count`** is notified first. Within the same count, the
student who queued **earliest** wins (FIFO). Queue requests expire automatically after
**7 days** (configurable via `TeamService(expiry_days=...)`).

### Project Status Transitions

| From | Allowed transitions |
|---|---|
| `DRAFT` | `ACTIVE` (requires a team to be assigned first), `ARCHIVED` |
| `ACTIVE` | `COMPLETED`, `ARCHIVED` |
| `COMPLETED` | `ARCHIVED` |
| `ARCHIVED` | *(terminal — no further transitions)* |

### Late Submission Penalties

One `Penalty` record is created **per team member** when a milestone is submitted after
its due date or explicitly marked as MISSED. The point value is determined by the
configured `PenaltyStrategy`. On-time submissions produce no penalty records.

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
| `tests/unit/` | Each class tested in isolation; all collaborators are mocked via `pytest-mock`. |
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
| `use-case.md` | Use Case | Actors (Student, Coordinator) and the 6 use cases with «include» relationships |
| `domain-model.md` | Class (domain model) | Entities, enumerations, and their multiplicities |
| `class-diagram.md` | Class (full) | All layers: models, repository ABCs, in-memory impls, Strategy hierarchy, Observer hierarchy, services, and dependency arrows |

For a narrative description of each use case (including main and alternative flows),
see [`docs/requirements.md`](docs/requirements.md).
