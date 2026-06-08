# Requirements — Student Project Support System

## 1. Problem Statement

A university needs software to manage the lifecycle of student projects: defining project
scopes, assigning teams, tracking milestone submissions, and enforcing fairness when
students compete for limited team spots. All state is held in memory for the duration of
the process; no external database is required.

The system must enforce project rules consistently, calculate late-submission penalties
using pluggable algorithms, and maintain a fair-but-priority-aware queue when multiple
students want to join a full team.

### 1.1 Non-Trivial Logic

#### Penalty Calculation

Penalty points are computed at submission time (or when a milestone is explicitly marked
missed) by a **PenaltyStrategy** selected at system configuration. Four strategies are
available:

| Strategy | Formula | Notes |
|---|---|---|
| **Flat** | `overdue_days × points_per_day` | Simple per-day penalty; no cap. |
| **Progressive** | Day *n* costs `base_points + (n−1) × increment`; total = Σ of all day costs, then `min(total, cap)` | Escalating penalty with an absolute ceiling. |
| **Weekend-Exempt** | Count only weekdays (Mon–Fri) in the overdue window; multiply by `points_per_day` | Students are not penalised for Saturdays and Sundays. |
| **Capped (Decorator)** | Delegates to any inner strategy, then applies `min(result, cap)` | Adds a hard cap to an existing strategy without modifying it. |

No penalty is created when the submission date is on or before the due date.
One penalty record is created **per team member** for each late or missed milestone.

#### Team-Join Priority Queue

When a team is full, a join request becomes a `QueueRequest`. When a spot opens up
(a member leaves), the student with the **highest priority** is notified first.
Priority is determined by a two-level sort key:

1. **Fewest active projects** — the student with the lowest `active_projects_count` is
   served first (encourages work-load balance across teams).
2. **Arrival time** — within the same active-project count, the student who queued
   earliest (`created_at` ascending) is served first (FIFO tiebreak).

Queue requests expire automatically after a configurable number of days (default: 7).

---

## 2. Actors

### Student

A registered university participant who can submit milestones on behalf of their team
and request to join project teams.

- A Student who is **blocked** cannot request to join any team until the block is lifted.
- A Student holds a `role` of either **LEADER** or **MEMBER**; both roles have the same
  system-level capabilities in this version.

### Coordinator

Academic staff responsible for creating and managing projects, assigning teams to
projects, applying penalties for missed milestones, and managing student standing
(blocking or unblocking accounts).

---

## 3. Use Cases

### UC-1 Create Project

**Actors:** Coordinator  
**Goal:** Define a new project that teams can subsequently be assigned to.

#### Main Flow

1. The Coordinator submits a project `title`, `description`, and optionally a `team_id`.
2. If `team_id` is provided, the system verifies the team exists.
3. The system creates a `Project` record with `status = DRAFT` and `created_at = now`.
4. The system returns the new `Project` to the caller.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | `team_id` provided but team not found | `TeamNotFoundError` raised; no project is created. |

---

### UC-2 Assign Team

**Actors:** Coordinator  
**Goal:** Link an existing team to a project so the project can be activated.

#### Main Flow

1. The Coordinator submits `project_id` and `team_id`.
2. The system looks up the project.
3. The system verifies the project is not ARCHIVED.
4. The system looks up the team.
5. The system sets `project.team_id = team_id` and persists the change.
6. The system returns the updated `Project`.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Project ID not found | `ProjectNotFoundError` raised; no state changes. |
| 3 | Project status is ARCHIVED | `InvalidStatusTransitionError` raised; no state changes. |
| 4 | Team ID not found | `TeamNotFoundError` raised; no state changes. |

---

### UC-3 Submit Milestone

**Actors:** Student  
**Goal:** Record the submission of a milestone; apply penalties if the submission is late.

#### Main Flow

1. The Student submits the `milestone_id`.
2. The system looks up the milestone and verifies it has not already been submitted.
3. The system records `submitted_at = now`.
4. The system calls `penalty_strategy.calculate(due_date.date(), now.date())`.
5. If the result is 0 (on time): the system sets `milestone.status = SUBMITTED`.
6. If the result is > 0 (late): the system sets `milestone.status = LATE`, creates one
   `Penalty` record per team member with the calculated points, and increments each
   team member's `missed_deadlines_count` by 1.
