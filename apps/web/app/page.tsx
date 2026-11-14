"use client";

import { FormEvent, useState } from "react";

type Session = {
  authorization: string;
  tenant: string;
  username: string;
  role: string;
};
type Incident = {
  id: string;
  pipeline_id: string;
  run_id: string | null;
  owner_id: string | null;
  category: string;
  severity: string;
  status: string;
  error_code: string;
  occurrence_count: number;
  last_seen_at: string;
  provenance: string;
  timeline?: {
    kind: string;
    code: string;
    safe_detail: string | null;
    occurred_at: string;
  }[];
  timeline_truncated?: boolean;
};
type Proposal = {
  id: string;
  action_type: string;
  target_id: string;
  parameters: Record<string, string>;
  payload_digest: string;
  policy_decision: string;
  policy_reason: string;
  status: string;
  requester_id: string;
  approver_id: string | null;
  expires_at: string;
  verification_status: string | null;
  timeline: { kind: string; code: string; occurred_at: string }[];
};
type ProposalSummary = Pick<
  Proposal,
  | "id"
  | "action_type"
  | "target_id"
  | "policy_decision"
  | "status"
  | "requester_id"
  | "expires_at"
> & { created_at: string };
type Impact = {
  items?: { id: string; name?: string; impact_type?: string }[];
  affected_assets?: { id: string; name?: string; impact_type?: string }[];
  [key: string]: unknown;
};
type Diagnosis = {
  id: string;
  status: string;
  method: string;
  model_id: string | null;
  provider_status: string;
  memory_status: string;
  similar_cases: { id: string; summary: string }[];
  created_at: string;
  hypotheses: {
    summary: string;
    category: string;
    confidence_label: string;
    supporting_evidence_refs: string[];
    unknowns: string[];
    next_checks: string[];
  }[];
};
type ShadowReplay = {
  id: string;
  status: string;
  reason: string;
  source_run_id: string;
  baseline_row_count: number | null;
  replay_row_count: number | null;
};
type RecoveryOutcome = {
  status: string;
  reason?: string;
  recovery_run_id?: string;
};

