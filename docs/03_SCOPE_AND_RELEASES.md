# Scope, releases, non-goals and dependencies

## Release schedule (capabilities, not calendar promises)
| Release | Product capability | Mandatory exit proof |
|---|---|---|
| R1 | Local batch reliability core | Reproducible actual run and quality result; auth and tests |
| R2 | Incident → policy → recovery | Denied unsafe action + approved or allowed bounded retry traced end to end |
| R3 | Contracts/lineage/impact | Good run / bad data blocked from publication; graph impact shown |
| R4 | Shadow lab/incident memory | Isolated test and post-action verification; verified incident retrieval |
| R5 | Streams/Azure adapter | Mocked connectors + one opt-in sandbox verified separately |
| R6 | Hardening/evaluation | Tested restore, load, CI, security drills, well-documented limits |

## Highest-priority features (P0)
Multi-tenant auth, pipeline registry, durable state, quality checks, incident timeline, proposal/policy/approval, audit, safe retry, documented demo, working tests.

## Differentiators (P1)
Data contracts, dataset lineage, business impact, Data Trust Passport, shadow repair, streaming lag/late event/reconciliation, incident memory, post-action verification.

## Experiments (P2)
Predictive incidents, cost advisor, provider-neutral LLM, conversational incident explorer, Teams/Slack notifications, multi-cloud, advanced ML model dependencies.

## Explicitly out of scope until separately approved
General-purpose low-code ETL builder; arbitrary user-uploaded Python execution; cloud deployment engine; production schema rewrite; IAM/firewall edits; data deletion; zero-downtime or SLA commitments; automatic billing; customer PII ingestion; unsupported Azure/Fabric APIs; orchestration replacement.

## Dependency ordering
Identity/permissions → durable run state → quality signals → incidents/evidence → safe action engine → contracts → lineage impact → shadow lab → adapters → predictive models. UI starts basic early and expands as proven backend capabilities appear. Security is never postponed.
