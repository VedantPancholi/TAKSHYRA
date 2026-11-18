"use client";

import { createContext, FormEvent, ReactNode, useContext, useState } from "react";
import { useRouter } from "next/navigation";

type Session = {
  authorization: string;
  tenant: string;
  username: string;
  role: string;
};
type Pipeline = { id: string; name: string; source_kind: string };
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
type StreamObservation = {
  id: string;
  scenario: string;
  status: string;
  error_code: string | null;
  incident_id: string | null;
  metrics: {
    source_events: number;
    written: number;
    dlq: number;
    duplicates: number;
    late: number;
    max_lag_seconds: number;
    source_sink_gap: number;
  };
};
type BrokerStatus = {
  mode: string;
  written: number;
  dlq: number;
  failures: number;
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

function useWorkspaceState() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [workspaceTenant, setWorkspaceTenant] = useState<string | null>(null);
  const [username, setUsername] = useState("demo-a-executor");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState("demo-a");
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [incidentView, setIncidentView] = useState<"overview" | "evidence" | "recovery">("overview");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [shadowReplay, setShadowReplay] = useState<ShadowReplay | null>(null);
  const [recoveryOutcome, setRecoveryOutcome] = useState<RecoveryOutcome | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [recentProposals, setRecentProposals] = useState<ProposalSummary[]>([]);
  const [streamScenario, setStreamScenario] = useState("SCHEMA_V15");
  const [streamObservation, setStreamObservation] = useState<StreamObservation | null>(null);
  const [brokerScenario, setBrokerScenario] = useState("SCHEMA_V15");
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [incidentSearch, setIncidentSearch] = useState("");
  const [incidentStatus, setIncidentStatus] = useState("ALL");
  const [incidentSeverity, setIncidentSeverity] = useState("ALL");
  const [note, setNote] = useState("Checked incident evidence");
  const [actionType, setActionType] = useState<
    "incident.annotate" | "pipeline.pause_demo" | "pipeline.reprocess_demo"
  >("incident.annotate");
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const demoPipeline = pipelines.find((item) => item.source_kind === "seed_orders_v1");
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

  async function loadBroker(active: Session) {
    setBrokerStatus(await api<BrokerStatus>(active, "GET", "stream-observations/broker"));
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
        setIncidentView("overview");
        setImpact(null);
        setDiagnosis(null);
        setShadowReplay(null);
        setRecoveryOutcome(null);
        setProposal(null);
        setRecentProposals([]);
        setStreamObservation(null);
        setBrokerStatus(null);
        setIncidentSearch("");
        setIncidentStatus("ALL");
        setIncidentSeverity("ALL");
      }
      setWorkspaceTenant(active.tenant);
      setSession(active);
      setPassword("");
      const [list, pipeList, proposals, streamObservations, broker] = await Promise.all([
        api<{ items: Incident[] }>(active, "GET", "incidents"),
        api<{ items: Pipeline[] }>(
          active,
          "GET",
          "pipelines",
        ),
        api<{ items: ProposalSummary[] }>(active, "GET", "action-proposals"),
        api<{ items: StreamObservation[] }>(active, "GET", "stream-observations"),
        api<BrokerStatus>(active, "GET", "stream-observations/broker").catch(() => null),
      ]);
      setIncidents(list.items);
      setPipelines(pipeList.items);
      setRecentProposals(proposals.items);
      setStreamObservation(streamObservations.items[0] ?? null);
      setBrokerStatus(broker);
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
    setIncidentView("overview");
    setImpact(null);
    setDiagnosis(null);
    setShadowReplay(null);
    setRecoveryOutcome(null);
    setRecentProposals([]);
    setStreamObservation(null);
    setBrokerStatus(null);
    setIncidentSearch("");
    setIncidentStatus("ALL");
    setIncidentSeverity("ALL");
    setNotice(
      "Signed out. Sign in with another role to continue the proposal handoff.",
    );
  }

  function selectIncident(active: Session, incident: Incident) {
    void perform(async () => {
      setIncidentView("overview");
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
    if (!demoPipeline) return;
    void perform(async () => {
      const created = await api<Incident>(
        active,
        "POST",
        `demo/pipelines/${demoPipeline.id}/freshness-miss`,
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
    if (!demoPipeline) return;
    void perform(async () => {
      await api(active, "POST", `pipelines/${demoPipeline.id}/runs`,
        { demo_fault: "F04" }, crypto.randomUUID());
      setNotice("Row deficit run queued. Refresh after the worker finishes, then select its quality incident.");
    });
  }

  function runStreamScenario(active: Session) {
    void perform(async () => {
      const result = await api<StreamObservation>(active, "POST", "stream-observations/demo",
        { scenario: streamScenario });
      setStreamObservation(result);
      await loadIncidents(active);
      setNotice(result.incident_id
        ? "Simulated stream failure recorded with an incident."
        : "Simulated stream checks passed.");
    });
  }

  function runBrokerScenario(active: Session) {
    void perform(async () => {
      const result = await api<{ queued: number }>(active, "POST", "stream-observations/broker-demo",
        { scenario: brokerScenario });
      await loadBroker(active);
      setNotice(`${result.queued} events queued in the local broker. Refresh after the worker processes them.`);
    });
  }

  function showIncidents(status: string) {
    setIncidentSearch("");
    setIncidentSeverity("ALL");
    setIncidentStatus(status);
    router.push("/incidents");
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
  const filteredIncidents = incidents.filter((item) => {
    const query = incidentSearch.trim().toLowerCase();
    const matchesQuery = !query || `${item.error_code} ${item.category} ${item.id}`.toLowerCase().includes(query);
    return matchesQuery && (incidentStatus === "ALL" || item.status === incidentStatus)
      && (incidentSeverity === "ALL" || item.severity === incidentSeverity);
  });


  return {
    session, username, setUsername, password, setPassword, tenant, setTenant,
    incidents, selected, incidentView, setIncidentView, impact, diagnosis, shadowReplay,
    recoveryOutcome, proposal, recentProposals, streamScenario, setStreamScenario,
    streamObservation, brokerScenario, setBrokerScenario, brokerStatus,
    incidentSearch, setIncidentSearch, incidentStatus, setIncidentStatus,
    incidentSeverity, setIncidentSeverity, note, setNote, actionType, setActionType,
    pipelines, demoPipeline, busy, error, setError, notice, setNotice, signIn, signOut,
    perform, loadIncidents, loadProposals, loadBroker, selectIncident,
    createDemo, investigate, diagnose, createRowDeficit, runStreamScenario,
    runBrokerScenario, showIncidents, replayIncident, verifyRecovery,
    createProposal, openProposal, changeProposal, canExecute, canApprove,
    impactItems, visibleProposals, filteredIncidents
  };
}

type Workspace = ReturnType<typeof useWorkspaceState>;
const WorkspaceContext = createContext<Workspace | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const workspace = useWorkspaceState();
  return <WorkspaceContext.Provider value={workspace}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("WorkspaceProvider is missing");
  return workspace;
}

export function Pill({ value }: { value: string }) {
  const tone = /FAIL|DENY|CRITICAL|HIGH|QUARANTINED/.test(value)
    ? "danger"
    : /APPROV|OPEN|MEDIUM|UNKNOWN|INCONCLUSIVE/.test(value)
      ? "warn"
      : "good";
  return <span className={`pill ${tone}`}>{value.replaceAll("_", " ")}</span>;
}

export function stamp(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
