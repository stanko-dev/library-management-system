# Domain Model

Core entities, value objects, and their relationships in the Student Project Support System.

```mermaid
classDiagram
    direction TB

    %% ── Enumerations ─────────────────────────────────────────────────
    class StudentRole {
        <<enumeration>>
        LEADER
        MEMBER
    }

    class ProjectStatus {
        <<enumeration>>
        DRAFT
        ACTIVE
        COMPLETED
        ARCHIVED
    }

    class MilestoneStatus {
        <<enumeration>>
        PENDING
        SUBMITTED
        LATE
        MISSED
    }

    class QueueRequestStatus {
        <<enumeration>>
        PENDING
        FULFILLED
        EXPIRED
        CANCELLED
    }

    %% ── Entities ─────────────────────────────────────────────────────
    class Student {
        +id : str
        +name : str
        +role : StudentRole
        +is_blocked : bool
        +active_projects_count : int
        +missed_deadlines_count : int
    }

    class Team {
        +id : str
        +name : str
        +capacity : int
        +member_ids : list
        +is_full() bool
        +available_spots() int
    }

    class Project {
        +id : str
        +title : str
        +description : str
        +status : ProjectStatus
        +team_id : str
        +created_at : datetime
    }

    class Milestone {
        +id : str
        +project_id : str
        +title : str
        +due_date : datetime
        +status : MilestoneStatus
        +submitted_at : datetime
    }

    class Submission {
        +id : str
        +milestone_id : str
        +team_id : str
        +submitted_at : datetime
    }

    class Penalty {
        +id : str
        +student_id : str
        +milestone_id : str
        +points : int
        +is_resolved : bool
    }

    class QueueRequest {
        +id : str
        +student_id : str
        +team_id : str
        +created_at : datetime
        +expires_at : datetime
        +status : QueueRequestStatus
    }

    %% ── Entity → Enumeration ────────────────────────────────────────
    Student      --> StudentRole         : role
    Project      --> ProjectStatus       : status
    Milestone    --> MilestoneStatus     : status
    QueueRequest --> QueueRequestStatus  : status

    %% ── Entity relationships ─────────────────────────────────────────
    Team "1" --> "0..*" Student          : has members
    Project "0..*" --> "0..1" Team       : assigned to
    Milestone "0..*" --> "1" Project     : belongs to
    Submission "0..1" --> "1" Milestone  : records
    Submission "0..1" --> "1" Team       : submitted by
    Penalty "0..*" --> "1" Student       : issued to
    Penalty "0..*" --> "1" Milestone     : triggered by
    QueueRequest "0..*" --> "1" Student  : placed by
    QueueRequest "0..*" --> "1" Team     : waiting for
```

## Relationship Notes

| Relationship | Multiplicity | Description |
|---|---|---|
| Team → Student | 1 to 0..* | A team holds a list of member IDs; membership is capped at the team's `capacity`. |
| Project → Team | 0..* to 0..1 | A project may have no team (DRAFT) or exactly one team once assigned. |
| Milestone → Project | 0..* to 1 | Each milestone belongs to exactly one project; a project may have many milestones. |
| Submission → Milestone | 0..1 to 1 | At most one submission per milestone; a second submit attempt raises `AlreadySubmittedError`. |
| Penalty → Student | 0..* to 1 | Multiple penalties may accumulate on one student across different milestones. |
| Penalty → Milestone | 0..* to 1 | Each late or missed milestone generates one penalty per team member. |
| QueueRequest → Team | 0..* to 1 | Multiple students may queue for the same full team; served by priority, not pure FIFO. |
