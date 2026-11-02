# M6 local operations console

M6 adds a Next.js and TypeScript console at `http://127.0.0.1:3000`. It reads the existing tenant-scoped APIs through a small same-origin proxy. The proxy accepts only the routes used by the workbench, forwards Basic credentials and tenant slug for each request, limits JSON request size, and does not store a session. The API remains responsible for authentication, tenant membership, role checks, policy, approval and action execution.

## Start and verify

Keep the seven distinct local passwords in ignored `.env`, then run:

```powershell
docker compose up --build -d --wait
docker compose exec -T api python scripts/smoke_m6.py
```

Docker is enough for the app. Node 22 and npm are only needed for a native web development loop; from `apps/web`, use `npm ci`, `npm run typecheck`, and `npm run build`. The checked-in `package-lock.json` is required for reproducible builds.

## Web journey

1. Sign in as `demo-a-executor` with the password in `.env`, tenant `demo-a`. Credentials live only in this browser tab's memory and are cleared on account switch or reload.
2. Select an existing incident or create the fixed simulated freshness incident. Inspect its timeline and potential downstream impact. An executor may mark an open incident investigating.
3. Select `incident.annotate`, enter a short note, and evaluate the proposal. Review the server policy decision and exact payload digest, then execute. The UI shows the server's verification result.
4. To exercise approval, select `pipeline.pause_demo` for an incident's pipeline. Record the proposal ID, switch to `demo-a-approver`, open the same ID, and approve the exact payload. Switch back to the original executor, open the ID and execute. This action only records a simulated pause marker; it does not stop the worker.
5. Sign in as `demo-a-viewer` to inspect incidents and proposals. Proposal, investigation and execution controls are unavailable. The API also rejects those writes with `403`.

The UI displays actual tenant API records, including empty and error states. No demo dashboard counts are fabricated. It does not implement production identity, persistent sessions, a full pipeline registry, customer-system actions or incident resolution. Keep the stack bound to loopback development ports.
