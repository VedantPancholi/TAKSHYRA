"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Pill, useWorkspace } from "../workspace-context";

export default function PipelinesPage() {
  const router = useRouter();
  const { session, pipelines, demoPipeline, incidents, canExecute, busy, createRowDeficit, selectIncident } = useWorkspace();
  if (!session) return null;

  return <>
    <div className="page-heading">
      <div><div className="eyebrow">WORKSPACE / PIPELINES</div><h1>Pipelines</h1><p>Registered pipelines and the incidents linked to their runs.</p></div>
      {canExecute && <button className="outline" disabled={busy || !demoPipeline} onClick={() => createRowDeficit(session)}>+ Create local row deficit run</button>}
    </div>
    <div className="scope-banner"><strong>Local demo registry</strong><span>This page shows the API pipeline list. Run history and cloud provider controls are not available in this demo.</span></div>
    <section className="pipeline-grid" aria-label="Registered pipelines">
      {pipelines.length ? pipelines.map((pipeline) => {
        const linked = incidents.filter((item) => item.pipeline_id === pipeline.id);
        const unresolved = linked.filter((item) => item.status !== "RESOLVED");
        return <article className="panel pipeline-card" key={pipeline.id}>
          <div className="pipeline-card-top"><span className="eyebrow">REGISTERED PIPELINE</span><Pill value={unresolved.length ? "OPEN" : "NO ACTIVE INCIDENTS"} /></div>
          <h2>{pipeline.name}</h2>
          <p className="muted">{pipeline.source_kind.replaceAll("_", " ")}</p>
          <p className="mono muted">{pipeline.id}</p>
          <div className="pipeline-facts"><div><span>LINKED INCIDENTS</span><strong>{linked.length}</strong></div><div><span>UNRESOLVED</span><strong>{unresolved.length}</strong></div></div>
          <div className="pipeline-recent"><h3>Recent signals</h3>
            {linked.length ? linked.slice(0, 3).map((incident) => <button key={incident.id} type="button" onClick={() => { selectIncident(session, incident); router.push("/incidents"); }}>
              <span>{incident.error_code}</span><Pill value={incident.status} /><span aria-hidden="true">→</span>
            </button>) : <p className="muted">No linked incidents in this tenant.</p>}
          </div>
          <Link className="pipeline-link" href="/incidents">Open incident center →</Link>
        </article>;
      }) : <div className="panel empty">No pipelines are registered for this tenant.</div>}
    </section>
  </>;
}
