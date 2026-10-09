# Changelog

## Unreleased — 2026-10-10

- Renamed the platform to TAKSHYRA, the Python distribution to `takshyra-core`, and the import package to `takshyra`. Added the chosen product, technology, Core, Insight, and Guardian names with honest implementation labels.
- Renamed the local project directory to `TAKSHYRA` and aligned API, Compose, tests, examples, documentation and CI paths.
- Added M1 local core: development-only tenant authentication, pipeline API, initial Alembic migration, DB-leased worker, deterministic CSV-to-Parquet transform, quality results, audit records, Compose configuration and integration tests.
- Added local runbook and Compose smoke script. PostgreSQL and Compose smoke verification remain pending because Docker is unavailable in the authoring environment.
- No cloud resources, agents, UI or paid integrations implemented.

## Blueprint — 2026-10-09

- Added Takshyra specifications, milestone prompts, design decisions, documentation validator and synthetic fixtures.
