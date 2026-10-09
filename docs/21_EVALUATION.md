# Measurable evaluation, benchmarks and proof

## No fabricated claims
All targets and numbers below are **measurement plans** until test results exist. Never advertise specific % improvement, RTO/RPO, financial savings, throughput, cloud usage or AI confidence without repeatable evidence and baseline.

## Operational metrics
| Metric | Definition / method | Potential failure of interpretation |
|---|---|---|
| Detection latency | persisted incident time - injected fault event time | missing monitoring window/outliers |
| Root-cause top-1/top-3 | verified labeled cause in top k | correlated symptoms not same as verified cause |
| Hallucinated evidence rate | agent cites missing/unsupported IDs / outputs | retrieval validation must catch |
| False-positive rate | alerts per healthy labeled window | seasonality and fixture representativeness |
| Verified recovery rate | VERIFIED actions / completed authorized actions | excluding inconclusive inflates results |
| Safety violation rate | executed prohibited actions / adversarial attempts | untested surface gives false reassurance |
| MTTR | resolution timestamp - incident opening | scenario variability and manual baseline |
| Cost/case | actual local compute energy estimate or measured Azure/model expenses / cases | simulated cost clearly labeled |
| Pipeline throughput | rows/s by hardware/data size with p50/p95 | synthetic size does not imply TB-scale |
| API p95 latency | instrumented user endpoints at load | cache, concurrency, warmed state |

## Evaluation protocol
- Freeze scenario suite and expected outcomes in version control; seed random sources.
- Run manual baseline procedures and Takshyra-assisted runs against equivalent fixtures; record who performed them and what instructions differ.
- At least 3 repeated runs for basic performance trends; record CPU, memory, software versions, dataset size, concurrency, filesystem, machine and median/p95.
- Report failures and confidence intervals only where enough observations; never imply statistically strong inference from tiny samples.
- Preserve raw benchmark commands/results in `benchmarks/` once measured and label source/mode/units/time.
- Audit that every proposal and executed recovery has a linked policy decision and verification record.

## Portfolio demonstration scoring rubric
A credible v1 demonstrates reproducibility (25%), safety isolation (25%), verifiable correctness (25%), evidence-rich UX (15%), and deployment/documentation quality (10%). This is an internal evaluation rubric, not an external standard.
