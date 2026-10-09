# Codex M4 — versioned contracts and publication gate

Implement Dataset and immutable DataContractVersion for synthetic orders; typed rules for schema required/optional, expected count, null rate, duplicate key, basic freshness. Build staged Parquet output manifest; evaluate required checks before publishing. Run execution, quality and publication statuses must remain independent in DB and API.

**Cases:** clean dataset PUBLISHED; row count drops 30% → technically SUCCEEDED, quality FAIL, publication QUARANTINED; missing required schema field fails; unexpected optional field follows compatibility setting; unavailable baseline UNKNOWN rather than PASS. Retain unauthorized artifact access denial.

**Exit:** repeatable end-to-end quality gate and visible manifest/quarantine, no half-published output, versioned contract check evidence, relevant unit/integration/auth tests pass.
