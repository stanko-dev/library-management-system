---
name: testing
description: TDD and coverage workflow. Use when writing, modifying or reviewing tests, or configuring coverage reports.
---

## TDD process (mandatory)

1. **Red** — write the failing test first. Run it; confirm it fails for the right reason.
2. **Green** — write the minimum production code to make it pass.
3. **Refactor** — clean up without breaking tests.

Never write production code that does not have a test written first.

## Unit tests

Isolate the class under test — mock every collaborator with `pytest-mock` / `MagicMock`.

```python
milestone_repo  = MagicMock()
penalty_repo    = MagicMock()
bus             = MagicMock()
svc = MilestoneService(milestone_repo, ..., penalty_repo, ..., bus, clock=lambda: fixed_dt)
_, penalties = svc.submit("m1")
bus.notify_milestone_status.assert_called_once()
```

- Name tests `test_<method>_<scenario>_<expected_outcome>`.
- Never hit real storage in unit tests.
- Inject a `clock=lambda: datetime(...)` instead of calling `datetime.now()`.

## Integration tests

Wire **real** in-memory repos and services together (no mocks). Verify end-to-end workflows.
Use the advanceable `Clock` fixture from `tests/integration/conftest.py`:

```python
clock.set(due + timedelta(days=3))   # jump to a specific moment
clock.advance(days=1)                # relative advance
```

## Coverage target

Branch coverage **>= 85%**. Both the true and false path of every branch must be exercised.

## Commands

```bash
# Quick check during development
pytest --cov=src --cov-branch --cov-report=term-missing

# Full CI report (required before merge)
pytest \
  --cov=src --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --junitxml=junit.xml
```

Artifacts: `coverage.xml` → SonarCloud, `junit.xml` → CI panel, `htmlcov/index.html` → human review.
