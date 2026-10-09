# Codex M0 — inspect, reconcile and plan

**Instruction:** Inspect every existing source/config/doc file relevant to R1 before writing implementation. Confirm this is documentation-only unless you actually find running code. List checked tooling and versions, Git branch/status and dependency constraints. Read root `AGENTS.md`, `CODEX_MASTER_PROMPT.md`, `docs/04_ARCHITECTURE.md`, `docs/17_SECURITY_AND_THREAT_MODEL.md`, `docs/22_LOCAL_DEV.md`, `docs/24_ROADMAP.md`.

1. Create/update `docs/IMPLEMENTATION_STATUS.md` with exact inventory, explicitly unimplemented parts, tool availability and risks.
2. Propose minimal M1 packages and database schema (Tenant/User/Membership/PipelineDefinition/Run/Attempt/QualityResult/AuditEvent). Choose worker implementation with reasons and document state handling.
3. Resolve Linux/macOS/Windows commands. Verify baseline blueprint check before changing anything.
4. Create ADR for any architectural deviation.
5. Then proceed to M1 in same session if tools permit; never pretend M1 passes without executing checks.

**Exit:** documented plan plus verified environment inventory; no claim of runtime API.
