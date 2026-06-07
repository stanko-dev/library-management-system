# Domain Model

Core entities, value objects, and their relationships in the Library Management System.

```mermaid
classDiagram
    direction TB

    %% ── Enumerations ─────────────────────────────────────────────────
    class MembershipType {
        <<enumeration>>
        PREMIUM
        STANDARD
    }

    class BookStatus {
        <<enumeration>>
        AVAILABLE
        UNAVAILABLE
        RESERVED
        LOST
        MAINTENANCE
    }

    class ReservationStatus {
        <<enumeration>>
        ACTIVE
        FULFILLED
        CANCELLED
        EXPIRED
    }

    %% ── Entities ─────────────────────────────────────────────────────
    class Reader {
        +id : str
        +name : str
        +membership : MembershipType
        +is_blocked : bool
        +active_loans : int
        +overdue_count : int
    }

    class Book {
        +id : str
        +title : str
        +author : str
        +isbn : str
        +total_copies : int
        +available_copies : int
        +status : BookStatus
    }

    class Loan {
        +id : str
        +book_id : str
        +reader_id : str
        +issued_at : datetime
        +due_date : datetime
        +returned_at : datetime | None
        +is_active() bool
        +is_overdue(as_of) bool
    }

    class Reservation {
        +id : str
        +book_id : str
        +reader_id : str
        +created_at : datetime
        +expires_at : datetime
        +status : ReservationStatus
    }

    class Fine {
        +id : str
        +reader_id : str
        +loan_id : str
        +amount : Decimal
        +is_paid : bool
    }

    %% ── Entity → Enumeration ────────────────────────────────────────
    Reader --> MembershipType : membership
    Book   --> BookStatus     : status
    Reservation --> ReservationStatus : status

    %% ── Entity relationships ─────────────────────────────────────────
    Reader "1" --> "0..*" Loan        : takes
    Reader "1" --> "0..*" Reservation : places
    Reader "1" --> "0..*" Fine        : owes

    Book "1" --> "0..*" Loan        : subject of
    Book "1" --> "0..*" Reservation : subject of

    Loan "1" --> "0..1" Fine : may generate
```

## Relationship Notes

| Relationship | Multiplicity | Description |
|---|---|---|
| Reader → Loan | 1 to 0..* | A reader may have multiple active or historical loans; limited by membership tier (STANDARD ≤ 3, PREMIUM ≤ 5 active at once). |
| Reader → Reservation | 1 to 0..* | A reader may hold at most one active reservation per title at a time. |
| Reader → Fine | 1 to 0..* | Fines accumulate across all overdue loans; total unpaid ≥ $10 triggers a block. |
| Book → Loan | 1 to 0..* | Multiple copies may be on loan simultaneously (`available_copies` tracks what remains). |
| Book → Reservation | 1 to 0..* | Multiple readers may queue for the same book; served in PREMIUM-first, oldest-first order. |
| Loan → Fine | 1 to 0..1 | A fine is created only when `return_date > due_date`; on-time returns generate no fine. |
