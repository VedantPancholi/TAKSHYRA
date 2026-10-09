# Connector contracts, capabilities and error taxonomy

## Goal
Observe existing systems through narrow, separately testable adapters. The control plane is portable without rewriting core incident or policy semantics for each cloud/tool.

## Versioned interface (conceptual Python)
```python
class ConnectorCapabilities(Protocol):
    can_read_runs: bool
    can_trigger_run: bool
    can_read_metrics: bool
    can_replay_window: bool
    can_read_lineage: bool

class PipelineObserver(Protocol):
    async def list_runs(self, scope: RunQuery) -> Page[ObservedRun]: ...
    async def get_run(self, identity: ExternalRunIdentity) -> ObservedRun: ...

class PipelineActionAdapter(Protocol):
    async def execute_allowlisted(self, action: AuthorizedAction) -> ExternalOperationReceipt: ...
    async def reconcile_operation(self, receipt: ExternalOperationReceipt) -> ActionOutcome: ...
```
These are architectural contracts, **not presently importable code**.

## Connector metadata
`connector_id`, `tenant_id`, `kind`, `mode MOCK | SANDBOX_LIVE | PRODUCTION_READ_ONLY`, `capabilities`, `secret_reference`, `resource_allowlist`, `last_sync`, `health`, `permission_scope`, `rate_limits`, `version`. No plaintext credentials.

## Error taxonomy
`AUTHORIZATION`, `BAD_CONFIGURATION`, `SCHEMA_INCOMPATIBILITY`, `SOURCE_THROTTLED`, `TRANSIENT_NETWORK`, `SOURCE_UNAVAILABLE`, `DESTINATION_UNAVAILABLE`, `TIMEOUT`, `CONTRACT_FAILURE`, `CHECKPOINT_MISSING`, `RETENTION_EXPIRED`, `UNKNOWN`.

Retry only retryable categories with max attempts/deadlines. Unknown is not automatically retryable. Preserve original provider error reference safely and return redacted user message.

## Connector compliance tests
- Contract schema validation, rate limits, paging, upper bounds, timeouts, cancellation.
- Secret redaction, tenant scoping, narrow Azure permission envelope.
- Read-only connector cannot mutate.
- Retry/double-delivery is idempotent when adapter supports it; otherwise action must require reconciliation before retry.
- Mock fixtures match external contract shape; live tests separately gated.

## Prioritization
LocalRunner (R1) → ADF read-only (R5) → Azure Monitor metrics (R5) → Kafka event reader (R5) → Event Hubs sandbox reader (R5) → ADLS/ClickHouse optional later. Do not promise every connector in v1.
