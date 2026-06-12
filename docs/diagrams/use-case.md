# Use Case Diagram

Actors and their interactions with the Student Project Support System.

- **Student** — a registered participant who submits milestones and requests to join project teams.
- **Coordinator** — academic staff who creates and manages projects, assigns teams, applies penalties, and manages student standing.

```mermaid
flowchart LR
    %% ── Actors ──────────────────────────────────────────────────────
    Student(("Student"))
    Coordinator(("Coordinator"))

    %% ── System boundary ─────────────────────────────────────────────
    subgraph SPSS ["Student Project Support System"]
        direction TB

        UC1(["Create Project"])
        UC2(["Assign Team"])
        UC3(["Submit Milestone"])
        UC4(["Request to Join Team"])
        UC5(["Apply Penalty"])
        UC6(["Block Student"])

        %% ── «include» relationships ─────────────────────────────────
        CAL(["Calculate Penalty Points"])
        CHK(["Check Student Eligibility"])
        EVL(["Evaluate Block Thresholds"])

        UC3 -.->|«include»| CAL
        UC4 -.->|«include»| CHK
        UC6 -.->|«include»| EVL
    end

    %% ── Student associations ─────────────────────────────────────────
    Student --> UC3
    Student --> UC4

    %% ── Coordinator associations ─────────────────────────────────────
    Coordinator --> UC1
    Coordinator --> UC2
    Coordinator --> UC5
    Coordinator --> UC6
```

## Use Case Descriptions

| Use Case | Primary Actor | Brief Description |
|---|---|---|
| **Create Project** | Coordinator | Creates a DRAFT project with a title and description; a team may be pre-assigned. |
| **Assign Team** | Coordinator | Links an existing team to a non-archived project, enabling it to be moved to ACTIVE. |
| **Submit Milestone** | Student | Records a milestone submission; when past the due date the penalty strategy calculates and stores penalty points for every team member. |
| **Request to Join Team** | Student | Joins the team directly if space is available; otherwise creates a queue request prioritised by fewest active projects, then FIFO. |
| **Apply Penalty** | Coordinator | Marks an overdue milestone as MISSED and creates penalty records for all team members via the configured penalty strategy. |
| **Block Student** | Coordinator | Blocks a student whose unresolved penalty points or missed-deadline count exceed configured thresholds; blocked students cannot join teams. |
