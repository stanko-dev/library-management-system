# Requirements — Library Management System

## 1. Problem Statement

A public library needs software to manage the lifecycle of book loans, reservations,
and reader accounts without an external database. All state is held in memory for the
duration of the process.

The system must enforce borrowing rules consistently across two membership tiers
(Standard and Premium), calculate overdue fines using pluggable algorithms, and
maintain a fair-but-priority-aware queue when multiple readers are waiting for the
same book.

### 1.1 Non-Trivial Logic

#### Fine Calculation

Fines are computed at return time by a **FineStrategy** selected at system
configuration. Four strategies are available:

| Strategy | Formula | Notes |
|---|---|---|
| **Flat** | `overdue_days × daily_rate` | Simple per-day fee; no cap. |
| **Progressive** | Day *n* costs `base_rate + (n−1) × increment`; total = Σ of all day costs, then `min(total, cap)` | Escalating penalty with an absolute ceiling. |
| **Weekend-Exempt** | Count only weekdays (Mon–Fri) in the overdue window; multiply by `daily_rate` | Readers are not charged for Saturdays and Sundays. |
| **Capped (Decorator)** | Delegates to any inner strategy, then applies `min(result, cap)` | Adds a hard cap to an existing strategy without modifying it. |

No fine is created when the book is returned on or before the due date.

#### Reservation-Queue Prioritization

When a book becomes available, the reader who holds the **highest-priority active
reservation** is notified first. Priority is determined by a two-level sort key:

1. **Membership tier** — Premium (rank 0) is served before Standard (rank 1).
2. **Arrival time** — within the same tier, the reader who reserved earliest
   (`created_at` ascending) is served first (FIFO).

Reservations expire automatically if not fulfilled within 3 days of creation.

---

## 2. Actors

### Reader

A registered library member who can borrow books, place reservations, and pay
outstanding fines. Readers belong to one of two membership tiers:

- **Standard** — may hold up to 3 active loans simultaneously.
- **Premium** — may hold up to 5 active loans simultaneously; takes priority in the
  reservation queue over Standard readers waiting for the same book.

A Reader who is **blocked** cannot borrow or reserve books until the block is lifted.

### Librarian

Library staff responsible for processing loan issuance and returns at the counter,
and for managing reader standing (blocking or unblocking accounts).

---

## 3. Use Cases

### UC-1 Issue Book

**Actors:** Reader, Librarian  
**Goal:** Create a new loan that associates a reader with a book copy for a fixed period.

#### Main Flow

1. The Librarian (or Reader) submits a loan request: `reader_id`, `book_id`,
   and optionally `loan_days` (default 14).
2. The system verifies the reader exists.
3. The system verifies the reader is not blocked.
4. The system verifies the book exists.
5. The system verifies at least one copy is available (`available_copies > 0`).
6. The system verifies the reader has not reached their active-loan limit
   (Standard ≤ 3, Premium ≤ 5).
7. The system creates a `Loan` record with `issued_at = now` and
   `due_date = now + loan_days`.
8. The system decrements `book.available_copies` by 1.
9. The system increments `reader.active_loans` by 1.
10. The system returns the new `Loan` to the caller.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Reader ID not found | `ReaderNotFoundError` raised; no state changes. |
| 3 | Reader is blocked | `ReaderBlockedError` raised; no state changes. |
| 4 | Book ID not found | `BookNotFoundError` raised; no state changes. |
| 5 | `available_copies == 0` | `BookNotAvailableError` raised; no state changes. |
| 6 | Active loans ≥ tier limit | `LoanLimitExceededError` raised; no state changes. |

---

### UC-2 Return Book

**Actors:** Reader, Librarian  
**Goal:** Record the return of a book, charge an overdue fine if applicable, and
notify the next reader in the reservation queue.

#### Main Flow

1. The Librarian (or Reader) submits the `loan_id`.
2. The system looks up the loan.
3. The system records `returned_at = now`.
4. The system calculates a fine via the configured `FineStrategy`:
   `strategy.calculate(due_date.date(), returned_at.date())`.
5. If the fine amount is greater than zero, the system creates a `Fine` record
   (marked unpaid) and increments `reader.overdue_count`.
6. The system increments `book.available_copies` by 1 and decrements
   `reader.active_loans` by 1 (floored at 0).
