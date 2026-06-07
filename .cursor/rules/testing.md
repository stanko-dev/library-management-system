# Testing Guide — Library Management System

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
    models/          test_book.py, test_member.py, test_loan.py, test_fine.py
    storage/         test_book_repo.py, test_member_repo.py, ...
    services/        test_book_service.py, test_loan_service.py, ...
    utils/           test_date_utils.py, test_validators.py
  integration/
    test_borrow_flow.py
    test_return_flow.py
    test_fine_flow.py
    test_search_flow.py
    test_notification_flow.py
```

Target: **200+ tests** total across both layers.

---

## Unit tests

Unit tests verify a single class in isolation. All collaborators are mocked.

```python
# tests/unit/services/test_loan_service.py
from unittest.mock import MagicMock
from services.loan_service import LoanService

def test_borrow_decrements_available_copies():
    loan_repo    = MagicMock()
    book_repo    = MagicMock()
    member_repo  = MagicMock()
    fine_strategy = MagicMock()
    event_bus    = MagicMock()

    book = Book(isbn="123", title="X", author="Y", year=2020,
                total_copies=2, available_copies=2)
    book_repo.get_by_isbn.return_value = book
    member_repo.get_by_id.return_value = Member(member_id="m1", name="A",
                                                 email="a@b.com", active=True)

    svc = LoanService(loan_repo, book_repo, member_repo, fine_strategy, event_bus)
    svc.borrow("m1", "123")

    assert book.available_copies == 1
    book_repo.update.assert_called_once_with(book)
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
# tests/integration/test_borrow_flow.py
from storage.memory.book_repo import InMemoryBookRepository
from storage.memory.member_repo import InMemoryMemberRepository
from storage.memory.loan_repo import InMemoryLoanRepository
from services.fine_strategies import PerDayFineStrategy
from utils.events import EventBus
from services.loan_service import LoanService

def test_full_borrow_and_return_updates_availability():
    books   = InMemoryBookRepository()
    members = InMemoryMemberRepository()
    loans   = InMemoryLoanRepository()
    bus     = EventBus()
    svc     = LoanService(loans, books, members, PerDayFineStrategy(), bus)

    books.add(Book(isbn="978", title="Clean Code", author="Martin",
                   year=2008, total_copies=1, available_copies=1))
    members.add(Member(member_id="m1", name="Alice", email="a@b.com", active=True))

    loan = svc.borrow("m1", "978")
    assert books.get_by_isbn("978").available_copies == 0

    svc.return_book(loan.loan_id)
    assert books.get_by_isbn("978").available_copies == 1
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
def test_event_published_on_return(mocker):
    bus = EventBus()
    spy = mocker.spy(bus, "publish")
    ...
    spy.assert_called_once()

# Patch a module-level import
def test_uses_today(mocker):
    mocker.patch("services.loan_service.date", return_value=date(2025, 1, 1))
    ...
```

---

## What NOT to test

- `__init__.py` files (excluded from coverage via `pyproject.toml`).
- Third-party library internals.
- Pure data containers where the only logic is Python's own dataclass machinery.
