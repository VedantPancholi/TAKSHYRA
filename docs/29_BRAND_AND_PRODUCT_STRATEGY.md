# Brand and product naming

## Chosen identity

**TAKSHYRA**
**Tagline:** Intelligence Behind Every Decision.

| Name | Role | Current implementation |
|---|---|---|
| **Takshyra Data Reliability Platform** | Customer-facing product | M1 local core only; broader platform remains planned. |
| **Takshyra AI** | Technology umbrella | Planned; no required LLM or AI service in M1. |
| **Takshyra Core** | Developer platform and local runtime | Current Python API, worker, migrations, deterministic pipeline and tests. |
| **Takshyra Insight** | AI investigation engine | Planned for the diagnosis milestone; not implemented. |
| **Takshyra Guardian** | Governed recovery capability | Planned; no autonomous mutation or production recovery is implemented. |

The product category remains a Data Reliability Control Plane. The value proposition is to detect data incidents, understand potential impact, evaluate safe actions and verify outcomes with evidence. Product language must distinguish observed, derived, estimated, simulated and unavailable facts.

## Naming rules

- Use **TAKSHYRA** for the primary brand mark and **Takshyra** in prose and component names.
- Use **Takshyra Core** for the implemented developer runtime. The Python distribution is `takshyra-core`; imports use `takshyra`.
- Do not label deterministic checks or templates as Takshyra AI or Insight. Do not label a proposed or approved action as a verified Guardian recovery.
- “Autonomous recovery” is a product direction, not a present capability or permission. The security and policy gates in `AGENTS.md`, `docs/11_POLICY_AND_ACTIONS.md` and `docs/17_SECURITY_AND_THREAT_MODEL.md` still apply before any mutating recovery action.

## Commercial validation

This repository does not establish trademark, company, package-registry or domain availability. Complete the relevant checks before commercial launch. Initial users are data engineering and platform teams using local batch systems and, later, supported cloud/streaming adapters. Discovery interviews, pricing and comparative claims remain hypotheses until measured.
