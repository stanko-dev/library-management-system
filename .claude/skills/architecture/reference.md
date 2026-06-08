# Architecture Reference — Student Project Support System

## Entities (`src/models/`)

| Class | Key fields |
|---|---|
| `Student` | id, name, role (LEADER/MEMBER), is_blocked, active_projects_count, missed_deadlines_count |
| `Team` | id, name, capacity, member_ids |
| `Project` | id, title, description, status (DRAFT/ACTIVE/COMPLETED/ARCHIVED), team_id, created_at |
| `Milestone` | id, project_id, title, due_date, status (PENDING/SUBMITTED/LATE/MISSED), submitted_at |
| `Submission` | id, milestone_id, team_id, submitted_at |
| `Penalty` | id, student_id, milestone_id, points, is_resolved |
| `QueueRequest` | id, student_id, team_id, created_at, expires_at, status (PENDING/FULFILLED/EXPIRED/CANCELLED) |

## Repository ABCs (`src/storage/interfaces.py`)

One ABC per entity: `StudentRepository`, `TeamRepository`, `ProjectRepository`,
`MilestoneRepository`, `SubmissionRepository`, `PenaltyRepository`, `QueueRequestRepository`.

Specialised query methods beyond basic CRUD:
- `MilestoneRepository.find_overdue(as_of)` — PENDING milestones past `due_date`
- `PenaltyRepository.total_unresolved_by_student(student_id) -> int`
- `QueueRequestRepository.find_pending_by_team(team_id)`

## Services (`src/services/`)

| Service | Responsibility | Key injected deps |
|---|---|---|
| `ProjectService` | Project lifecycle (create, assign team, change status) | `ProjectRepository`, `TeamRepository` |
| `MilestoneService` | Submissions, missed marks, penalty creation, event firing | All repos + `PenaltyStrategy` + `DeadlineSubject` |
| `TeamService` | Join/queue/leave, queue expiry, priority ordering | `TeamRepository`, `StudentRepository`, `QueueRequestRepository`, `DeadlineSubject` |
| `MembershipService` | Evaluate/block/unblock based on penalty points and missed deadlines | `StudentRepository`, `PenaltyRepository` |

## GoF patterns

### Strategy — penalty calculation

`PenaltyStrategy` (ABC) in `src/services/penalty_strategies.py`.  
Concrete strategies: `FlatPenaltyStrategy`, `ProgressivePenaltyStrategy`,
`WeekendExemptPenaltyStrategy`, `CappedPenaltyStrategy` (Decorator).  
Factory: `PenaltyStrategyFactory`.  
Injected into `MilestoneService`; called as `strategy.calculate(due_date, submitted_date) -> int`.

### Observer — milestone status + team-spot events

ABCs: `DeadlineSubject`, `DeadlineObserver` — both in `src/services/events.py`.  
Concrete subject: `EventBus` (snapshot-based dispatch, idempotent subscribe).  
Events: `MilestoneStatusChangedEvent`, `TeamSpotAvailableEvent`.  
Concrete observer: `StudentNotifier` (`src/services/notification.py`) — records
`Notification` objects for team members (on milestone change) and the top-priority
queued student (on team-spot event).

## Valid project status transitions

```
DRAFT  →  ACTIVE (requires team_id set)
DRAFT  →  ARCHIVED
ACTIVE →  COMPLETED
ACTIVE →  ARCHIVED
COMPLETED → ARCHIVED
ARCHIVED  → (terminal)
```

## Queue priority key

`(student.active_projects_count, queue_request.created_at)` — ascending.  
Lower active-project count wins; FIFO within the same count.
