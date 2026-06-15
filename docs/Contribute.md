# Contributing to Lychee NSFW Classification

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

Before contributing, review the documentation structure:
- [Overview](0-overview/README.md) — High-level introduction
- [Core Concepts](1-concepts/README.md) — Domain model and fundamental concepts
- [Reference Documentation](3-reference/) — Coding conventions and architecture
- [Architecture Documentation](4-architecture/) — Knowledge map and feature specs

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up your development environment
4. Create a new branch for your feature or bug fix
5. Make your changes
6. Test your changes
7. Submit a pull request

## Development Environment Setup

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (package and environment manager)

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/Lychee-NSFW-Classification.git
    cd Lychee-NSFW-Classification
    ```

2. Install dependencies (uv creates and manages the virtualenv automatically):
    ```bash
    uv sync --dev
    ```

3. Start the development server:
    ```bash
    uv run uvicorn app.main:app --reload
    ```

## Code Standards and Quality

### Python Standards

- **Python 3.13** — use modern syntax and type hints throughout
- **Type annotations** are required on all function signatures
- **Line length** is 120 characters (enforced by ruff)
- **No `# type: ignore`** comments without a documented reason
- All new files must contain the **license header** (take example from an existing file)

### Project-Specific Conventions

- Configuration lives in `app/config.py` via `pydantic-settings` — never read env vars directly
- Detection logic lives in `app/detection/` — keep API routing and business logic separate
- API routes live in `app/api/` — routes should be thin; delegate to detection layer

## Testing and Quality Assurance

Before submitting a pull request, ensure all quality checks pass.

### Run the test suite

```bash
make test
```

### Linting and formatting (ruff)

Check for lint errors and formatting:
```bash
make lint
```

Apply auto-fixes and format:
```bash
make format
```

### Type checking (ty)

```bash
uv run ty check
```

## Submitting Changes

1. **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name
    ```

2. **Make your changes** following the coding standards above

3. **Test your changes** using the quality assurance commands

4. **Commit your changes** with a clear and descriptive commit message:
    ```bash
    git commit -m "Add feature: description of your changes"
    ```

5. **Push your branch** to your fork:
    ```bash
    git push origin feature/your-feature-name
    ```

6. **Create a pull request** on GitHub with:
   - A clear title describing the change
   - A detailed description of what was changed and why
   - References to any related issues

## Using AI/Claude for Contributions

AI-assisted development is permitted and welcomed. However, contributions using AI tools must follow our **Specification-Driven Development (SDD)** workflow:

### Guidelines

1. **Read [AGENTS.md](../AGENTS.md) first** — This file contains the instructions that guide AI agents working on this codebase.

2. **Follow Spec-Driven Development** — AI-generated code must be anchored in explicit specifications:
   - Start by creating or updating the feature specification at `docs/4-architecture/features/<NNN>-<feature-name>/spec.md`
   - Generate a feature plan (`plan.md`) and tasks checklist (`tasks.md`)
   - Write tests before implementation (test-first cadence)

3. **Understand before generating** — AI tools should explore and understand the existing codebase before proposing changes.

4. **Quality gates still apply** — All AI-generated code must pass the same quality checks as human-written code:
   - `ty check` for type errors
   - `ruff check` for lint errors
   - `ruff format` for formatting
   - Full test suite via `pytest`

5. **Review and understand all output** — Contributors are responsible for understanding and validating any AI-generated code before submitting.

6. **Document open questions** — When AI encounters ambiguity, log questions in `docs/4-architecture/open-questions.md` and wait for clarification before proceeding.

### Recommended AI Models

We recommend using **Claude Sonnet or Claude Opus** for AI-assisted contributions.

When using **Claude Code**, reference `@AGENTS.md` as the first step in your conversation to guide the agent through the SDD workflow.

### Small Fixes Exception

The full SDD workflow is not required for trivial changes such as:
- Typo fixes
- Single-line bug fixes with obvious solutions
- Minor documentation corrections
- Simple configuration changes

For these cases, a direct PR without specifications is acceptable.

## Pull Request Guidelines

- Keep your changes focused and atomic
- Include tests for new functionality
- Update documentation if necessary
- Ensure all quality checks pass (`make lint`, `make test`)
- Be responsive to feedback during code review

## Getting Help

If you need help or have questions:

- Review the [documentation structure](.) to understand how the project is organised
- Check existing [discussions](https://github.com/LycheeOrg/Lychee/discussions)
- Join our [Discord](https://discord.gg/JMPvuRQcTf) and post in the #help channel

---

*Last updated: June 15, 2026*
