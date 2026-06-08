# Testing Guide — Student Project Support System

## Toolchain

| Tool | Purpose |
|---|---|
| `pytest >= 8` | Test runner |
| `pytest-cov >= 5` | Branch coverage via `--cov` |
| `pytest-mock >= 3.14` | `mocker` fixture / `MagicMock` helpers |

Install: `pip install -e ".[dev]"`

---

## TDD workflow (mandatory)

1. **Red** — write a test that describes the desired behaviour. Run it; confirm it fails.
2. **Green** — write the minimum implementation to make it pass.
3. **Refactor** — clean up without breaking tests.

Never commit production code that does not have a corresponding test written first.

---

## Test layout

```
tests/
  unit/
    models/      test_student.py, test_team.py, test_project.py,
                 test_milestone.py, test_submission.py, test_penalty.py,
                 test_queue_request.py, test_enums.py
    storage/     test_student_repo.py, test_team_repo.py, test_project_repo.py,
                 test_milestone_repo.py, test_submission_repo.py,
                 test_penalty_repo.py, test_queue_request_repo.py
    services/    test_penalty_strategies.py, test_events_observer.py,
                 test_notification.py, test_project_service.py,
                 test_milestone_service.py, test_team_service.py,
                 test_membership_service.py
  integration/
    conftest.py                        (shared fixtures, Clock helper)
    test_project_milestone_workflow.py
    test_team_queue_workflow.py
    test_membership_blocking_workflow.py
```

Target: **200+ tests** total across both layers.

---

## Unit tests

Unit tests verify a single class in isolation. All collaborators are mocked.

```python
# tests/unit/services/test_milestone_service.py
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from services.milestone_service import MilestoneService
from services.penalty_strategies import FlatPenaltyStrategy

def test_late_submit_creates_penalty_per_team_member():
    milestone_repo  = MagicMock()
    submission_repo = MagicMock()
    penalty_repo    = MagicMock()
    project_repo    = MagicMock()
    team_repo       = MagicMock()
    student_repo    = MagicMock()
    bus             = MagicMock()

    due = datetime(2025, 10, 15)
    milestone_repo.get_by_id.return_value = Milestone(
        "m1", "p1", "Sprint 1", due
    )
    project_repo.get_by_id.return_value = Project(
        "p1", "AI Project", "desc", team_id="t1", created_at=due
    )
    team_repo.get_by_id.return_value = Team("t1", "Alpha", 4, ["s1", "s2"])

    svc = MilestoneService(
        milestone_repo, submission_repo, penalty_repo,
        project_repo, team_repo, student_repo,
        FlatPenaltyStrategy(2), bus,
        clock=lambda: due + timedelta(days=3),
    )
    _, penalties = svc.submit("m1")

    assert len(penalties) == 2          # one per team member
    assert all(p.points == 6 for p in penalties)  # 3 days × 2 pts
    bus.notify_milestone_status.assert_called_once()
```

Rules:
- One `assert` per logical concept (multiple asserts for one scenario are fine).
- Never hit real storage — always inject mocks.
- Name tests `test_<method>_<scenario>_<expected_outcome>`.

---

## Integration tests

Integration tests wire real in-memory implementations together through the full stack
and verify end-to-end workflows.

```python
# tests/integration/test_project_milestone_workflow.py
from datetime import datetime, timedelta
from storage.memory.student_repo import InMemoryStudentRepository
from storage.memory.team_repo import InMemoryTeamRepository
from storage.memory.project_repo import InMemoryProjectRepository
from storage.memory.milestone_repo import InMemoryMilestoneRepository
from storage.memory.submission_repo import InMemorySubmissionRepository
from storage.memory.penalty_repo import InMemoryPenaltyRepository
from services.penalty_strategies import FlatPenaltyStrategy
from services.events import EventBus
from services.milestone_service import MilestoneService

def test_late_submission_stores_penalties():
    students    = InMemoryStudentRepository()
    teams       = InMemoryTeamRepository()
    projects    = InMemoryProjectRepository()
    milestones  = InMemoryMilestoneRepository()
    submissions = InMemorySubmissionRepository()
    penalties   = InMemoryPenaltyRepository()
    bus         = EventBus()
    due         = datetime(2025, 10, 15)

    students.add(Student("s1", "Alice", StudentRole.MEMBER))
    teams.add(Team("t1", "Alpha", 4, ["s1"]))
    projects.add(Project("p1", "Capstone", "desc", team_id="t1", created_at=due))
    milestones.add(Milestone("m1", "p1", "Sprint 1", due))

    svc = MilestoneService(
        milestones, submissions, penalties, projects, teams, students,
        FlatPenaltyStrategy(2), bus,
        clock=lambda: due + timedelta(days=4),
    )
    _, created = svc.submit("m1")
    assert len(created) == 1
    assert created[0].points == 8
```

---

## Coverage

### Run locally

```bash
pytest --cov=src --cov-branch --cov-report=term-missing
```

### Generate all report formats (CI)

```bash
pytest \
  --cov=src \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --junitxml=junit.xml
```

### Artifacts

| File | Consumer |
|---|---|
| `coverage.xml` | SonarQube / SonarCloud |
| `junit.xml` | CI test-results panel |
| `htmlcov/` | Human review |

### Target

**Branch coverage >= 85%.** The assignment minimum is 70%; the extra margin accounts for
edge-case branches exposed during integration testing.

A branch is considered covered only when both the true and false paths are exercised.
Use `# pragma: no cover` sparingly and only for unreachable defensive guards.

---

## pytest-mock patterns

```python
# Spy on a method without replacing it
def test_event_fired_on_late_submit(mocker):
    bus = EventBus()
    spy = mocker.spy(bus, "notify_milestone_status")
    ...
    spy.assert_called_once()

# Inject a controllable clock
def test_submit_on_due_date_no_penalty():
    due = datetime(2025, 10, 15)
    svc = MilestoneService(..., clock=lambda: due)
    _, penalties = svc.submit("m1")
    assert penalties == []
```

---

## What NOT to test

- `__init__.py` files (excluded from coverage via `pyproject.toml`).
- Third-party library internals.
- Pure data containers where the only logic is Python's own dataclass machinery.
