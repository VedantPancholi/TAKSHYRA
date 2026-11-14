# M7 diagnosis, first slice

M7 records evidence-linked hypotheses. Rules work without a model. An optional local Ollama provider can suggest structured hypotheses; its output never confirms a cause or changes policy and action authority.

## Local API and console

- `GET /api/v1/incidents/{id}/diagnoses` returns up to 20 recent revisions for a tenant member.
- `POST /api/v1/incidents/{id}/diagnoses` lets an executor generate a diagnosis from the current incident, run and quality records. It accepts no client-supplied evidence or free-form instructions. An assigned incident can only be diagnosed by its owner.
- A matching evidence snapshot returns the existing diagnosis. A changed incident observation or run/check state creates a new record.
- The operations console shows the latest diagnosis and a **Generate diagnosis** button for executors.

Rules cover row deficits, simulated freshness misses and source read failures. Each result is marked `HYPOTHESIS`, cites stored evidence IDs and lists unknowns and a next check. Unmatched evidence yields `UNKNOWN` with no invented cause. The method is recorded as `RULES_V1`.

## Optional local model

The default `.env` value is `TAKSHYRA_DIAGNOSIS_PROVIDER=rules`. To opt in, run Ollama locally, install a model of your choice, and set `TAKSHYRA_DIAGNOSIS_PROVIDER=ollama` and `TAKSHYRA_OLLAMA_MODEL=<installed-model-name>` in ignored `.env`. The Docker API reaches the local host at `http://host.docker.internal:11434`; a native API process may use `TAKSHYRA_OLLAMA_BASE_URL=http://127.0.0.1:11434`. Only these local hostnames and port 11434 are accepted. Recreate the API container after changing Compose environment values.

The request sends only server-created incident, run and check identifiers and bounded status codes. It excludes raw rows, observed values, notes, credentials and full prompts. It asks Ollama's `/api/generate` for a JSON-schema result with streaming disabled, an eight-second timeout and bounded response size. The server validates the schema, allowed evidence IDs, category, confidence label and next-check enum. Invalid, timed-out or unavailable responses fall back to rules. The diagnosis response reports `method`, `model_id` and `provider_status`; an existing model result is reused for unchanged evidence and model name. Model text stays advisory.

No Ollama process or model is bundled with Compose. Without one, leave the provider on `rules`; the incident, policy and pipeline flows continue normally.

## Verified memory in M8

- M8 retrieves up to three independently verified recovery outcomes for later incidents with the same error code in the same tenant. These are evidence of a previous local repair, not proof of the new incident's cause. See [M8 shadow recovery](44_M8_SHADOW_RECOVERY.md).
- Expand labeled evaluation fixtures when real connector evidence exists. The current tests cover no-model operation, missing evidence IDs, forbidden output fields, unsafe next checks, local-only endpoint configuration and model fallback.

Do not present these hypotheses as confirmed causes. The demo pipeline and its faults remain synthetic.
