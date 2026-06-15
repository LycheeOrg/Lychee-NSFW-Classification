# Lychee NSFW Classification — Documentation

Welcome to the developer documentation for the Lychee NSFW Classification microservice.
This folder contains documentation about the service's architecture, integration model, data structures, and contribution guidelines. It is intended for contributors and operators who want to understand or extend the service.

The key folders at the root level of the repository are:

```
./
├── app/        # FastAPI application: routes, detection, and classification logic
├── docs/       # Developer documentation (this folder)
├── tests/      # Automated test suite
├── Dockerfile  # Multi-stage container build
└── Makefile    # Development workflow shortcuts
```

## Documentation Structure

Documentation is organised following the [Diátaxis framework](https://diataxis.fr/):

- **[0-overview](0-overview/)** — Service overview and integration model
- **[1-concepts](1-concepts/)** — Domain model (detection pipeline, classification thresholds, NSFW categories)
- **[2-how-to](2-how-to/)** — Deployment and tuning guides
- **[3-reference](3-reference/)** — Technical reference (API, configuration, coding conventions)
- **[4-architecture](4-architecture/)** — Architecture decisions and feature specifications

### Contributing

- [Contribution Guide](Contribute.md) — How to contribute to this project
- [Coding Conventions](3-reference/coding-conventions.md) — Python coding standards
- [AGENTS.md](../AGENTS.md) — Instructions for AI agents working on this codebase

## Additional Resources

- [Main Lychee Repository](https://github.com/LycheeOrg/Lychee)
- [Official Website](https://lycheeorg.dev/)
- [Admin Documentation](https://lycheeorg.dev/docs/)

---

*Last updated: June 15, 2026*
