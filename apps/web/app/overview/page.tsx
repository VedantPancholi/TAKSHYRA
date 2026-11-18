"use client";

import Link from "next/link";
import { Pill, stamp, useWorkspace } from "../workspace-context";

export default function OverviewPage() {
  const { session, incidents, pipelines, recentProposals, brokerStatus, busy, perform, loadIncidents, loadBroker, showIncidents, selectIncident } = useWorkspace();
  if (!session) return null;
  const open = incidents.filter((item) => item.status === "OPEN").length;
  const investigating = incidents.filter((item) => item.status === "INVESTIGATING").length;
  const awaiting = recentProposals.filter((item) => item.status === "AWAITING_APPROVAL").length;

  return <>
    <div className="page-heading">
      <div>
        <div className="eyebrow">COMMAND CENTER / {session.tenant.toUpperCase()}</div>
        <h1>Operations overview</h1>
        <p>Monitor the workspace, prioritize incidents, and move to the right workbench.</p>
        <span className="work-status" role="status">{busy ? "Updating workspace…" : "Workspace ready"}</span>
      </div>
      <button className="outline" onClick={() => void perform(async () => {
        await Promise.all([loadIncidents(session), loadBroker(session)]);
      })} disabled={busy}>↻ &nbsp; Refresh</button>
    </div>
    <section className="metric-row" aria-label="Workspace summary">
      <button type="button" className="metric metric-action" onClick={() => showIncidents("ALL")}>
        <span>INCIDENTS</span><strong>{incidents.length}</strong><small>Open incident center →</small>
      </button>
      <button type="button" className="metric metric-action" onClick={() => showIncidents("OPEN")}>
        <span>OPEN</span><strong>{open}</strong><small>Needs investigation →</small>
      </button>
      <button type="button" className="metric metric-action" onClick={() => showIncidents("INVESTIGATING")}>
        <span>INVESTIGATING</span><strong>{investigating}</strong><small>Review active work →</small>
      </button>
      <Link className="metric metric-action" href="/actions">
        <span>AWAITING APPROVAL</span><strong>{awaiting}</strong><small>Open action queue →</small>
      </Link>
    </section>
    <div className="section-top"><div><div className="eyebrow">WORKSPACE / MODULES</div><h2>Choose your next step</h2></div></div>
    <section className="module-grid" aria-label="Workspace modules">
      <Link className="module-card" href="/incidents"><span>01 / DETECT</span><h3>Incident center</h3><p>Investigate evidence, impact, diagnosis, and recovery options.</p><b>Open incidents →</b></Link>
      <Link className="module-card" href="/pipelines"><span>02 / OPERATE</span><h3>Pipelines</h3><p>See the registered local pipelines and their incident workload.</p><b>{pipelines.length} available →</b></Link>
      <Link className="module-card" href="/streaming"><span>03 / OBSERVE</span><h3>Streaming</h3><p>Inspect synthetic telemetry and local broker delivery.</p><b>{brokerStatus ? `${brokerStatus.failures} flagged events` : "Open telemetry"} →</b></Link>
      <Link className="module-card" href="/actions"><span>04 / RESPOND</span><h3>Governed actions</h3><p>Review exact proposals, approvals, execution, and verification.</p><b>Open workbench →</b></Link>
    </section>
    <div className="section-top"><div><div className="eyebrow">RECENT SIGNALS</div><h2>Latest incidents</h2></div><Link className="text-button" href="/incidents">View all →</Link></div>
    <section className="panel overview-activity" aria-label="Latest incidents">
      {incidents.length ? incidents.slice(0, 5).map((item) => <button key={item.id} type="button" onClick={() => { selectIncident(session, item); showIncidents("ALL"); }}>
        <span><strong>{item.error_code}</strong><small>{item.category.replaceAll("_", " ")} · {stamp(item.last_seen_at)}</small></span>
        <Pill value={item.severity} /><Pill value={item.status} /><span className="activity-arrow">→</span>
      </button>) : <p className="empty">No incidents yet. The incident center has the local demo controls.</p>}
    </section>
  </>;
}
