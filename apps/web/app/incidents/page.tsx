"use client";

import Link from "next/link";
import { Pill, stamp, useWorkspace } from "../workspace-context";

export default function Page() {
  const { session, incidents, selected, incidentView, setIncidentView,
    diagnosis, shadowReplay, incidentSearch, setIncidentSearch, incidentStatus,
    setIncidentStatus, incidentSeverity, setIncidentSeverity, demoPipeline, busy,
    createDemo, createRowDeficit, selectIncident, diagnose, replayIncident,
    investigate, impactItems, filteredIncidents, canExecute } = useWorkspace();
  if (!session) return null;
  return (
    <>
          <div className="page-heading">
            <div>
              <div className="eyebrow">WORKSPACE / INCIDENTS</div>
              <h1>Incident center</h1>
              <p>Filter the queue, inspect evidence, and prepare a governed response.</p>
            </div>
            {canExecute && (
              <div className="button-row">
                <button className="outline" onClick={() => createDemo(session)} disabled={busy || !demoPipeline}>
                  + Create freshness incident
                </button>
                <button className="outline" onClick={() => createRowDeficit(session)} disabled={busy || !demoPipeline}>
                  + Create row deficit run
                </button>
              </div>
            )}
          </div>
          <section className="work-grid">
            <div className="panel incident-list">
              <div className="panel-heading">
                <strong>Live incident queue</strong>
                <span>{filteredIncidents.length} of {incidents.length} records</span>
              </div>
              <div className="incident-filters">
                <input aria-label="Search incidents" placeholder="Search code, category or ID" value={incidentSearch} onChange={(event) => setIncidentSearch(event.target.value)} />
                <select aria-label="Filter incident status" value={incidentStatus} onChange={(event) => setIncidentStatus(event.target.value)}>
                  <option value="ALL">All statuses</option>
                  <option value="OPEN">Open</option>
                  <option value="INVESTIGATING">Investigating</option>
                  <option value="RESOLVED">Resolved</option>
                </select>
                <select aria-label="Filter incident severity" value={incidentSeverity} onChange={(event) => setIncidentSeverity(event.target.value)}>
                  <option value="ALL">All severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
                {(incidentSearch || incidentStatus !== "ALL" || incidentSeverity !== "ALL") && (
                  <button className="filter-clear" type="button" onClick={() => {
                    setIncidentSearch("");
                    setIncidentStatus("ALL");
                    setIncidentSeverity("ALL");
                  }}>Clear</button>
                )}
              </div>
              {incidents.length === 0 ? (
                <div className="empty">
                  No incidents yet.{" "}
                  {canExecute
                    ? "Create a simulated freshness incident to try the workflow."
                    : "Ask an executor to start the demo scenario."}
                </div>
              ) : filteredIncidents.length === 0 ? (
                <div className="empty">No incidents match these filters. Clear the search or choose another status.</div>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Incident</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Last seen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIncidents.map((item) => (
                        <tr
                          key={item.id}
                          className={selected?.id === item.id ? "selected" : ""}
                        >
                          <td>
                            <button
                              className="row-button"
                              onClick={() => selectIncident(session, item)}
                            >
                              <strong>{item.error_code}</strong>
                              <small>
                                {item.category.replaceAll("_", " ")} ·{" "}
                                {item.id.slice(0, 8)}
                              </small>
                            </button>
                          </td>
                          <td>
                            <Pill value={item.severity} />
                          </td>
                          <td>
                            <Pill value={item.status} />
                          </td>
                          <td className="muted">{stamp(item.last_seen_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="panel detail-panel">
              <div className="panel-heading">
                <strong>Incident brief</strong>
                <span>
                  {selected ? selected.id.slice(0, 8) : "Select an incident"}
                </span>
              </div>
              {!selected ? (
                <div className="empty">
                  Select an incident to inspect evidence, impact and available
                  actions.
                </div>
              ) : (
                <>
                  <div className="detail-title">
                    <div>
                      <div className="eyebrow">
                        {selected.category.replaceAll("_", " ")}
                      </div>
                      <h3>{selected.error_code}</h3>
                    </div>
                    <Pill value={selected.status} />
                  </div>
                  <div className="fact-grid">
                    <div>
                      <span>SEVERITY</span>
                      <Pill value={selected.severity} />
                    </div>
                    <div>
                      <span>OCCURRENCES</span>
                      <strong>{selected.occurrence_count}</strong>
                    </div>
                    <div>
                      <span>PROVENANCE</span>
                      <strong>{selected.provenance}</strong>
                    </div>
                    <div>
                      <span>LAST SEEN</span>
                      <strong>{stamp(selected.last_seen_at)}</strong>
                    </div>
                  </div>
                  <div className="detail-tabs" aria-label="Incident information">
                    {(["overview", "evidence", "recovery"] as const).map((view) => (
                      <button
                        key={view}
                        type="button"
                        className={incidentView === view ? "active" : ""}
                        aria-pressed={incidentView === view}
                        onClick={() => setIncidentView(view)}
                      >
                        {view === "overview" ? "Overview" : view === "evidence" ? "Evidence" : "Recovery"}
                      </button>
                    ))}
                  </div>
                  {incidentView === "overview" && <>
                  <div className="detail-block">
                    <h4>Potential downstream impact</h4>
                    <p>
                      Lineage indicates possible reach, not confirmed damage.
                    </p>
                    {impactItems.length ? (
                      <ul className="impact-list">
                        {impactItems.map((asset, index) => (
                          <li key={asset.id ?? index}>
                            {asset.name ?? asset.id}{" "}
                            <small>{asset.impact_type ?? "POTENTIAL"}</small>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">
                        No affected assets reported for this incident.
                      </p>
                    )}
                  </div>
                  <div className="detail-block">
                    <h4>Diagnosis</h4>
                    {diagnosis ? (
                      <>
                        <p><Pill value={diagnosis.status} /> {diagnosis.method} · {stamp(diagnosis.created_at)}</p>
                        <p className="muted">Provider: {diagnosis.provider_status.replaceAll("_", " ")}{diagnosis.model_id ? ` · ${diagnosis.model_id}` : ""}</p>
                        {diagnosis.hypotheses.length ? diagnosis.hypotheses.map((item) => (
                          <div key={item.category}>
                            <p><strong>{item.summary}</strong> ({item.confidence_label.toLowerCase()} confidence)</p>
                            <p className="muted">Evidence: {item.supporting_evidence_refs.join(", ")}</p>
                            <p className="muted">Unknown: {item.unknowns.join(" ")}</p>
                            <p className="muted">Next check: {item.next_checks.join(" ")}</p>
                          </div>
                        )) : <p className="muted">The current evidence supports no specific cause.</p>}
                        {diagnosis.memory_status === "NO_VERIFIED_OUTCOMES" && (
                          <p className="muted">No independently verified prior cases are available yet.</p>
                        )}
                        {diagnosis.similar_cases.map((item) => (
                          <p key={item.id} className="muted">Verified prior case {item.id.slice(0, 8)}: {item.summary}</p>
                        ))}
                      </>
                    ) : <p className="muted">No diagnosis has been recorded for this incident.</p>}
                    {canExecute && (
                      <button className="secondary" onClick={() => diagnose(session)} disabled={busy}>
                        {diagnosis ? "Refresh diagnosis" : "Generate diagnosis"}
                      </button>
                    )}
                  </div>
                  <div className="detail-block detail-next-step">
                    <Link href="/actions">Review governed actions <span aria-hidden="true">→</span></Link>
                    <p>Actions are evaluated by policy before execution.</p>
                  </div>
                  </>}
                  {incidentView === "recovery" && <>
                  <div className="detail-block">
                    <h4>Shadow replay</h4>
                    <p className="muted">Replay the fixed local source in scratch space to test whether the missing row can be restored.</p>
                    {shadowReplay ? (
                      <p><Pill value={shadowReplay.status} /> {shadowReplay.reason.replaceAll("_", " ")}. Rows: {shadowReplay.baseline_row_count ?? "?"} → {shadowReplay.replay_row_count ?? "?"}.</p>
                    ) : <p className="muted">No replay recorded for this incident.</p>}
                    {canExecute && selected.status !== "RESOLVED" && selected.run_id && (
                      <button className="secondary" onClick={() => replayIncident(session)} disabled={busy}>Run shadow replay</button>
                    )}
                  </div>
                  </>}
                  {incidentView === "evidence" && <>
                  <div className="detail-block">
                    <h4>Evidence timeline</h4>
                    {selected.timeline?.length ? (
                      <ol className="timeline">
                        {selected.timeline.map((event, index) => (
                          <li key={index}>
                            <b>{event.code}</b>
                            <span>{stamp(event.occurred_at)}</span>
                            {event.safe_detail && <p>{event.safe_detail}</p>}
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="muted">No timeline events are available.</p>
                    )}
                    {selected.timeline_truncated && (
                      <p className="muted">Showing the first 100 events.</p>
                    )}
                  </div>
                  </>}
                  {canExecute && selected.status === "OPEN" && (
                    <button
                      className="secondary"
                      onClick={() => investigate(session)}
                      disabled={busy}
                    >
                      Start investigation →
                    </button>
                  )}
                </>
              )}
            </div>
          </section>
    </>
  );
}
