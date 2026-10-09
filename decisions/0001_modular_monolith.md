# ADR 0001 — Modular monolith + worker
**Status:** Accepted as initial design (2026-10-09)

**Context:** Small initial team, several logical domains; microservices add network/deployment/tracing complexity before product-market validation.

**Decision:** Use one FastAPI modular monolith and separately executed worker; explicit module interfaces and Postgres transactions. Redis can transport jobs but not be sole durable truth.

**Tradeoffs:** Fast iteration, simple auth, easier testability. Must enforce boundary imports and avoid blocking API with ETL workloads. Extract services only with measured operational need.
