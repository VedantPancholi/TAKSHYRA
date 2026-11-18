"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { useWorkspace } from "./workspace-context";

const routes = [
  { href: "/overview", label: "Overview", number: "01" },
  { href: "/incidents", label: "Incidents", number: "02" },
  { href: "/pipelines", label: "Pipelines", number: "03" },
  { href: "/streaming", label: "Streaming", number: "04" },
  { href: "/actions", label: "Governed actions", number: "05" },
];

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const {
    session, username, setUsername, password, setPassword, tenant, setTenant,
    incidents, busy, error, setError, notice, setNotice, signIn, signOut,
  } = useWorkspace();
  return (
    <main className="shell">
      <header className="topbar">
        <Link className="brand" href="/overview" aria-label="TAKSHYRA overview">
          <span className="brand-mark">T</span>
          <span className="brand-copy"><strong>TAKSHYRA</strong><small>OPERATIONS CONSOLE</small></span>
        </Link>
        <div className="top-right">
          <span className="environment">● &nbsp; LOCAL DEMO</span>
          {session && <>
            <span className="identity">{session.username} · {session.role} · {session.tenant}</span>
            <button className="text-button" onClick={signOut}>Switch account</button>
          </>}
        </div>
      </header>
      {!session ? (
        <section className="login-wrap">
          <div className="login-copy">
            <div className="eyebrow">DATA RELIABILITY / LOCAL DEMO</div>
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
        <div className="console-layout">
          <aside className="console-sidebar">
            <div className="sidebar-label">WORKSPACE / {session.tenant.toUpperCase()}</div>
            <nav className="module-nav" aria-label="Main navigation">
              {routes.map((route) => (
                <Link key={route.href} href={route.href} className={pathname === route.href ? "active" : ""} aria-current={pathname === route.href ? "page" : undefined}>
                  <span className="nav-number">{route.number}</span>
                  <span>{route.label}</span>
                  {route.href === "/incidents" && <small>{incidents.filter((item) => item.status !== "RESOLVED").length}</small>}
                </Link>
              ))}
            </nav>
            <div className="sidebar-bottom"><span>ACCESS LEVEL</span><strong>{session.role.toUpperCase()}</strong><small>Enforced by API</small></div>
          </aside>
          <div className="console-content">
            <div className="mobile-module-nav"><nav aria-label="Mobile navigation">{routes.map((route) => <Link key={route.href} href={route.href} aria-current={pathname === route.href ? "page" : undefined}>{route.label}</Link>)}</nav></div>
            {children}
          </div>
        </div>
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

      <footer>TAKSHYRA · Intelligence Behind Every Decision <span>Development workspace · No production actions</span></footer>
    </main>
  );
}
