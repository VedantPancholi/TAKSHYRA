"use client";

import Link from "next/link";
import { Pill, stamp, useWorkspace } from "../workspace-context";

export default function Page() {
  const { session, selected, proposal, recoveryOutcome, note, setNote,
    actionType, setActionType, busy, perform, loadProposals, createProposal,
    openProposal, changeProposal, verifyRecovery, canExecute, canApprove,
    visibleProposals, shadowReplay } = useWorkspace();
  if (!session) return null;
  return (
    <>
          <div className="page-heading">
            <div>
              <div className="eyebrow">WORKSPACE / ACTIONS</div>
              <h1>Governed actions</h1>
              <p>Evaluate a proposal, review policy, and verify its result.</p>
            </div>
            <span className="section-aside">
              Policy decides · People review · API verifies
            </span>
          </div>
          <div className="scope-banner"><strong>{selected ? `Selected: ${selected.error_code}` : "No incident selected"}</strong><span>{selected ? "The proposal form will use this incident or its linked pipeline." : "Select an incident before proposing a new action."}</span><Link href="/incidents">{selected ? "Change incident →" : "Choose incident →"}</Link></div>
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
  );
}
