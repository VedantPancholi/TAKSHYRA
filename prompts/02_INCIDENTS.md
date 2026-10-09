# Codex M2 — deterministic fault lab and incidents

Implement typed error taxonomy, transient/persistent failure injection restricted to demo mode, retry budgets and backoff, quality failure/late data incident creation, dedup fingerprint, evidence references, incident lifecycle/timeline, role-protected incident APIs.

**Cases:** F02 transient 503 twice then success, F03 persistent failure with capped attempts, F04 synthetic row drop with execution SUCCEEDED but quality FAIL, F07 missed freshness with no run, repeated alerts not infinite incidents. Each event links to real run/check evidence, not generic LLM prose.

**Tests:** retry count/deadline, explicit UNKNOWN for unsupported inference, duplicate alert increments count, tenant A/B isolation, viewer read-only, redacted evidence, incident can be investigated but not silently resolved. Include seeded deterministic `make demo` or direct command only after implemented.

**Exit:** run→fault→incident data visible through API with accurate timestamps and durable timeline, tests executed and status docs updated.
