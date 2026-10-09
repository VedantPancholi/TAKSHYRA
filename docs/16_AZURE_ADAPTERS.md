# Azure integration roadmap — optional, paid-resource-aware

## Principle
The local system works without Azure subscription, credentials, or paid service. Azure adapters are capability-gated and mocked in normal CI. **Never provision or mutate cloud resources automatically.** Live tests run only after explicit sandbox setup, budget checks, and user opt-in.

## Azure Data Factory (ADF)
- Read-only first: list selected pipeline runs, activity runs, durations, status, failures and basic safe parameter metadata.
- Validate Entra identity, subscription and resource-group allowlists, paging, API retry headers, time range and response limit.
- Triggering a sandbox pipeline is a later typed action with policy, exact pipeline parameters, approval if warranted, resource allowlist and operation reconciliation; not a free-form REST call from agents.
- Normalize raw Azure state to internal ObservedRun without leaking sensitive activity inputs/outputs.

## Azure Monitor / Application Insights
- Use controlled, bounded query templates for metrics/logs and map correlation ID. Restrict workspace/resources and time windows, cap rows and redact returned secrets.
- Alert correlation must not claim data quality if only infrastructure health is observed.

## Azure Event Hubs
- Separate test consumer group; document partition, checkpoint store, retention, duplicate delivery, event time vs process time and replay rules.
- Implement read-only stream-health observations before replay. Replay never moves production consumer-group checkpoints.

## ADLS Gen2 and Blob
- Default local Parquet output. Cloud adapter uses least privilege with managed identity where supported. No public storage containers.
- Store approved artifact/manifest references not SAS tokens in UI, prompts or audit payloads.
- Snapshot retention, versioning and encryption/ACL assumptions must be documented and verified, not assumed.

## Azure Functions
- Optionally observe bounded function invocations, exceptions and Application Insights traces. Do not require Azure Functions deployment for local application.

## Microsoft Fabric Real-Time Intelligence
- Optional evaluation of supported official Eventstream/Eventhouse/KQL data access/monitoring capabilities. Do **not** invent operations endpoints or promise privileged actions absent public APIs and tested permissions.

## Identity & secrets
- Local demo auth first; Entra ID/OIDC later with strict issuer, audience, exp, group/role and tenant mapping.
- On Azure hosting use Managed Identity and Key Vault references. No client secrets in frontend or LLM prompts.
- Document tenant boundary both application-side and in Azure resource scope.

## Live test readiness checklist
- Dedicated sandbox subscription/resource group and test datasets.
- Budgets, alerts, quota and cleanup plan; zero-cost not guaranteed.
- Exact minimal roles, scopes and resource allowlist reviewed.
- `ENABLE_LIVE_AZURE_TESTS=true` plus explicit target IDs; CI default false.
- Separate `@pytest.mark.azure_live` and timeout/cleanup; no destructive changes.
- Document actual Azure SDK/API versions used at implementation time.

## Reference links
- ADF REST API: https://learn.microsoft.com/en-us/rest/api/datafactory/
- Azure Event Hubs: https://learn.microsoft.com/en-us/azure/event-hubs/
- Managed identities: https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview
- Azure Key Vault: https://learn.microsoft.com/en-us/azure/key-vault/general/overview

Treat official docs as authoritative for supported features, pricing and role scope; recheck during implementation because details evolve.
