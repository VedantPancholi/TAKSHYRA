"use client";

import { Pill, stamp, useWorkspace } from "../workspace-context";

export default function Page() {
  const { session, streamScenario, setStreamScenario, streamObservation,
    brokerScenario, setBrokerScenario, brokerStatus, canExecute, busy,
    runStreamScenario, runBrokerScenario, perform, loadBroker, loadIncidents } = useWorkspace();
  if (!session) return null;
  return (
    <>
          <div className="page-heading">
            <div>
              <div className="eyebrow">WORKSPACE / STREAMING</div>
              <h1>Streaming</h1>
              <p>Inspect synthetic telemetry checks and the local Redis broker.</p>
            </div>
            <span className="section-aside">Synthetic events · local environment</span>
          </div>
          <div className="section-top"><div><div className="eyebrow">01 / CHECK</div><h2>Telemetry scenarios</h2></div></div>
          <section className="panel stream-lab" aria-label="Synthetic stream checks">
            <div>
              <p className="muted">Run a bounded telemetry scenario. The decoder, lag, dead-letter count and source-to-sink totals are checked before an incident is recorded.</p>
              {canExecute && <div className="stream-controls">
                <select aria-label="Stream scenario" value={streamScenario} onChange={(event) => setStreamScenario(event.target.value)}>
                  <option value="SCHEMA_V15">Schema v15 arrives at v14 decoder</option>
                  <option value="SINK_GAP">Sink misses an acknowledged event</option>
                  <option value="CONSUMER_LAG">Consumer falls behind</option>
                  <option value="LATE_EVENT">Late event</option>
                  <option value="DUPLICATE">Duplicate delivery, safely deduplicated</option>
                  <option value="CLEAN">Clean stream</option>
                </select>
                <button className="secondary" disabled={busy} onClick={() => runStreamScenario(session)}>Run local check</button>
              </div>}
            </div>
            <div className="stream-result">
              {streamObservation ? <>
                <p><Pill value={streamObservation.status} /> {streamObservation.error_code?.replaceAll("_", " ") ?? "No failure detected"}</p>
                <div className="stream-stats">
                  <span>Source <strong>{streamObservation.metrics.source_events}</strong></span>
                  <span>Written <strong>{streamObservation.metrics.written}</strong></span>
                  <span>Gap <strong>{streamObservation.metrics.source_sink_gap}</strong></span>
                  <span>DLQ <strong>{streamObservation.metrics.dlq}</strong></span>
                  <span>Lag <strong>{streamObservation.metrics.max_lag_seconds}s</strong></span>
                </div>
                <small className="muted">{streamObservation.scenario.replaceAll("_", " ")} · simulated evidence</small>
              </> : <p className="muted">No stream check recorded yet.</p>}
            </div>
          </section>
          <div className="section-top"><div><div className="eyebrow">02 / DELIVERY</div><h2>Broker delivery</h2></div></div>
          <section className="panel broker-lab" aria-label="Local broker stream">
            <div>
              <div className="eyebrow">REDIS STREAM / LOCAL</div>
              <h3>Broker delivery</h3>
              <p className="muted">Publish fixed test events to Redis. A separate worker records accepted events, dead letters and incidents with a durable checkpoint.</p>
              {canExecute && <div className="stream-controls">
                <select aria-label="Broker scenario" value={brokerScenario} onChange={(event) => setBrokerScenario(event.target.value)}>
                  <option value="SCHEMA_V15">Schema mismatch</option>
                  <option value="CONSUMER_LAG">Consumer lag</option>
                  <option value="LATE_EVENT">Late event</option>
                  <option value="DUPLICATE">Duplicate delivery</option>
                  <option value="CLEAN">Clean delivery</option>
                </select>
                <button className="secondary" disabled={busy} onClick={() => runBrokerScenario(session)}>Publish test events</button>
              </div>}
            </div>
            <div className="broker-summary" aria-live="polite">
              <div className="stream-stats">
                <span>Written <strong>{brokerStatus?.written ?? "—"}</strong></span>
                <span>Dead letter <strong>{brokerStatus?.dlq ?? "—"}</strong></span>
                <span>Flagged <strong>{brokerStatus?.failures ?? "—"}</strong></span>
              </div>
              <button className="outline" disabled={busy} onClick={() => void perform(async () => {
                await loadBroker(session);
                await loadIncidents(session);
              })}>Refresh broker results</button>
              <small className="muted">{brokerStatus ? "Synthetic events · local Redis · counts for this tenant" : "Broker status unavailable for this workspace"}</small>
            </div>
          </section>
    </>
  );
}
