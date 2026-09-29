"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/backend";
const LOCAL_EMAIL = "admin@enesko.local";
const LOCAL_PASSWORD = "EneskoDemo2026!";

type View = "overview" | "cases" | "tenant-requests" | "activations" | "audit" | "parking";

export default function Admin() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [email, setEmail] = useState(LOCAL_EMAIL);
  const [password, setPassword] = useState(LOCAL_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState("");
  const [data, setData] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [acts, setActs] = useState<any[]>([]);
  const [parking, setParking] = useState<any[]>([]);
  const [tenantRequests, setTenantRequests] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [activeView, setActiveView] = useState<View>("overview");
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [selectedActivation, setSelectedActivation] = useState<any>(null);
  const [selectedParking, setSelectedParking] = useState<any>(null);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [credentialsReset, setCredentialsReset] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("enesko-ops-theme");
    const next =
      saved === "light" || saved === "dark"
        ? saved
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    setTheme(next);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("enesko-ops-theme", theme);
  }, [theme]);

  function authHeaders(t = token) {
    return { Authorization: "Bearer " + t };
  }

  async function readJson(response: Response, label: string) {
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(body?.detail || `${label} failed (HTTP ${response.status}).`);
    }
    return body;
  }

  async function load(t: string, announce = false) {
    const headers = authHeaders(t);
    const [overviewResponse, casesResponse, activationsResponse, parkingResponse] =
      await Promise.all([
        fetch(API + "/api/v1/admin/overview", { headers }),
        fetch(API + "/api/v1/cases", { headers }),
        fetch(API + "/api/v1/activations", { headers }),
        fetch(API + "/api/v1/parking", { headers }),
      ]);

    const [overviewData, caseData, activationData, parkingData] = await Promise.all([
      readJson(overviewResponse, "Operational overview"),
      readJson(casesResponse, "Cases"),
      readJson(activationsResponse, "Activations"),
      readJson(parkingResponse, "Parking"),
    ]);

    setData(overviewData);
    setCases(caseData);
    setActs(activationData);
    setParking(parkingData);

    if (selectedCase) {
      const refreshed = caseData.find((item: any) => item.reference === selectedCase.reference);
      if (refreshed) setSelectedCase(refreshed);
    }
    if (selectedActivation) {
      const refreshed = activationData.find((item: any) => item.reference === selectedActivation.reference);
      if (refreshed) setSelectedActivation(refreshed);
    }
    if (selectedParking) {
      const refreshed = parkingData.find((item: any) => item.area_code === selectedParking.area_code);
      if (refreshed) setSelectedParking(refreshed);
    }

    if (announce) {
      setStatusMessage("Operational data refreshed.");
      window.setTimeout(() => setStatusMessage(""), 2500);
    }
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatusMessage("");
    setCredentialsReset(false);
    setSigningIn(true);

    try {
      const response = await fetch(API + "/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: email.trim().toLowerCase(),
          password,
        }),
      });

      const result = await readJson(response, "Login");
      await load(result.access_token);
      setToken(result.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ENESKO could not complete the sign-in request.");
    } finally {
      setSigningIn(false);
    }
  }

  function loadLocalCredentials() {
    setEmail(LOCAL_EMAIL);
    setPassword(LOCAL_PASSWORD);
    setError("");
    setCredentialsReset(true);
  }

  async function openView(view: View) {
    setError("");
    setStatusMessage("");
    setActiveView(view);

    try {
      if (view === "audit") {
        setBusy(true);
        const response = await fetch(API + "/api/v1/admin/audit", { headers: authHeaders() });
        setAudit(await readJson(response, "Audit log"));
      }

      if (view === "tenant-requests") {
        setBusy(true);
        const tenantsResponse = await fetch(API + "/api/v1/tenants", { headers: authHeaders() });
        const tenants = await readJson(tenantsResponse, "Tenants");

        const requestGroups = await Promise.all(
          tenants.map(async (tenant: any) => {
            const response = await fetch(API + `/api/v1/tenants/${tenant.id}/requests`, {
              headers: authHeaders(),
            });
            const requests = await readJson(response, `Requests for ${tenant.name}`);
            return requests.map((request: any) => ({ ...request, tenant_name: tenant.name }));
          })
        );

        setTenantRequests(requestGroups.flat());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "The selected operations view could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  async function updateCaseStatus(status: string) {
    if (!selectedCase) return;
    setBusy(true);
    setError("");
    setStatusMessage("");

    try {
      const response = await fetch(
        API + `/api/v1/cases/${encodeURIComponent(selectedCase.reference)}/status`,
        {
          method: "PATCH",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status,
            note: `Status changed to ${status} from ENESKO Operations Control.`,
            actor: "admin_dashboard",
          }),
        }
      );
      const updated = await readJson(response, "Case update");
      setSelectedCase(updated);
      await load(token);
      setStatusMessage(`${updated.reference} updated to ${updated.status}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Case status update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function updateActivationStage(stage: string) {
    if (!selectedActivation) return;
    setBusy(true);
    setError("");
    setStatusMessage("");

    try {
      const response = await fetch(
        API + `/api/v1/activations/${encodeURIComponent(selectedActivation.reference)}/stage`,
        {
          method: "PATCH",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            current_stage: stage,
            status: stage === "CONFIRMED" ? "APPROVED" : "IN_REVIEW",
          }),
        }
      );
      const updated = await readJson(response, "Activation update");
      setSelectedActivation(updated);
      await load(token);
      setStatusMessage(`${updated.reference} moved to ${updated.current_stage}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activation stage update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function updateParkingStatus(status: string) {
    if (!selectedParking) return;
    setBusy(true);
    setError("");
    setStatusMessage("");

    try {
      const response = await fetch(
        API + `/api/v1/parking/${encodeURIComponent(selectedParking.area_code)}/status`,
        {
          method: "PATCH",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ occupancy_status: status, expires_minutes: 30 }),
        }
      );
      const updated = await readJson(response, "Parking update");
      setSelectedParking(updated);
      await load(token);
      setStatusMessage(`${updated.name} updated to ${updated.occupancy_status} for 30 minutes.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Parking status update failed.");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    setToken("");
    setData(null);
    setCases([]);
    setActs([]);
    setParking([]);
    setTenantRequests([]);
    setAudit([]);
    setSelectedCase(null);
    setSelectedActivation(null);
    setSelectedParking(null);
    setActiveView("overview");
    setError("");
    setStatusMessage("");
  }

  const metricCards: Array<[string, number, View]> = [
    ["Cases", data?.cases ?? 0, "cases"],
    ["Tenant requests", data?.tenant_requests ?? 0, "tenant-requests"],
    ["Activations", data?.activations ?? 0, "activations"],
    ["Audit events", data?.audit_events ?? 0, "audit"],
  ];

  return (
    <div className="shell">
      <nav className="nav">
        <div className="brand">ENESKO OPS</div>
        <div className="row">
          {token && (
            <button className="navButton" type="button" onClick={() => openView("overview")}>
              Overview
            </button>
          )}
          {token && (
            <button className="navButton" type="button" onClick={() => openView("parking")}>
              Parking
            </button>
          )}
          {token && (
            <button className="navButton" type="button" onClick={signOut}>
              Sign out
            </button>
          )}
          <button
            className="themeToggle"
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle light and dark mode"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <span className="pill">Operations Control</span>
        </div>
      </nav>

      <main className="main">
        {!token ? (
          <div className="panel card">
            <div className="eyebrow">Authorized staff</div>
            <h1>Operations sign in</h1>
            <p className="muted">Secure staff access to ENESKO operations and live workflow controls.</p>

            <form onSubmit={login}>
              <label htmlFor="admin-email" className="muted">Email</label>
              <input
                id="admin-email"
                className="input"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />

              <label htmlFor="admin-password" className="muted">Password</label>
              <input
                id="admin-password"
                className="input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />

              <div className="row" style={{ marginTop: 8, marginBottom: 16 }}>
                <label className="muted">
                  <input
                    type="checkbox"
                    checked={showPassword}
                    onChange={(event) => setShowPassword(event.target.checked)}
                    style={{ marginRight: 8 }}
                  />
                  Show password
                </label>
              </div>

              <div className="row">
                <button className="button" type="submit" disabled={signingIn}>
                  {signingIn ? "Signing in..." : "Sign in securely"}
                </button>
                <button className="secondaryButton" type="button" onClick={loadLocalCredentials}>
                  Load local credentials
                </button>
              </div>
            </form>

            {credentialsReset && <p className="status">Local credentials loaded.</p>}
            {error && <p className="danger">{error}</p>}
          </div>
        ) : (
          <>
            <div className="row headerRow">
              <div>
                <div className="eyebrow">Command center</div>
                <h1>{activeView === "overview" ? "Operational overview" : activeView.replace("-", " ")}</h1>
                <p className="muted">
                  {activeView === "overview"
                    ? "Select a metric or operational queue to inspect and act on current records."
                    : "Use Back to overview to return to the command center."}
                </p>
              </div>
              <div className="row">
                {activeView !== "overview" && (
                  <button className="secondaryButton" type="button" onClick={() => openView("overview")}>
                    Back to overview
                  </button>
                )}
                <button className="button" type="button" onClick={() => load(token, true)} disabled={busy}>
                  {busy ? "Working..." : "Refresh"}
                </button>
              </div>
            </div>

            {statusMessage && <p className="status notice">{statusMessage}</p>}
            {error && <p className="danger notice">{error}</p>}

            {activeView === "overview" && (
              <>
                <div className="grid">
                  {metricCards.map(([label, value, view]) => (
                    <button className="card interactiveCard" type="button" key={label} onClick={() => openView(view)}>
                      <div className="metric">{value}</div>
                      <p className="muted">{label}</p>
                      <span className="linkText">Open →</span>
                    </button>
                  ))}
                </div>

                <div className="grid">
                  <div className="card">
                    <div className="sectionHeader">
                      <h3>Case queue</h3>
                      <button className="textButton" type="button" onClick={() => openView("cases")}>View all</button>
                    </div>
                    {cases.slice(0, 5).map((item) => (
                      <button
                        key={item.id}
                        className="listButton"
                        type="button"
                        onClick={() => {
                          setSelectedCase(item);
                          setActiveView("cases");
                        }}
                      >
                        <strong>{item.reference}</strong>
                        <span>{item.status} · {item.summary}</span>
                      </button>
                    ))}
                  </div>

                  <div className="card">
                    <div className="sectionHeader">
                      <h3>Activations</h3>
                      <button className="textButton" type="button" onClick={() => openView("activations")}>View all</button>
                    </div>
                    {acts.slice(0, 5).map((item) => (
                      <button
                        key={item.id}
                        className="listButton"
                        type="button"
                        onClick={() => {
                          setSelectedActivation(item);
                          setActiveView("activations");
                        }}
                      >
                        <strong>{item.reference}</strong>
                        <span>{item.current_stage}</span>
                      </button>
                    ))}
                  </div>

                  <div className="card">
                    <div className="sectionHeader">
                      <h3>Parking</h3>
                      <button className="textButton" type="button" onClick={() => openView("parking")}>Manage</button>
                    </div>
                    {parking.map((item) => (
                      <button
                        key={item.id}
                        className="listButton"
                        type="button"
                        onClick={() => {
                          setSelectedParking(item);
                          setActiveView("parking");
                        }}
                      >
                        <strong>{item.name}</strong>
                        <span>{item.occupancy_status}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeView === "cases" && (
              <div className="split">
                <div className="card">
                  <h3>Cases</h3>
                  {cases.map((item) => (
                    <button
                      key={item.id}
                      className={`listButton ${selectedCase?.id === item.id ? "selected" : ""}`}
                      type="button"
                      onClick={() => setSelectedCase(item)}
                    >
                      <strong>{item.reference}</strong>
                      <span>{item.status} · {item.summary}</span>
                    </button>
                  ))}
                </div>
                <div className="card detailCard">
                  {selectedCase ? (
                    <>
                      <div className="eyebrow">Case detail</div>
                      <h2>{selectedCase.reference}</h2>
                      <p><strong>{selectedCase.summary}</strong></p>
                      <p className="muted">{selectedCase.description}</p>
                      <p className="muted">Type: {selectedCase.case_type} · Priority: {selectedCase.priority} · Channel: {selectedCase.channel}</p>
                      <p className="muted">Status: <strong>{selectedCase.status}</strong></p>
                      <div className="actionGroup">
                        {["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"].map((status) => (
                          <button
                            key={status}
                            className="secondaryButton"
                            type="button"
                            disabled={busy || selectedCase.status === status}
                            onClick={() => updateCaseStatus(status)}
                          >
                            {status.replace("_", " ")}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="muted">Select a case to inspect and update it.</p>
                  )}
                </div>
              </div>
            )}

            {activeView === "tenant-requests" && (
              <div className="card">
                <h3>Tenant requests</h3>
                {busy ? (
                  <p className="muted">Loading tenant requests…</p>
                ) : tenantRequests.length ? (
                  tenantRequests.map((item) => (
                    <div className="record" key={item.id}>
                      <strong>{item.tenant_name}</strong>
                      <span>{item.request_type} · {item.case?.reference} · {item.case?.status}</span>
                      <span className="muted">{item.case?.summary}</span>
                    </div>
                  ))
                ) : (
                  <p className="muted">No tenant requests are currently recorded.</p>
                )}
              </div>
            )}

            {activeView === "activations" && (
              <div className="split">
                <div className="card">
                  <h3>Activations</h3>
                  {acts.map((item) => (
                    <button
                      key={item.id}
                      className={`listButton ${selectedActivation?.id === item.id ? "selected" : ""}`}
                      type="button"
                      onClick={() => setSelectedActivation(item)}
                    >
                      <strong>{item.reference}</strong>
                      <span>{item.current_stage} · {item.title}</span>
                    </button>
                  ))}
                </div>
                <div className="card detailCard">
                  {selectedActivation ? (
                    <>
                      <div className="eyebrow">Activation workflow</div>
                      <h2>{selectedActivation.reference}</h2>
                      <p><strong>{selectedActivation.title}</strong></p>
                      <p className="muted">{selectedActivation.description}</p>
                      <p className="muted">Applicant: {selectedActivation.applicant_name} · Proposed date: {selectedActivation.proposed_date}</p>
                      <p className="muted">Stage: <strong>{selectedActivation.current_stage}</strong></p>
                      <div className="actionGroup">
                        {["INTAKE", "VALIDATION", "MARKETING_REVIEW", "FACILITIES_REVIEW", "SECURITY_REVIEW", "MANAGEMENT_APPROVAL", "COMMERCIAL", "CONFIRMED"].map((stage) => (
                          <button
                            key={stage}
                            className="secondaryButton"
                            type="button"
                            disabled={busy || selectedActivation.current_stage === stage}
                            onClick={() => updateActivationStage(stage)}
                          >
                            {stage.replaceAll("_", " ")}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="muted">Select an activation to inspect its workflow.</p>
                  )}
                </div>
              </div>
            )}

            {activeView === "parking" && (
              <div className="split">
                <div className="card">
                  <h3>Parking areas</h3>
                  {parking.map((item) => (
                    <button
                      key={item.id}
                      className={`listButton ${selectedParking?.id === item.id ? "selected" : ""}`}
                      type="button"
                      onClick={() => setSelectedParking(item)}
                    >
                      <strong>{item.name}</strong>
                      <span>{item.occupancy_status} · {item.data_status}</span>
                    </button>
                  ))}
                </div>
                <div className="card detailCard">
                  {selectedParking ? (
                    <>
                      <div className="eyebrow">Staff parking status</div>
                      <h2>{selectedParking.name}</h2>
                      <p className="muted">Area code: {selectedParking.area_code}</p>
                      <p className="muted">Current status: <strong>{selectedParking.occupancy_status}</strong></p>
                      <p className="muted">Source: {selectedParking.source} · Data status: {selectedParking.data_status}</p>
                      <p className="muted">Staff updates expire after 30 minutes.</p>
                      <div className="actionGroup">
                        {["AVAILABLE", "BUSY", "NEAR_CAPACITY", "FULL", "CLOSED", "UNKNOWN"].map((status) => (
                          <button
                            key={status}
                            className="secondaryButton"
                            type="button"
                            disabled={busy || selectedParking.occupancy_status === status}
                            onClick={() => updateParkingStatus(status)}
                          >
                            {status.replace("_", " ")}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="muted">Select a parking area to post a verified staff status.</p>
                  )}
                </div>
              </div>
            )}

            {activeView === "audit" && (
              <div className="card">
                <h3>Audit events</h3>
                {busy ? (
                  <p className="muted">Loading audit events…</p>
                ) : audit.length ? (
                  audit.map((item) => (
                    <div className="record" key={item.id}>
                      <strong>{item.method} {item.path}</strong>
                      <span>HTTP {item.status_code} · {item.actor_role || "anonymous"}</span>
                      <span className="muted">{new Date(item.created_at).toLocaleString()}</span>
                    </div>
                  ))
                ) : (
                  <p className="muted">No audit events are currently recorded.</p>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
