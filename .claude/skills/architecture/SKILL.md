---
name: architecture
description: In-memory layered architecture of the Student Project Support System. Use when creating or modifying models, repository interfaces or services, or deciding which layer new code belongs to.
---

## Layer order

```
models  →  storage interfaces (ABC)  →  services  →  utils
```

Dependencies flow in one direction only — no layer imports from a layer above it.

## Rules

1. **Define the `abc.ABC` interface first.** No `InMemory*` implementation may exist without its abstract counterpart in `storage/interfaces.py`.
2. **Inject all dependencies via constructor.** No `import`-time instantiation of collaborators; no global state.
3. **No external I/O.** Nothing in `src/` may touch a database, HTTP endpoint, file system, or third-party API.
4. **`models/` imports nothing** from this project. `utils/` imports nothing from `services/` or `storage/`.
5. **Services depend on ABCs**, never on `InMemory*` concrete classes.

## Where new code belongs

| What you're adding | Layer |
|---|---|
| Data entity (fields + `__post_init__` validation) | `models/` |
| ABC query contract | `storage/interfaces.py` |
| Dict-backed store | `storage/memory/<name>_repo.py` |
| Business rule / workflow | `services/` |
| Domain exception | `utils/exceptions.py` |
| Event or observer ABC | `services/events.py` |
| Penalty algorithm variant | `services/penalty_strategies.py` |

For the full entity list, pattern locations, and dependency diagram see
[`reference.md`](reference.md) in this folder.
