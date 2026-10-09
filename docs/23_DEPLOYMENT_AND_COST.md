# Deployment, cost tiers and operating constraints

## Local-first economics
Development can be ₹0 in software/cloud subscription fees if using your own machine, open-source tools and synthetic data. Electricity, disk, hardware, Internet and optional model downloads still have costs. Check licenses of code, containers, models and commercial redistribution before monetization.

## Environment modes
`LOCAL_DEMO` (default, synthetic, no cloud), `SANDBOX_LIVE` (explicit cloud testing, budgeted), `PRODUCTION_READ_ONLY` (only after serious review), `PRODUCTION_CONTROLLED` (future, not MVP). Mode set server-side and immutable during action execution; agents cannot elevate mode.

## Sandbox guardrails
- Separate Azure resource group and subscription when possible; least privilege and deny-lists/allowlists.
- Estimated cost budget, actual billing alerts and teardown instructions; alerts are **not** guaranteed spending caps.
- Opt-in live integration test marker and CI disabled by default.
- Terraform `plan` review required; no automatic `apply`, `destroy` or permission escalation.
- Managed Identity / Key Vault references for hosted resources.

## Future deployment architecture
Build secure images, run least privilege (non-root), TLS termination, controlled ingress, migrations, readiness probes, backup and restore testing, encrypted transport, retention policies, dependency scanning, actual monitoring and paging. Separate environments and credentials. Avoid calling a single Compose VPS an enterprise production deployment.

## Cost dimensions to measure
API/worker CPU/memory; PostgreSQL/storage; log/trace retention; stream throughput/retention; per-incident LLM tokens if configured; shadow replay compute and I/O; Azure ADF/Monitor/Event Hubs/API calls and data egress. Label estimated/simulated/real separately.

## Before connecting customer data
Formal threat review, vendor security review, privacy/data processing terms, incident response owner, backup/restore objectives, independent penetration testing, tenant isolation review, authorization tests, per-tenant retention and deletion, on-call / SLOs. Never claim regulatory certification merely from using encryption or RBAC.
