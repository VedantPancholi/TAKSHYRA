# Decisions, assumptions and open questions

## Accepted design decisions
1. Start with modular monolith + one worker.
2. Local synthetic/CPU-first core; Azure optional.
3. LLM is advisory, deterministic policy is authoritative.
4. Mutating actions must be typed and allowlisted; infrastructure destructive ops denied.
5. Execution, quality and publication are separate dimensions.
6. Incident memory contains verified outcomes distinctly from hypotheses.
7. Data lineage may be declared, observed or inferred; mark source.

## Assumptions to validate before Milestone 1 coding
- Local authentication chosen (secure development-only login) and supported password hashing implementation.
- Whether RQ or Celery best satisfies durable retry, visibility and lease behavior for actual code.
- PostgreSQL + Redis local resources can run on development machine.
- Basic file output rename / DB publication manifest consistency mechanism chosen.
- Default date/time policy (UTC and source event time) specified.
- Native Windows setup uses PowerShell equivalents for Makefile commands.

## Open tradeoffs for ADRs
| Question | Default bias | Decide when |
|---|---|---|
| RQ vs Celery? | simplest verified bounded jobs | M1 |
| SQL JSONB rules or separate rule rows? | JSONB with schema validation, immutable versions | M4 |
| RLS in database? | optional defense in depth; backend checks mandatory | M1/M10 |
| pgvector for memory? | defer until similarity retrieval clearly useful | M7 |
| Semantic lineage vs UI graph store? | PostgreSQL adjacency initially | M5 |
| Ollama bundled vs separate? | optional local runtime, not default core | M7 |
| Kafka vs Redpanda? | choose one local test broker, document license | M9 |
| FastAPI run-in-process? | never for long processing | M1 |

If a decision affects security or data integrity, create ADR under `decisions/` and include migration/testing implications.
