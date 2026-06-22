# Python — Personal Standards

Reference file. Load when working on Python code.

---

## Comments

Write comments only when the **why** is non-obvious: a hidden constraint, a workaround for a specific bug, an invariant that would surprise a reader.

Never write:
- Comments that restate what the code does (`# increment counter`)
- Multi-line docstrings for private functions
- TODO/FIXME without a ticket reference

One-line docstrings on public functions are acceptable when the signature alone is ambiguous.

## Naming

| Construct | Convention | Example |
|-----------|-----------|---------|
| Function / method | `snake_case`, verb | `compute_cost()`, `load_data()` |
| Class | `PascalCase`, noun | `SolverConfig`, `AssetLoader` |
| Variable | `snake_case`, noun | `node_count`, `time_horizon` |
| Constant (module-level) | `UPPER_SNAKE` | `MAX_ITERATIONS`, `DEFAULT_TIMEOUT` |
| Private | leading `_` | `_validate_bounds()` |
| Type alias | `PascalCase` | `NodeId = int` |

Prefer full words over abbreviations unless the abbreviation is domain-standard (`lp`, `mip`, `kpi`).

## Code Structure

- Functions do one thing. If you need "and" to describe it, split it.
- No function longer than 40 lines without a strong reason.
- No speculative abstractions — extract only when the duplication exists, not when it might.
- Return early; avoid deep nesting.
- Prefer `dataclass` over plain dict for structured data passed between functions.

## Type Annotations

- Annotate all public function signatures.
- Do not annotate obvious local variables (`x: int = 0` → just `x = 0`).
- Use `from __future__ import annotations` for forward references.
- `Optional[X]` → `X | None` (Python ≥ 3.10).

## Imports

Order: stdlib → third-party → local. One blank line between groups.  
Never use wildcard imports (`from module import *`).  
Absolute imports only; avoid relative imports except inside packages.

## Error Handling

Validate at system boundaries (user input, external APIs, file I/O). Trust internal guarantees.  
Catch specific exceptions, never bare `except:`.  
Raise `ValueError` for bad arguments, `RuntimeError` for unexpected states.
