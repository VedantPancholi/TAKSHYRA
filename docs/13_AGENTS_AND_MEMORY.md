# Agent roles, orchestration, incident memory and evaluation

## Operating principle
Deterministic services compute checks, policy decisions and execution results. AI agents synthesize evidence, investigate hypotheses, rank next checks and draft bounded proposals. Never call an LLM merely to perform a deterministic count or role check.

## Roles
| Component | Inputs | Outputs | Trust level |
|---|---|---|---|
| Monitoring service | run events, metrics, contract results | incident candidate | deterministic |
| Quality service | bounded dataset sample/aggregate, contract | checked assertion list | deterministic |
| Diagnosis agent | redacted evidence, changes, similar cases | ranked structured hypotheses | untrusted advisory |
| Blast-radius service | lineage graph, target incident | paths to impacted assets | deterministic graph / labeled inference |
| Remediation planner | incident, verified constraints, action catalog | typed action proposal | untrusted advisory |
| Policy engine | proposal, actor, target, current state | ALLOW/DENY/REQUIRES_APPROVAL | deterministic authority |
| Replay worker | allowlisted sandbox action | before/after evidence | isolated execution |
| Verification service | original incident invariant, new outputs | VERIFIED/FAILED/INCONCLUSIVE | deterministic authority |
| Incident memory | verified records + sanitized search query | reference-only prior cases | advisory retrieval |
| Cost insight | real usage or marked synthetic samples | estimates and opportunities | advisory |

## AgentExecution contract
`agent_type`, `agent_version`, `input_evidence_ids`, `prompt_version`, `model_id/provider`, `max_tokens`, `deadline_ms`, `output_schema_version`, `structured_output`, `validation_failures`, `confidence_label`, `created_at`, `trace_id`. Only store safe/redacted summaries; no full sensitive prompts.

## Coordinator
One bounded DAG, not agents freely chatting indefinitely: gather evidence → deterministic checks → optional similarity retrieval → optional diagnosis LLM → validate output → remediation proposal → policy service. Max steps, max concurrent calls, timeouts, token/compute budget, cancellation and fallback. Record partial/unavailable results without blocking core pipeline execution.

## Memory design
Use PostgreSQL as record of verified incident outcomes; pgvector optional after proven need. `KnowledgeRecord` has tenant, fingerprint/tags, verified cause, supporting evidence, action and outcome, verifier, version, date, expiry. Store provisional cases separately. Retrieval matches authorized tenant and returns citations to internal safe evidence IDs. Never allow retrieved text to become a tool instruction or override current policy. Add stale record warnings.

## Injection defense
Adversarial data can say 'ignore policies' or mimic system messages. Treat all source data, logs, filenames and search results as **data**. Structured response parser accepts only documented fields and action enum; rejects arbitrary tool names/URLs/code. Sensitive logging and external model requests disabled without explicit opt-in.

## Deterministic fallback
When Ollama/hosted LLM absent, generate rule-based hypotheses: HTTP 429=rate limit; DNS/timeouts=transient connectivity; schema fingerprint mismatch=schema hypothesis; row deficit=quality incident; never automatically assert verified cause without independent evidence.

## Model evaluation
Create labeled fixtures with known causes and distractors; top-k cause recall, hallucinated evidence count, invalid proposal rate, unsafe-action proposals, false confirmations, latency and per-case cost. Avoid claiming calibrated numeric confidence without labeled calibration set.
