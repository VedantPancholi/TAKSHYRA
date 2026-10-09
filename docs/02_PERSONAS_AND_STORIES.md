# Personas, permissions and user journeys

| Persona | Need | Success story | Role |
|---|---|---|---|
| Data Engineer | Investigate a broken dataset | Opens incident, inspects evidence, proposes scoped replay | DATA_ENGINEER |
| Platform Engineer / SRE | Reliability across jobs and streams | Detects lag and failure patterns, uses runbooks | PLATFORM_ENGINEER |
| Data Product Owner | Trust in business data | Sees passport, impacted assets and freshness deadline | PRODUCT_OWNER |
| Approver / Lead | Control operational risk | Reviews exact diff, approves or denies action | APPROVER |
| Tenant Admin | Manage access and data connections | Grants roles within own tenant | TENANT_ADMIN |
| Auditor | Complete decision trail | Exports redacted provenance timeline read-only | AUDITOR |
| Viewer | Understand status | Can read scoped assets, never mutate | VIEWER |

## Core jobs with acceptance conditions
1. **Onboard:** create tenant, user, authorized membership, pipeline and dataset; no client-controlled privilege escalation.
2. **Run batch:** run synthetic orders pipeline; inspect source/output counts, quality checks and output manifest.
3. **Detect silent loss:** transform completes, row count contract fails, downstream publishing remains HELD or QUARANTINED.
4. **Investigate:** incident shows run, quality evidence, source version change, ranked hypotheses and uncertainty.
5. **Understand impact:** identify known dependent reports/model, graph displays inferred versus declared edge.
6. **Review recovery:** show affected date/partition, exact action payload, policy, approval expiry, estimated side effects.
7. **Execute & verify:** after authorized execution, reconcile records and mark VERIFIED or INCONCLUSIVE; preserve all audit events.
8. **Learn:** search prior verified causes and link them to current analysis without cross-tenant leakage.

## Permissions principle
Permissions split **read**, **execute pipeline**, **propose**, **approve**, **execute allowlisted action**, **manage connector**, **manage membership**, **audit**. Roles map to permissions on backend. No user may self-approve a high-risk action. Default deny.
