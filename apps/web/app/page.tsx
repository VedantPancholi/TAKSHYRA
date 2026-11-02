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
type Impact = {
  items?: { id: string; name?: string; impact_type?: string }[];
  affected_assets?: { id: string; name?: string; impact_type?: string }[];
  [key: string]: unknown;
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
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [proposalId, setProposalId] = useState("");
  const [note, setNote] = useState("Checked incident evidence");
  const [actionType, setActionType] = useState<
    "incident.annotate" | "pipeline.pause_demo"
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
        setProposal(null);
        setProposalId("");
      }
      setWorkspaceTenant(active.tenant);
      setSession(active);
      setPassword("");
      const [list, pipeList] = await Promise.all([
        api<{ items: Incident[] }>(active, "GET", "incidents"),
        api<{ items: { id: string; name: string }[] }>(
          active,
          "GET",
          "pipelines",
        ),
      ]);
      setIncidents(list.items);
      setPipelines(pipeList.items);
      if (proposalId) {
        try {
          setProposal(
            await api<Proposal>(
              active,
              "GET",
              `action-proposals/${proposalId}`,
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
    setNotice(
      "Signed out. Proposal ID stays on this page for the approval handoff.",
    );
  }

  function selectIncident(active: Session, incident: Incident) {
    void perform(async () => {
      const [detail, radius] = await Promise.all([
        api<Incident>(active, "GET", `incidents/${incident.id}`),
        api<Impact>(active, "GET", `incidents/${incident.id}/impact`),
      ]);
      setSelected(detail);
      setImpact(radius);
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
            actionType === "incident.annotate"
              ? selected.id
              : selected.pipeline_id,
          parameters:
            actionType === "incident.annotate" ? { note: note.trim() } : {},
        },
        crypto.randomUUID(),
      );
      setProposal(created);
      setProposalId(created.id);
      setNotice(
        "Proposal evaluated by the server. Review its decision before execution.",
      );
    });
  }

  function openProposal(active: Session, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void perform(async () => {
      const found = await api<Proposal>(
        active,
        "GET",
        `action-proposals/${proposalId.trim()}`,
      );
      setProposal(found);
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
              <button
                className="outline"
                onClick={() => createDemo(session)}
                disabled={busy || pipelines.length === 0}
              >
                + Create demo incident
              </button>
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
              <button
                className="primary"
                onClick={() => createProposal(session)}
                disabled={
                  !canExecute ||
                  !selected ||
                  (actionType === "incident.annotate" && !note.trim()) ||
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
              <form
                className="lookup"
                onSubmit={(event) => openProposal(session, event)}
              >
                <label>
                  Open proposal by ID
                  <input
                    value={proposalId}
                    onChange={(event) => setProposalId(event.target.value)}
                    placeholder="Proposal UUID"
                  />
                </label>
                <button
                  className="outline"
                  disabled={!proposalId.trim() || busy}
                >
                  Open
                </button>
              </form>
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
                  Create or open a proposal to review policy, approval and
                  verification.
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
