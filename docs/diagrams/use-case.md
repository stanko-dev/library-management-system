# Use Case Diagram

Actors and their interactions with the Library Management System.

- **Reader** — a registered library member who borrows, reserves, and pays fines.
- **Librarian** — library staff who processes loans/returns and manages reader standing.

```mermaid
graph LR
    %% ── Actors ──────────────────────────────────────────────────────
    Reader(("Reader"))
    Librarian(("Librarian"))

    %% ── System boundary ─────────────────────────────────────────────
    subgraph LMS ["Library Management System"]
        direction TB

        UC1(["Issue Book\n(Borrow)"])
        UC2(["Return Book"])
        UC3(["Reserve Book"])
        UC4(["Cancel Reservation"])
        UC5(["Pay Fine"])
        UC6(["Block / Unblock Reader"])

        %% ── «include» relationships ─────────────────────────────────
        CHK["«include»\nCheck Reader Eligibility"]
        CAL["«include»\nCalculate Fine"]
        QUE["«include»\nEvaluate Reservation Queue"]

        UC1 -.->|«include»| CHK
        UC2 -.->|«include»| CAL
        UC2 -.->|«include»| QUE
        UC6 -.->|«include»| CHK
    end

    %% ── Reader associations ─────────────────────────────────────────
    Reader --> UC1
    Reader --> UC2
    Reader --> UC3
    Reader --> UC4
    Reader --> UC5

    %% ── Librarian associations ───────────────────────────────────────
    Librarian --> UC1
    Librarian --> UC2
    Librarian --> UC6
```

## Use Case Descriptions

| Use Case | Primary Actor | Brief Description |
|---|---|---|
| **Issue Book** | Reader / Librarian | Reader requests a loan; system checks eligibility (not blocked, copy available, loan limit not exceeded) and creates a Loan. |
| **Return Book** | Reader / Librarian | Reader returns a copy; system records return date, calculates any overdue fine, restores the available-copy count, and notifies waiting reservers. |
| **Reserve Book** | Reader | Reader places a reservation on a fully-borrowed title; system adds it to the priority queue (PREMIUM before STANDARD, oldest first). |
| **Cancel Reservation** | Reader | Reader withdraws an active reservation before it expires or is fulfilled. |
| **Pay Fine** | Reader | Reader settles an outstanding fine; once all fines are paid and overdue count is within threshold, the reader may be unblocked. |
| **Block / Unblock Reader** | Librarian | Librarian (or automated evaluation) blocks a reader whose unpaid fines ≥ $10 or overdue-return count ≥ 3; unblocks when thresholds are cleared. |
