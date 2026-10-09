# Codex M7 — optional AI diagnosis and verified memory

Add deterministic diagnosis first using structured evidence, previous runs, schema/config changes and quality results. Rank hypotheses with evidence links, counter-evidence, confidence **labels** (not calibrated probability) and next checks. Implement bounded agent coordinator and typed Pydantic output; default offline mode needs zero paid APIs. Add optional local Ollama behind feature flag with timeouts and fallback.

Store verified incident resolution memory separate from provisional cases, with tenant scope, staleness, provenance and explicit human/verification criteria. Retrieval is advisory only; no output is an instruction to policy or executor.

**Tests:** invalid model JSON, timeout, model unavailable, hallucinated evidence reference rejected, prompt-injection in logs, tenant memory leakage, repeated model attempts bounded, actual deterministic fallback. Run agent evaluation fixture and report results honestly.

**Exit:** incident has evidence-backed hypotheses, trustworthy fallback and memory lookup; not just a chatbot that generates anecdotes.
