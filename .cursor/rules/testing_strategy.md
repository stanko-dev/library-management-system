# Testing Strategy — Student Project Support System

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

## What to test in each layer

### models/

Cover every validation branch in `__post_init__`:
- Empty or whitespace `id`, `title`, `name` → `ValueError`.
- Out-of-range numeric fields (`capacity < 1`, `points <= 0`, negative counts).
- `expires_at <= created_at` on `QueueRequest`.
- Auto-set defaults (`Project.created_at` auto-set when `None`).
- Property methods (`Team.is_full`, `Team.available_spots`).

### storage/ (in-memory repos)

For every repository:
- `add` stores and `get_by_id` retrieves the same object.
- `add` on a duplicate id raises `ValueError`.
- `update` on a missing id raises `KeyError`.
- `delete` on a missing id raises `KeyError`.
- `list_all` reflects current state after add/delete.
- All domain-specific query methods (`find_pending_by_team`, `total_unresolved_by_student`,
  `find_overdue`, etc.) return correct subsets.

Use `pytest.mark.parametrize` to run CRUD assertions across all seven repos with a
single parametrized test.

### services/ (unit tests with mocks)

Cover every branch in each service method:

**ProjectService:**
- `create_project` with and without a team_id; unknown team_id raises `TeamNotFoundError`.
- `assign_team` — happy path; ARCHIVED project raises `InvalidStatusTransitionError`.
- `change_status` — all valid transitions; invalid transition raises; DRAFT→ACTIVE without
  team raises.

**MilestoneService:**
- `submit` on time → `SUBMITTED`, no penalties.
- `submit` late → `LATE`, one penalty per member, `missed_deadlines_count` incremented.
- `submit` when team not found / no team assigned → no penalties, submission still created.
- `submit` on already-submitted milestone → `AlreadySubmittedError`.
- `mark_missed` → `MISSED`, penalties created, event fired.
- Event bus `notify_milestone_status` called exactly once per submit/mark-missed.

**TeamService:**
- `join_or_queue` with space → student added, `active_projects_count` incremented.
- `join_or_queue` full team → `QueueRequest` created.
- `join_or_queue` blocked student → `StudentBlockedError`.
- `join_or_queue` duplicate queue request → `DuplicateQueueRequestError`.
- `leave_team` → member removed, count decremented (floor 0), `TeamSpotAvailableEvent` fired.
- `expire_old` → only requests past `expires_at` are set to `EXPIRED`.
- `get_next_in_queue` → respects priority (lower `active_projects_count` first, then FIFO).

**MembershipService:**
- `evaluate` → blocks when points ≥ threshold OR missed deadlines ≥ threshold.
- `evaluate` → unblocks when both conditions clear.
- `block` / `unblock` → force-override regardless of thresholds.
- All three methods raise `StudentNotFoundError` for unknown student.

**PenaltyStrategy:**
- Each strategy: 0 days overdue → 0 points.
- Each strategy: positive overdue → correct formula result.
- `ProgressivePenaltyStrategy`: cap is respected.
- `CappedPenaltyStrategy`: delegates to inner strategy, then clamps.
- `WeekendExemptPenaltyStrategy`: Saturday and Sunday not counted.
- `PenaltyStrategyFactory.from_name`: known names return correct type; unknown raises.

**Observer / EventBus:**
- Subscribe is idempotent (second subscribe of same observer has no effect).
- Unsubscribe of unregistered observer raises `ValueError`.
- Notify dispatches to a snapshot — observer may unsubscribe mid-dispatch without error.
- `StudentNotifier.on_milestone_status_changed` records notification for each team member.
- `StudentNotifier.on_team_spot_available` records notification for highest-priority
  queued student only.

### integration/

Wire real repos + services (no mocks). Cover the three end-to-end scenarios:

1. **Late submission → penalty → resolve → unblock**
   - Project created, team assigned, milestone submitted late.
   - Penalties stored; `evaluate()` blocks student.
   - Penalties resolved; `evaluate()` unblocks student.

2. **Full team → priority queue → leave → notify**
   - Two students with different `active_projects_count` queue for a full team.
   - A member leaves; the student with fewer active projects is notified, not the
     one who queued first.

3. **Missed deadlines → blocked → join rejected → unblocked → join succeeds**
   - Student accumulates `missed_deadlines_count` via late submissions.
   - `evaluate()` blocks; `join_or_queue` raises `StudentBlockedError`.
   - `unblock()` called; `join_or_queue` succeeds.

---

## Parametrize for breadth

```python
@pytest.mark.parametrize("days_late,expected_points", [
    (0, 0),
    (1, 2),
    (3, 6),
    (7, 14),
])
def test_flat_strategy_various_overdue(days_late, expected_points):
    strategy = FlatPenaltyStrategy(points_per_day=2)
    due = date(2025, 10, 15)
    result = strategy.calculate(due, due + timedelta(days=days_late))
    assert result == expected_points
```

Use parametrize wherever a method has a clear input→output table (strategy formulas,
validation edge cases, status transitions).

---

## Clock injection pattern

Never call `datetime.now()` directly in tests. All services accept an injectable clock:

```python
# Freeze time at due date (on-time submission)
svc = MilestoneService(..., clock=lambda: due)

# Advance time (late submission)
svc = MilestoneService(..., clock=lambda: due + timedelta(days=3))
```

For integration tests, use the advanceable `Clock` helper from `tests/integration/conftest.py`:

```python
clock.set(due + timedelta(days=5))   # jump to specific instant
clock.advance(days=2)                # relative advance
```

---

## Coverage target

**Branch coverage >= 85%.** Every `if` / `else` / `elif`, every `or` / `and` short-circuit,
and every loop body must be exercised by at least one test.

Run `pytest --cov=src --cov-branch --cov-report=term-missing` and inspect the
`Missing` column. Add targeted tests for any uncovered branch before merging.

---

## What NOT to test

- `__init__.py` files (excluded from coverage via `pyproject.toml`).
- Third-party library internals.
- Pure data containers where the only logic is Python's own dataclass machinery.