7. The system creates a `Submission` record and stores it.
8. The system fires a `MilestoneStatusChangedEvent`; the subscribed `StudentNotifier`
   records a `Notification` for each team member of the affected project.
9. The system returns the `Submission` and the list of `Penalty` records
   (empty list if on time).

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Milestone ID not found | `MilestoneNotFoundError` raised; no state changes. |
| 2 | Milestone status is already SUBMITTED or LATE | `AlreadySubmittedError` raised; no state changes. |
| 6 | Project has no team assigned (`team_id` is None) | No penalties are created; submission is still recorded. |
| 6 | Team not found in repository | No penalties are created; submission is still recorded. |
| 6 | A team member ID is not found in the student repository | Penalty is still created; `missed_deadlines_count` increment is skipped for that member. |

---

### UC-4 Request to Join Team

**Actors:** Student  
**Goal:** Join a project team directly, or queue for a spot if the team is full.

#### Main Flow

1. The Student submits `student_id` and `team_id`.
2. The system verifies the student exists and is not blocked.
3. The system looks up the team.
4. **If the team has an available spot:**
   a. The system appends `student_id` to `team.member_ids`.
   b. The system increments `student.active_projects_count` by 1.
   c. The system returns the updated `Team`.
5. **If the team is full:**
   a. The system checks there is no existing PENDING queue request for this student
      and team combination.
   b. The system creates a `QueueRequest` with `created_at = now` and
      `expires_at = now + expiry_days`.
   c. The system returns the new `QueueRequest`.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Student ID not found | `StudentNotFoundError` raised; no state changes. |
| 2 | Student is blocked | `StudentBlockedError` raised; no state changes. |
| 3 | Team ID not found | `TeamNotFoundError` raised; no state changes. |
| 5a | Student already has a PENDING queue request for this team | `DuplicateQueueRequestError` raised; no state changes. |

---

### UC-5 Apply Penalty

**Actors:** Coordinator  
**Goal:** Mark an overdue milestone as MISSED and create penalty records for all team members.

#### Main Flow

1. The Coordinator submits the `milestone_id`.
2. The system looks up the milestone.
3. The system sets `milestone.status = MISSED`.
4. The system calls `penalty_strategy.calculate(due_date.date(), now.date())` to
   determine the point value.
5. The system creates one `Penalty` record per team member and stores them.
6. The system fires a `MilestoneStatusChangedEvent`.
7. The system returns the list of `Penalty` records created.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Milestone ID not found | `MilestoneNotFoundError` raised; no state changes. |
| 4–5 | Project has no team assigned or team not found in repository | No penalties are created; milestone status is still updated to MISSED. |

---

### UC-6 Block Student

**Actors:** Coordinator  
**Goal:** Restrict or restore a student's ability to join teams.

#### Main Flow — Automated Evaluation

1. The Coordinator (or the system on a scheduled basis) calls
   `MembershipService.evaluate(student_id)`.
2. The system retrieves the student.
3. The system sums all unresolved penalty points for the student via
   `penalty_repo.total_unresolved_by_student(student_id)`.
4. The system applies the block condition:
   - **Block** if `total_unresolved_points ≥ max_unresolved_points` OR
     `student.missed_deadlines_count ≥ max_missed_deadlines`.
   - **Unblock** if neither condition holds.
5. The system persists the updated `student.is_blocked` flag.
6. The service returns `True` if the student ended up blocked, `False` otherwise.

#### Alternative Flow — Force Block

1. The Coordinator calls `MembershipService.block(student_id)`.
2. The system retrieves the student.
3. The system sets `student.is_blocked = True` regardless of thresholds.
4. The system persists the change.

#### Alternative Flow — Force Unblock

1. The Coordinator calls `MembershipService.unblock(student_id)`.
2. The system retrieves the student.
3. The system sets `student.is_blocked = False` regardless of thresholds.
4. The system persists the change.

#### Alternative Flows (all sub-cases)

| Step | Condition | Outcome |
|---|---|---|
| 2 (any flow) | Student ID not found | `StudentNotFoundError` raised; no state changes. |
| 6 | Penalties resolved so thresholds are no longer exceeded | Student is automatically unblocked on the next `evaluate()` call. |