7. The system publishes a `BookAvailableEvent` to the event bus.
8. The `ReaderNotifier` observer receives the event, finds the highest-priority
   active reservation for the book (Premium first, then FIFO), and records a
   `Notification` for that reader.
9. The system returns the `Fine` object (or `None` if no fine was generated).

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Loan ID not found | `LoanNotFoundError` raised; no state changes. |
| 2 | Loan already has `returned_at` set | `AlreadyReturnedError` raised; no state changes. |
| 4 | `return_date ≤ due_date` | Fine amount is 0; no `Fine` record is created (step 5 is skipped). |
| 8 | No active reservations for the book | Notification step is skipped silently. |

---

### UC-3 Reserve Book

**Actors:** Reader  
**Goal:** Queue a reader to be notified when a fully-borrowed book becomes available.

#### Main Flow

1. The Reader submits `reader_id` and `book_id`.
2. The system verifies the reader exists.
3. The system verifies the reader is not blocked.
4. The system verifies the book exists.
5. The system checks that the reader does not already hold an active reservation
   for this book.
6. The system creates a `Reservation` record with status `ACTIVE`,
   `created_at = now`, and `expires_at = now + 3 days`.
7. The system returns the new `Reservation`.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Reader ID not found | `ReaderNotFoundError` raised. |
| 3 | Reader is blocked | `ReaderBlockedError` raised. |
| 4 | Book ID not found | `BookNotFoundError` raised. |
| 5 | Reader already has an active reservation for the book | `DuplicateReservationError` raised. |

---

### UC-4 Cancel Reservation

**Actors:** Reader  
**Goal:** Withdraw an active reservation before it is fulfilled or expires.

#### Main Flow

1. The Reader submits `reservation_id`.
2. The system looks up the reservation.
3. The system sets `reservation.status = CANCELLED`.
4. The system persists the change.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Reservation ID not found | `ReservationNotFoundError` raised. |

> **Note:** The system does not restrict cancellation to `ACTIVE` reservations; a
> previously expired or fulfilled reservation can also be set to `CANCELLED` via this
> flow, though in practice clients should only cancel active ones.

---

### UC-5 Pay Fine

**Actors:** Reader  
**Goal:** Mark one or more outstanding fines as paid and, if thresholds are cleared,
allow the reader's account to be unblocked.

#### Main Flow

1. The Reader (or Librarian) identifies the unpaid `Fine` by its `id`.
2. The system retrieves the fine from the repository.
3. The system sets `fine.is_paid = True`.
4. The system persists the updated fine.
5. (Optional) The Librarian calls `MembershipService.evaluate(reader_id)` to
   recompute the reader's blocked status against the current totals:
   - **Block condition:** `total_unpaid_fines ≥ $10.00` OR `overdue_count ≥ 3`.
   - If neither condition holds, the reader is automatically unblocked.

#### Alternative Flows

| Step | Condition | Outcome |
|---|---|---|
| 2 | Fine ID not found | No matching record; no changes made. |
| 5 | Unpaid fines still ≥ $10.00 or overdue_count still ≥ 3 after payment | Reader remains blocked. |

---

### UC-6 Block / Unblock Reader

**Actors:** Librarian  
**Goal:** Restrict or restore a reader's ability to borrow and reserve books.

#### Main Flow — Automated Evaluation

1. The Librarian (or the system on a scheduled basis) calls
   `MembershipService.evaluate(reader_id)`.
2. The system retrieves the reader.
3. The system sums all unpaid fines for the reader.
4. The system applies the block condition:
   - **Block** if `total_unpaid ≥ $10.00` OR `reader.overdue_count ≥ 3`.
   - **Unblock** if neither condition holds.
5. The system persists the updated `reader.is_blocked` flag.
6. The service returns `True` if blocked, `False` if unblocked.

#### Alternative Flow — Force Block

1. The Librarian calls `MembershipService.block(reader_id)`.
2. The system retrieves the reader.
3. The system sets `reader.is_blocked = True` regardless of thresholds.
4. The system persists the change.

#### Alternative Flow — Force Unblock

1. The Librarian calls `MembershipService.unblock(reader_id)`.
2. The system retrieves the reader.
3. The system sets `reader.is_blocked = False` regardless of thresholds.
4. The system persists the change.

#### Alternative Flows (all sub-cases)

| Step | Condition | Outcome |
|---|---|---|
| 2 (any flow) | Reader ID not found | `ReaderNotFoundError` raised. |
