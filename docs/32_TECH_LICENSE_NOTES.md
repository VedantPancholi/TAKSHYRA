# Technology selection and license due diligence

## Expected stack
Python + FastAPI + Pydantic + SQLAlchemy/Alembic + PostgreSQL + Docker Compose + Next.js/TypeScript + a Redis-backed worker + DuckDB/PyArrow for demo + pytest/Playwright + OpenTelemetry. Optional: Ollama, pgvector, Kafka/Redpanda, Grafana/Prometheus, Azure SDKs.

## Before shipping public code
- Inspect and pin actual library versions at implementation time; generate lockfiles or constrained dependencies.
- Check **code license**, **model license**, **container image terms**, and **commercial redistribution/use rights** independently. A no-fee download is not automatically unrestricted open source.
- Do not claim named providers offer permanent free Azure services; pricing/free allocations can change, and local developer time/hardware are not free.
- Choose an intentional repo LICENSE; absent a license, standard copyright restrictions apply.
- Generate SBOM and dependency/vulnerability scan if supported by CI.

## Standards (reference, not implemented claim)
OpenLineage: https://openlineage.io/docs/spec/
OpenTelemetry: https://opentelemetry.io/docs/specs/semconv/
FastAPI: https://fastapi.tiangolo.com/
PostgreSQL: https://www.postgresql.org/docs/
Azure: https://learn.microsoft.com/en-us/azure/

No technology choice should be replaced merely due to buzzword popularity. Prefer fewer systems with working tests and demonstrable failure recovery.
