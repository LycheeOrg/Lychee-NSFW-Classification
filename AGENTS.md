# AGENTS.md — AI Agent Guidelines

This file guides AI agents (Claude, Copilot, etc.) working on this repository.
Read it before exploring the codebase or proposing any changes.

## Repository at a glance

- **Language:** Python 3.13
- **Framework:** FastAPI + Uvicorn
- **Purpose:** NSFW classification microservice for the [Lychee](https://github.com/LycheeOrg/Lychee) photo gallery
- **Key docs:** [`docs/`](docs/) — start with [`docs/0-overview/README.md`](docs/0-overview/README.md)

## Mandatory first steps

Before writing any code:

1. Read [`docs/0-overview/README.md`](docs/0-overview/README.md) — integration model and design decisions.
2. Read [`docs/1-concepts/README.md`](docs/1-concepts/README.md) — domain model (detection pipeline, classification, thresholds).
3. Read [`docs/3-reference/coding-conventions.md`](docs/3-reference/coding-conventions.md) — enforced style and architecture rules.
4. Explore the relevant `app/` modules for the area you will touch.

## Spec-Driven Development (SDD)

All non-trivial changes follow SDD. Work through these phases in order — do not skip ahead to implementation.

### Phase 1 — Explore

Read the relevant source files and existing specs. Understand the current behaviour before proposing changes.

### Phase 2 — Spec

Create a feature directory and write the specification:

```
docs/4-architecture/features/<NNN>-<feature-name>/
└── spec.md
```

- `<NNN>` is a three-digit zero-padded sequential number (see [feature numbering conventions](docs/4-architecture/spec-guidelines/feature-numbering-conventions.md)).
- `<feature-name>` is 2–4 hyphen-separated lowercase words in action-noun format (e.g. `add-blur-filter`, `fix-threshold-logic`).
- Check existing feature directories to find the next available number.

**`spec.md` must cover:**
- Goal and motivation
- Scope (what is in / out)
- Functional requirements (numbered, testable)
- Non-functional requirements (performance, security, backward compatibility)
- Data model or API changes, if any
- Open questions (unresolved decisions that block progress)

**Stop and present open questions** before continuing. Format them as Decision Cards following [`docs/4-architecture/spec-guidelines/open-questions-format.md`](docs/4-architecture/spec-guidelines/open-questions-format.md). Wait for human answers before writing plan or code.

### Phase 3 — Plan

Once all open questions are resolved, write the implementation plan:

```
docs/4-architecture/features/<NNN>-<feature-name>/
├── spec.md
└── plan.md
```

`plan.md` describes the approach: which files change, in what order, and why. Include alternatives considered and why they were rejected.

### Phase 4 — Tasks

Break the plan into a checkbox task list:

```
docs/4-architecture/features/<NNN>-<feature-name>/
├── spec.md
├── plan.md
└── tasks.md
```

`tasks.md` contains ordered `- [ ] …` items. Write tests before implementation (test-first). Mark each item `[x]` as it is completed.

### Phase 5 — Implement

Follow the task list. Tick items as you go. Do not add scope beyond what is in the spec.

### Small fixes exception

Typo fixes, single-line bug fixes with an obvious cause, and minor documentation corrections do not need a feature directory. A direct PR is acceptable.

## Quality gates

All of the following must pass before a PR is opened:

```bash
make lint    # ruff check + ruff format --check + ty check
make test    # pytest
```

Never skip hooks or disable linters to make CI pass. Fix the root cause instead.

## Key conventions (summary)

- All env vars live in `AppSettings` (`app/config.py`) — never read `os.environ` directly.
- CPU-bound work (NudeNet inference) must be offloaded via `loop.run_in_executor(executor, ...)`.
- Routes are thin — delegate to domain modules in `app/detection/`.
- Use `typing.Protocol` for backend-agnostic interfaces; no inheritance required.
- `from __future__ import annotations` at the top of every module.
- All signatures must be fully type-annotated.

Full details: [`docs/3-reference/coding-conventions.md`](docs/3-reference/coding-conventions.md)

## References

| Document | Purpose |
|---|---|
| [`docs/0-overview/README.md`](docs/0-overview/README.md) | Service overview and integration model |
| [`docs/1-concepts/README.md`](docs/1-concepts/README.md) | Domain concepts |
| [`docs/2-how-to/`](docs/2-how-to/) | Deployment and tuning guides |
| [`docs/3-reference/api.md`](docs/3-reference/api.md) | API endpoint reference |
| [`docs/3-reference/configuration.md`](docs/3-reference/configuration.md) | All environment variables |
| [`docs/3-reference/coding-conventions.md`](docs/3-reference/coding-conventions.md) | Style and architecture rules |
| [`docs/4-architecture/spec-guidelines/feature-numbering-conventions.md`](docs/4-architecture/spec-guidelines/feature-numbering-conventions.md) | Feature numbering and naming |
| [`docs/4-architecture/spec-guidelines/open-questions-format.md`](docs/4-architecture/spec-guidelines/open-questions-format.md) | Decision Card format for open questions |
| [`docs/Contribute.md`](docs/Contribute.md) | Human contributor guide |
