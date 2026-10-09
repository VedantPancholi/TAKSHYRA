# Specification index and reading order

This is a **blueprint**. Implementation status lives only in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), never inferred from documentation presence.

The implemented M1 local core and commands are documented in [37_M1_LOCAL_CORE.md](37_M1_LOCAL_CORE.md). Later capabilities in this index remain specifications.

| Concern | Authoritative specification |
|---|---|
| What/why/who | [01_PRODUCT_VISION.md](01_PRODUCT_VISION.md), [02_PERSONAS_AND_STORIES.md](02_PERSONAS_AND_STORIES.md), [29_BRAND_AND_PRODUCT_STRATEGY.md](29_BRAND_AND_PRODUCT_STRATEGY.md) |
| Scope & prioritization | [03_SCOPE_AND_RELEASES.md](03_SCOPE_AND_RELEASES.md), [24_ROADMAP.md](24_ROADMAP.md) |
| System architecture | [04_ARCHITECTURE.md](04_ARCHITECTURE.md), [05_DOMAIN_MODEL.md](05_DOMAIN_MODEL.md), [06_STATES_AND_EVENTS.md](06_STATES_AND_EVENTS.md) |
| API | [07_API_CONTRACTS.md](07_API_CONTRACTS.md) |
| Contracts, lineage, quality | [08_DATA_QUALITY.md](08_DATA_QUALITY.md), [09_LINEAGE_AND_IMPACT.md](09_LINEAGE_AND_IMPACT.md) |
| Diagnosis & recovery | [10_INCIDENTS.md](10_INCIDENTS.md), [11_POLICY_AND_ACTIONS.md](11_POLICY_AND_ACTIONS.md), [12_SHADOW_LAB_AND_REPLAY.md](12_SHADOW_LAB_AND_REPLAY.md), [13_AGENTS_AND_MEMORY.md](13_AGENTS_AND_MEMORY.md) |
| Streaming & integrations | [14_STREAMING_RELIABILITY.md](14_STREAMING_RELIABILITY.md), [15_CONNECTOR_SDK.md](15_CONNECTOR_SDK.md), [16_AZURE_ADAPTERS.md](16_AZURE_ADAPTERS.md) |
| Security and operations | [17_SECURITY_AND_THREAT_MODEL.md](17_SECURITY_AND_THREAT_MODEL.md), [18_OBSERVABILITY_SLOS.md](18_OBSERVABILITY_SLOS.md), [30_PRIVACY_AND_RETENTION.md](30_PRIVACY_AND_RETENTION.md) |
| Experience & QA | [19_UX_DESIGN.md](19_UX_DESIGN.md), [20_TESTING_AND_FAULT_LAB.md](20_TESTING_AND_FAULT_LAB.md), [21_EVALUATION.md](21_EVALUATION.md) |
| Developer & cloud ops | [22_LOCAL_DEV.md](22_LOCAL_DEV.md), [23_DEPLOYMENT_AND_COST.md](23_DEPLOYMENT_AND_COST.md), [25_ACCEPTANCE_GATES.md](25_ACCEPTANCE_GATES.md), [26_BACKLOG.md](26_BACKLOG.md) |
| Demos and strategy | [27_DEMO_PLAYBOOK.md](27_DEMO_PLAYBOOK.md), [28_GLOSSARY.md](28_GLOSSARY.md), [29_BRAND_AND_PRODUCT_STRATEGY.md](29_BRAND_AND_PRODUCT_STRATEGY.md) |
| Change management | [31_DECISIONS_AND_OPEN_QUESTIONS.md](31_DECISIONS_AND_OPEN_QUESTIONS.md), [32_TECH_LICENSE_NOTES.md](32_TECH_LICENSE_NOTES.md), [33_ORIGINAL_BLUEPRINT_MAPPING.md](33_ORIGINAL_BLUEPRINT_MAPPING.md) |

## Source-of-truth hierarchy
1. Security and invariants: `AGENTS.md`, [17_SECURITY_AND_THREAT_MODEL.md](17_SECURITY_AND_THREAT_MODEL.md), [11_POLICY_AND_ACTIONS.md](11_POLICY_AND_ACTIONS.md).
2. Current approved milestone: [24_ROADMAP.md](24_ROADMAP.md) and associated `prompts/` file.
3. Domain/API specifications: docs 04–16.
4. Live implementation behavior and tests; discrepancies require doc updates and explicit ADR.

When specs conflict, **do not silently choose**: record conflict and a safe proposed resolution in `docs/IMPLEMENTATION_STATUS.md` before implementing risky behavior.