async function api<T>(
  session: Session,
  method: string,
  path: string,
  body?: object,
  key?: string,
): Promise<T> {
  const response = await fetch(`/api/core/${path}`, {
    method,
    headers: {
      Authorization: session.authorization,
      "X-Tenant-Slug": session.tenant,
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      data?.error?.message ?? `Request failed (${response.status})`,
    );
  return data as T;
}

function stamp(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function Pill({ value }: { value: string }) {
  const tone = /FAILED|DENY|CRITICAL|HIGH|QUARANTINED/.test(value)
    ? "danger"
    : /APPROV|OPEN|MEDIUM|UNKNOWN|INCONCLUSIVE/.test(value)
      ? "warn"
      : "good";
  return <span className={`pill ${tone}`}>{value.replaceAll("_", " ")}</span>;
}

export default function OperationsPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [workspaceTenant, setWorkspaceTenant] = useState<string | null>(null);
  const [username, setUsername] = useState("demo-a-executor");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState("demo-a");
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [impact, setImpact] = useState<Impact | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [shadowReplay, setShadowReplay] = useState<ShadowReplay | null>(null);
  const [recoveryOutcome, setRecoveryOutcome] = useState<RecoveryOutcome | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [recentProposals, setRecentProposals] = useState<ProposalSummary[]>([]);
  const [note, setNote] = useState("Checked incident evidence");
  const [actionType, setActionType] = useState<
    "incident.annotate" | "pipeline.pause_demo" | "pipeline.reprocess_demo"
  >("incident.annotate");
  const [pipelines, setPipelines] = useState<{ id: string; name: string }[]>(
    [],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function perform(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadIncidents(active: Session) {
    const list = await api<{ items: Incident[] }>(active, "GET", "incidents");
    setIncidents(list.items);
  }

  async function loadProposals(active: Session) {
    const list = await api<{ items: ProposalSummary[] }>(
      active,
      "GET",
      "action-proposals",
    );
    setRecentProposals(list.items);
  }

  function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void perform(async () => {
      const authorization = `Basic ${btoa(`${username}:${password}`)}`;
      const candidate = { authorization, tenant, username, role: "" };
      const me = await api<{
        username: string;
        tenant_slug: string;
        role: string;
      }>(candidate, "GET", "me");
      const active = {
        ...candidate,
        username: me.username,
        tenant: me.tenant_slug,
        role: me.role,
      };
      if (workspaceTenant && workspaceTenant !== active.tenant) {
        setSelected(null);
        setImpact(null);
        setDiagnosis(null);
        setShadowReplay(null);
        setRecoveryOutcome(null);
        setProposal(null);
        setRecentProposals([]);
      }
      setWorkspaceTenant(active.tenant);
      setSession(active);
      setPassword("");
      const [list, pipeList, proposals] = await Promise.all([
        api<{ items: Incident[] }>(active, "GET", "incidents"),
        api<{ items: { id: string; name: string }[] }>(
          active,
          "GET",
          "pipelines",
        ),
        api<{ items: ProposalSummary[] }>(active, "GET", "action-proposals"),
      ]);
      setIncidents(list.items);
      setPipelines(pipeList.items);
      setRecentProposals(proposals.items);
      if (proposal && (!workspaceTenant || workspaceTenant === active.tenant)) {
        try {
          setProposal(
            await api<Proposal>(
              active,
              "GET",
              `action-proposals/${proposal.id}`,
            ),
          );
        } catch {
          setProposal(null);
        }
      }
    });
  }

  function signOut() {
    setSession(null);
    setIncidents([]);
    setPipelines([]);
    setSelected(null);
    setImpact(null);
    setDiagnosis(null);
    setShadowReplay(null);
    setRecoveryOutcome(null);
    setRecentProposals([]);
    setNotice(
      "Signed out. Sign in with another role to continue the proposal handoff.",
    );
  }

  function selectIncident(active: Session, incident: Incident) {
    void perform(async () => {
      const [detail, radius, diagnoses, replays] = await Promise.all([
        api<Incident>(active, "GET", `incidents/${incident.id}`),
        api<Impact>(active, "GET", `incidents/${incident.id}/impact`),
        api<{ items: Diagnosis[] }>(active, "GET", `incidents/${incident.id}/diagnoses`),
        api<{ items: ShadowReplay[] }>(active, "GET", `incidents/${incident.id}/shadow-replays`),
      ]);
      setSelected(detail);
      setImpact(radius);
      setDiagnosis(diagnoses.items[0] ?? null);
      setShadowReplay(replays.items.find((item) => item.source_run_id === detail.run_id) ?? null);
      setActionType("incident.annotate");
    });
  }

  function createDemo(active: Session) {
    if (!pipelines[0]) return;
    void perform(async () => {
      const created = await api<Incident>(
        active,
        "POST",
        `demo/pipelines/${pipelines[0].id}/freshness-miss`,
        {},
      );
      await loadIncidents(active);
      setSelected(created);
      setDiagnosis(null);
      setShadowReplay(null);
      setImpact(
        await api<Impact>(active, "GET", `incidents/${created.id}/impact`),
      );
      setNotice("Simulated freshness incident recorded.");
    });
  }

  function investigate(active: Session) {
    if (!selected) return;
    void perform(async () => {
      const updated = await api<Incident>(
        active,
        "PATCH",
        `incidents/${selected.id}`,
        { status: "INVESTIGATING" },
      );
      setSelected(updated);
      await loadIncidents(active);
      setNotice("Investigation started.");
    });
  }

  function diagnose(active: Session) {
    if (!selected) return;
    void perform(async () => {
      const result = await api<Diagnosis>(
        active, "POST", `incidents/${selected.id}/diagnoses`, {},
      );
      setDiagnosis(result);
      setSelected(await api<Incident>(active, "GET", `incidents/${selected.id}`));
      setNotice("Evidence-linked diagnosis recorded. The cause remains a hypothesis.");
    });
  }

  function createRowDeficit(active: Session) {
    if (!pipelines[0]) return;
    void perform(async () => {
      await api(active, "POST", `pipelines/${pipelines[0].id}/runs`,
        { demo_fault: "F04" }, crypto.randomUUID());
      setNotice("Row deficit run queued. Refresh after the worker finishes, then select its quality incident.");
    });
  }

  function replayIncident(active: Session) {
    if (!selected) return;
    void perform(async () => {
      const result = await api<ShadowReplay>(active, "POST",
        `incidents/${selected.id}/shadow-replays`, {});
      setShadowReplay(result);
      setNotice(`Shadow replay ${result.status.toLowerCase()}: ${result.reason.replaceAll("_", " ")}.`);
    });
  }

  function verifyRecovery(active: Session) {
    if (!proposal) return;
    void perform(async () => {
      const result = await api<RecoveryOutcome>(active, "POST",
        `action-proposals/${proposal.id}/verify-recovery`, {});
      setRecoveryOutcome(result);
      await loadIncidents(active);
      if (selected) setSelected(await api<Incident>(active, "GET", `incidents/${selected.id}`));
      setNotice(`Recovery check: ${result.status.toLowerCase().replaceAll("_", " ")}.`);
    });
  }

  function createProposal(active: Session) {
    if (!selected) return;
    void perform(async () => {
      const created = await api<Proposal>(
        active,
        "POST",
        "action-proposals",
        {
          action_type: actionType,
          target_id:
            actionType === "incident.annotate" ? selected.id
              : actionType === "pipeline.reprocess_demo" ? selected.run_id
              : selected.pipeline_id,
          parameters:
            actionType === "incident.annotate" ? { note: note.trim() }
              : actionType === "pipeline.reprocess_demo" ? { shadow_report_id: shadowReplay?.id ?? "" }
              : {},
        },
        crypto.randomUUID(),
      );
      setProposal(created);
      await loadProposals(active);
      setNotice(
        "Proposal evaluated by the server. Review its decision before execution.",
      );
    });
  }

  function openProposal(active: Session, id: string) {
    void perform(async () => {
      const found = await api<Proposal>(
        active,
        "GET",
        `action-proposals/${id}`,
      );
      setProposal(found);
      setRecoveryOutcome(found.action_type === "pipeline.reprocess_demo"
        ? await api<RecoveryOutcome>(active, "GET", `action-proposals/${id}/recovery-outcome`)
        : null);
      setNotice("Proposal loaded.");
    });
  }

  function changeProposal(active: Session, verb: "approve" | "execute") {
    if (!proposal) return;
    void perform(async () => {
      const updated = await api<Proposal>(
        active,
        "POST",
        `action-proposals/${proposal.id}/${verb}`,
        {},
      );
      setProposal(updated);
      await loadProposals(active);
      setNotice(
        verb === "approve"
          ? "Exact proposal approved."
          : "Action finished; inspect verification below.",
      );
      if (selected)
        setSelected(
          await api<Incident>(active, "GET", `incidents/${selected.id}`),
        );
    });
  }

  const canExecute = session?.role === "executor" || session?.role === "admin";
  const canApprove = session?.role === "approver" || session?.role === "admin";
  const impactItems = impact?.affected_assets ?? impact?.items ?? [];
  const visibleProposals = canApprove
    ? recentProposals
        .slice()
        .sort(
          (a, b) =>
            Number(b.status === "AWAITING_APPROVAL") -
            Number(a.status === "AWAITING_APPROVAL"),
        )
    : recentProposals;

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <div>
            <strong>TAKSHYRA</strong>
            <small>OPERATIONS CONSOLE</small>
          </div>
        </div>
        <div className="top-right">
          <span className="environment">● &nbsp; LOCAL DEMO</span>
          {session && (
            <>
              <span className="identity">
                {session.username} · {session.role} · {session.tenant}
              </span>
              <button className="text-button" onClick={signOut}>
                Switch account
              </button>
            </>
          )}
        </div>
      </header>

      {!session ? (
        <section className="login-wrap">
          <div className="login-copy">
            <div className="eyebrow">DATA RELIABILITY / M6</div>
            <h1>
              See the signal.
              <br />
              <em>Own the response.</em>
            </h1>
            <p>
              A focused workbench for incident evidence, downstream impact and
              governed actions.
            </p>
            <div className="login-note">
              This local demo uses the seeded API identities. Credentials stay
              in browser memory for this tab and are cleared when you switch
              accounts or reload.
            </div>
          </div>
          <form className="login-card" onSubmit={signIn}>
            <div className="card-kicker">01 / ACCESS</div>
            <h2>Sign in to your workspace</h2>
            <label>
              Tenant
              <input
                value={tenant}
                onChange={(event) => setTenant(event.target.value)}
                required
                autoComplete="off"
              />
            </label>
            <label>
              Username
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            <button className="primary" disabled={busy}>
              Enter console <span>→</span>
            </button>
            <p className="form-hint">
              Try executor, viewer or approver identities for a seeded tenant.
            </p>
          </form>
        </section>
      ) : (
        <>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                COMMAND CENTER / {session.tenant.toUpperCase()}
              </div>
              <h1>Operations overview</h1>
              <p>
                Investigate evidence and move from signal to a verified local
                action.
              </p>
            </div>
            <button
              className="outline"
              onClick={() => void perform(() => loadIncidents(session))}
              disabled={busy}
            >
              ↻ &nbsp; Refresh
            </button>
          </div>
          <section className="metric-row" aria-label="Incident summary">
            <div className="metric">
              <span>INCIDENTS</span>
              <strong>{incidents.length}</strong>
              <small>Visible in this tenant</small>
            </div>
            <div className="metric">
              <span>OPEN</span>
              <strong>
                {incidents.filter((item) => item.status === "OPEN").length}
              </strong>
              <small>Awaiting investigation</small>
            </div>
            <div className="metric">
              <span>INVESTIGATING</span>
              <strong>
                {
                  incidents.filter((item) => item.status === "INVESTIGATING")
                    .length
                }
              </strong>
              <small>Owned work in progress</small>
            </div>
            <div className="metric accent">
              <span>YOUR ACCESS</span>
              <strong>{session.role.toUpperCase()}</strong>
              <small>Enforced by the API</small>
            </div>
          </section>
          <div className="section-top">
            <div>
              <div className="eyebrow">01 / DETECT</div>
              <h2>Incident center</h2>
            </div>
            {canExecute && (
              <div className="button-row">
                <button className="outline" onClick={() => createDemo(session)} disabled={busy || pipelines.length === 0}>
                  + Create freshness incident
                </button>
                <button className="outline" onClick={() => createRowDeficit(session)} disabled={busy || pipelines.length === 0}>
                  + Create row deficit run
                </button>
              </div>
            )}
          </div>
          <section className="work-grid">
            <div className="panel incident-list">
              <div className="panel-heading">
                <strong>Live incident queue</strong>
                <span>{incidents.length} records</span>
              </div>
              {incidents.length === 0 ? (
                <div className="empty">
                  No incidents yet.{" "}
                  {canExecute
                    ? "Create a simulated freshness incident to try the workflow."
                    : "Ask an executor to start the demo scenario."}
                </div>
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
                      {incidents.map((item) => (
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
          <div className="section-top">
            <div>
              <div className="eyebrow">02 / RESPOND</div>
              <h2>Governed action</h2>
            </div>
            <span className="section-aside">
              Policy decides · People review · API verifies
            </span>
          </div>
          <p className="demo-scope">
            This demo uses one fixed seeded pipeline. A supported row deficit can be
            reprocessed after a shadow replay and a separate approval. Recovery is
            checked only after the new run finishes. The pause action is simulated.
          </p>
          <section className="work-grid action-grid">
            <div className="panel action-card">
              <div className="panel-heading">
                <strong>Create a proposal</strong>
                <span>Local effect</span>
              </div>
              <p>
                Choose an allowlisted action. The API evaluates policy and
                stores the exact payload before any effect occurs.
              </p>
              <label>
                Action type
                <select
                  value={actionType}
                  onChange={(event) =>
                    setActionType(event.target.value as typeof actionType)
                  }
                  disabled={!canExecute}
                >
                  <option value="incident.annotate">
                    Annotate selected incident · allowed
                  </option>
                  <option value="pipeline.pause_demo">
                    Simulate pipeline pause · approval required
                  </option>
                  <option value="pipeline.reprocess_demo">
                    Reprocess row deficit · shadow replay and approval required
                  </option>
                </select>
              </label>
              {actionType === "incident.annotate" && (
                <label>
                  Investigation note
                  <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    maxLength={200}
                    rows={4}
                    disabled={!canExecute}
                  />
                </label>
              )}
              {actionType === "pipeline.pause_demo" && (
                <p className="form-hint">
                  This records a simulated pause marker. It does not stop the
                  worker.
                </p>
              )}
              {actionType === "pipeline.reprocess_demo" && (
                <p className="form-hint">Select a quality incident with a supported shadow replay. A separate approver must review the exact payload.</p>
              )}
              <button
                className="primary"
                onClick={() => createProposal(session)}
                disabled={
                  !canExecute ||
                  !selected ||
                  (actionType === "incident.annotate" && !note.trim()) ||
                  (actionType === "pipeline.reprocess_demo" && (!selected.run_id || shadowReplay?.status !== "SUPPORTED")) ||
                  busy
                }
              >
                Evaluate proposal <span>→</span>
              </button>
              {!canExecute && (
                <p className="form-hint">
                  An executor account is required to propose actions.
                </p>
              )}
              <div className="recent-proposals">
                <div className="recent-heading">
                  <strong>
                    {canApprove ? "Proposals to review" : "Recent proposals"}
                  </strong>
                  <button
                    className="text-button"
                    onClick={() => void perform(() => loadProposals(session))}
                    disabled={busy}
                  >
                    Refresh
                  </button>
                </div>
                {visibleProposals.length === 0 ? (
                  <p className="form-hint">No proposals in this tenant yet.</p>
                ) : (
                  <div className="proposal-list">
                    {visibleProposals.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className={`proposal-row ${proposal?.id === item.id ? "selected" : ""}`}
                        aria-pressed={proposal?.id === item.id}
                        onClick={() => openProposal(session, item.id)}
                        disabled={busy}
                      >
                        <span>
                          <strong>
                            {item.action_type.replaceAll("_", " ")}
                          </strong>
                          <small>
                            {stamp(item.created_at)} · {item.id.slice(0, 8)}
                          </small>
                        </span>
                        <Pill value={item.status} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="panel proposal-card">
              <div className="panel-heading">
                <strong>Proposal review</strong>
                <span>
                  {proposal ? proposal.id.slice(0, 8) : "No proposal selected"}
                </span>
              </div>
              {!proposal ? (
                <div className="empty">
                  Create or select a recent proposal to review policy, approval
                  and verification.
                </div>
              ) : (
                <>
                  <div className="proposal-head">
                    <Pill value={proposal.policy_decision} />
                    <Pill value={proposal.status} />
                  </div>
                  <dl className="proposal-facts">
                    <div>
                      <dt>Action</dt>
                      <dd>{proposal.action_type}</dd>
                    </div>
                    <div>
                      <dt>Target</dt>
                      <dd className="mono">{proposal.target_id}</dd>
                    </div>
                    <div>
                      <dt>Note</dt>
                      <dd>{proposal.parameters.note ?? "—"}</dd>
                    </div>
                    {proposal.parameters.shadow_report_id && <div><dt>Shadow report</dt><dd className="mono">{proposal.parameters.shadow_report_id}</dd></div>}
                    <div>
                      <dt>Policy reason</dt>
                      <dd>{proposal.policy_reason}</dd>
                    </div>
                    <div>
                      <dt>Expires</dt>
                      <dd>{stamp(proposal.expires_at)}</dd>
                    </div>
                    <div>
                      <dt>Payload digest</dt>
                      <dd className="mono digest">{proposal.payload_digest}</dd>
                    </div>
                    <div>
                      <dt>Verification</dt>
                      <dd>{proposal.verification_status ?? "Pending"}</dd>
                    </div>
                  </dl>
                  <div className="button-row">
                    {canApprove &&
                      proposal.policy_decision === "REQUIRES_APPROVAL" &&
                      proposal.status === "AWAITING_APPROVAL" && (
                        <button
                          className="secondary"
                          onClick={() => changeProposal(session, "approve")}
                          disabled={busy}
                        >
                          Approve exact payload
                        </button>
                      )}
                    {canExecute &&
                      ["READY", "APPROVED", "INCONCLUSIVE"].includes(
                        proposal.status,
                      ) && (
                        <button
                          className="primary"
                          onClick={() => changeProposal(session, "execute")}
                          disabled={busy}
                        >
                          Execute and verify <span>→</span>
                        </button>
                      )}
                  </div>
                  {proposal.action_type === "pipeline.reprocess_demo" && proposal.status === "VERIFIED" && (
                    <div className="detail-block">
                      <h4>Data recovery</h4>
                      <p className="muted">Action verification confirms the new run was queued. Check the data after the worker completes.</p>
                      {recoveryOutcome && <p><Pill value={recoveryOutcome.status} /> {recoveryOutcome.reason?.replaceAll("_", " ")}</p>}
                      {canExecute && <button className="secondary" onClick={() => verifyRecovery(session)} disabled={busy}>Verify recovered data</button>}
                    </div>
                  )}
                  <div className="detail-block">
                    <h4>Action timeline</h4>
                    <ol className="timeline">
                      {proposal.timeline.map((event, index) => (
                        <li key={index}>
                          <b>{event.code}</b>
                          <span>{stamp(event.occurred_at)}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </>
              )}
            </div>
          </section>
        </>
      )}
      {(error || notice) && (
        <div
          className={`toast ${error ? "error" : ""}`}
          role={error ? "alert" : "status"}
        >
          {error || notice}
          <button
            onClick={() => {
              setError("");
              setNotice("");
            }}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}
      <footer>
        TAKSHYRA · Intelligence Behind Every Decision{" "}
        <span>Development workspace · No production actions</span>
      </footer>
    </main>
  );
}
