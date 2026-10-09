# Requirement-to-proof traceability

| ID | Requirement | Key design doc | Acceptance scenario | Release |
|---|---|---|---|---|
| RQ-001 | Tenant-scoped access | 17, 05, 07 | F08, F09 | R1 |
| RQ-002 | Durable pipeline run | 04, 06 | F01, F13 | R1 |
| RQ-003 | Independent execution/quality/publish axes | 06, 08 | F04 | R1/R3 |
| RQ-004 | Deterministic quality checks | 08 | F04–F07 | R1/R3 |
| RQ-005 | Incident evidence and dedup | 10 | F03–F07 | R2 |
| RQ-006 | Policy action allowlist | 11 | F08, F10, F12 | R2 |
| RQ-007 | Bound approval to payload | 11, 06 | F10, F11 | R2 |
| RQ-008 | OpenLineage-compatible graph | 09 | lineage graph tests | R3 |
| RQ-009 | Blast radius with provenance | 09 | F04 downstream graph | R3 |
| RQ-010 | Structured diagnosis and fallback | 13, 10 | F03, F12 | R4 |
| RQ-011 | Shadow replay | 12 | F16 | R4 |
| RQ-012 | Independent verification | 11, 12 | F02, F16 | R2/R4 |
| RQ-013 | Stream reconciliation | 14 | F14, F15 | R5 |
| RQ-014 | Azure sandbox adapter | 16, 15 | mocked + opt-in live | R5 |
| RQ-015 | Monitoring and measurable improvement | 18, 21 | recorded experiment | R6 |

Every implemented PR should cite `RQ-*` and actual tests; do not check off requirement based solely on a generated file name.
