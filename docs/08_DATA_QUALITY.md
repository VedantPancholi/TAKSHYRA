# Data contracts, deterministic checks and publication gates

## Concept
A Data Contract is a versioned agreement associated with a dataset or data product, owned by an accountable person/team and enforced independently of the compute engine. In the MVP, rules are typed declarative JSON/YAML, never executable user-provided code.

## Contract v1 fields
`contract_id`, `dataset_ref`, `version`, `owner`, `severity_policy`, `schema_fields`, `primary_key`, `freshness_slo`, `checks[]`, `publish_on_warn` and effective time. Each check has `rule_id`, `type`, `params`, `severity`, `expected`, `applies_to_window`, `contract_version`.

### Required rules and edge cases
| Rule | Calculation / evidence | Edge case |
|---|---|---|
| Freshness | `now - last_source_event_time` or last successful updated window; explicit reference clock | no source rows = UNKNOWN vs FAIL by policy |
| Completeness | observed/expected rows or expected key coverage | missing baseline → UNKNOWN, not zero-loss claim |
| Duplicates | duplicate rows per deterministic key/group | null keys and dedupe window explicit |
| Null rate | null count/non-null eligible rows | empty dataset rule defined |
| Schema | fields/types/missing/unexpected compatibility mode | new optional field vs missing required field |
| Range | min/max and invalid value count | numeric casting failures accounted |
| Distribution | optional PSI/histogram/drift against approved baseline | minimum volume and multiple tests issues |
| Cross-table reconciliation | count/checksum/key reconciliation source → sink | eventual consistency grace period |

## Quality result
Store `rule_id/version`, `expected`, `observed`, `eligible_count`, `outcome PASS/WARN/FAIL/UNKNOWN`, `evidence refs`, `run`, `time_window`, `dataset version`, `evaluation time`. Missing baseline/data or permissions must not masquerade as PASS.

## Publication protocol
1. Write to staging path or temporary manifest/partition location.
2. Compute checksum/row counts/schema fingerprint and evaluate required contract rules.
3. Use policy to decide `PUBLISHED | HELD | QUARANTINED | REJECTED`.
4. Commit a manifest/version pointer atomically where system supports it. On local filesystem use safe rename + transaction reconciliation; explicitly document DB-filesystem atomicity gap and recovery scan.
5. Publish lineage/update downstream signals only after visibility contract; quarantine artifact stays accessible only to authorized reviewers.
6. Overrides require documented exception scope, approver, expiry and audit.

## Data Trust Passport
Show **dimensions**, not just an opaque score: freshness, completeness, schema conformity, uniqueness, last validated timestamp, contract version, owner, last incidents, and downstream consumers. A composite score, if introduced, requires disclosed weights, missing-data handling and calibration. `UNKNOWN` is visually distinct from good.

## Demo failure
A source has 150k expected orders; output has 105k. Transform returns SUCCEEDED, completeness FAIL, publication QUARANTINED, incident opens and downstream consumers are flagged potentially impacted. Data values are synthetic.

## Test requirements
Empty data, missing column, unexpected optional field, transient unavailable source, duplicated keys, null spike, varying timezone boundaries, baseline absent, partition partial, repeated messages, controlled quality override. Every rule tested deterministically.
