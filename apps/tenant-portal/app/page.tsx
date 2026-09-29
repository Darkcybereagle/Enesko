"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/backend";
const LOCAL_EMAIL = "tenant@enesko.local";
const LOCAL_PASSWORD = "TenantLocal2026!";

type TenantProfile = {
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    tenant_id: number | null;
    active: boolean;
  };
  tenant_name: string | null;
};

type TenantRecord = {
  id: number;
  mall_id: number;
  name: string;
  unit: string | null;
  primary_contact_name: string;
  primary_contact: string;
  active: boolean;
  data_status: string;
};

type TenantMetrics = {
  tenant_id: number;
  total_requests: number;
  open_requests: number;
  resolved_requests: number;
};

type TenantRequest = {
  id: number;
  tenant_id: number;
  case_id: number;
  request_type: string;
  created_at: string;
  case: {
    reference: string;
    case_type: string;
    status: string;
    priority: string;
    channel: string;
    summary: string;
    description: string;
    created_at: string;
    updated_at: string;
  };
};

type Announcement = {
  id: number;
  title: string;
  message: string;
  data_status: string;
  created_at: string;
};

type TenantDocument = {
  id: number;
  title: string;
  document_type: string;
  reference: string;
  data_status: string;
  created_at: string;
};

export default function TenantPortal() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [email, setEmail] = useState(LOCAL_EMAIL);
  const [password, setPassword] = useState(LOCAL_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [tenant, setTenant] = useState<TenantRecord | null>(null);
  const [metrics, setMetrics] = useState<TenantMetrics | null>(null);
  const [requests, setRequests] = useState<TenantRequest[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [documents, setDocuments] = useState<TenantDocument[]>([]);
  const [requestType, setRequestType] = useState("FACILITIES");
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [credentialsLoaded, setCredentialsLoaded] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("enesko-tenant-theme");
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
    window.localStorage.setItem("enesko-tenant-theme", theme);
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

  async function loadWorkspace(t: string, tenantId: number, announce = false) {
    const headers = authHeaders(t);
    const [
      tenantResponse,
      metricsResponse,
      requestsResponse,
      announcementsResponse,
      documentsResponse,
    ] = await Promise.all([
      fetch(API + `/api/v1/tenants/${tenantId}`, { headers }),
      fetch(API + `/api/v1/tenants/${tenantId}/metrics`, { headers }),
      fetch(API + `/api/v1/tenants/${tenantId}/requests`, { headers }),
      fetch(API + `/api/v1/tenants/${tenantId}/announcements`, { headers }),
      fetch(API + `/api/v1/tenants/${tenantId}/documents`, { headers }),
    ]);

    const [
      tenantData,
      metricsData,
      requestData,
      announcementData,
      documentData,
    ] = await Promise.all([
      readJson(tenantResponse, "Tenant profile"),
      readJson(metricsResponse, "Tenant metrics"),
      readJson(requestsResponse, "Tenant requests"),
      readJson(announcementsResponse, "Tenant announcements"),
      readJson(documentsResponse, "Tenant documents"),
    ]);

    setTenant(tenantData);
    setMetrics(metricsData);
    setRequests(requestData);
    setAnnouncements(announcementData);
    setDocuments(documentData);

    if (announce) {
      setNotice("Tenant workspace refreshed.");
      window.setTimeout(() => setNotice(""), 2500);
    }
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    setCredentialsLoaded(false);
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

      const auth = await readJson(response, "Tenant sign in");
      const profileResponse = await fetch(API + "/api/v1/tenant-portal/me", {
        headers: authHeaders(auth.access_token),
      });
      const profileData: TenantProfile = await readJson(
        profileResponse,
        "Tenant workspace"
      );

      if (!profileData.user.tenant_id) {
        throw new Error("This account is not linked to an active tenant workspace.");
      }

      await loadWorkspace(auth.access_token, profileData.user.tenant_id);
      setToken(auth.access_token);
      setProfile(profileData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "ENESKO could not complete the tenant sign-in request."
      );
    } finally {
      setSigningIn(false);
    }
  }

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!profile?.user.tenant_id) {
      setError("No tenant workspace is linked to this account.");
      return;
    }

    if (!summary.trim() || !description.trim()) {
      setError("Add both a request summary and a clear description.");
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        API + `/api/v1/tenants/${profile.user.tenant_id}/requests`,
        {
          method: "POST",
          headers: {
            ...authHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            request_type: requestType,
            summary: summary.trim(),
            description: description.trim(),
            priority,
            channel: "tenant_portal",
          }),
        }
      );

      const created = await readJson(response, "Tenant request");
      setSummary("");
      setDescription("");
      setPriority("NORMAL");
      await loadWorkspace(token, profile.user.tenant_id);
      setNotice(
        `Request ${created.case.reference} created and sent to ENESKO Operations.`
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Tenant request could not be created."
      );
    } finally {
      setBusy(false);
    }
  }

  async function refreshWorkspace() {
    if (!profile?.user.tenant_id) return;
    setBusy(true);
    setError("");

    try {
      await loadWorkspace(token, profile.user.tenant_id, true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Tenant workspace could not be refreshed."
      );
    } finally {
      setBusy(false);
    }
  }

  function loadLocalCredentials() {
    setEmail(LOCAL_EMAIL);
    setPassword(LOCAL_PASSWORD);
    setCredentialsLoaded(true);
    setError("");
  }

  function signOut() {
    setToken("");
    setProfile(null);
    setTenant(null);
    setMetrics(null);
    setRequests([]);
    setAnnouncements([]);
    setDocuments([]);
    setSummary("");
    setDescription("");
    setError("");
    setNotice("");
  }

  const statusLabel = tenant?.data_status === "REFERENCE_MODEL"
    ? "Reference workspace"
    : tenant?.data_status?.replaceAll("_", " ") || "Tenant workspace";

  return (
    <div className="shell">
      <nav className="nav">
        <button className="brandButton" type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <span className="brandMark">E</span>
          <span>
            <strong>ENESKO TENANT</strong>
            <small>Tenant Operations</small>
          </span>
        </button>

        <div className="navActions">
          {profile && (
            <button className="navButton" type="button" onClick={refreshWorkspace} disabled={busy}>
              {busy ? "Working..." : "Refresh"}
            </button>
          )}
          {profile && (
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
          <span className="pill">Tenant Operations</span>
        </div>
      </nav>

      <main className="main">
        {!profile ? (
          <section className="loginLayout">
            <div className="loginCopy">
              <span className="eyebrow">Tenant workspace</span>
              <h1>Run mall operations without chasing messages.</h1>
              <p>
                Submit operational requests, track their status, receive mall
                communications and keep tenant documents in one clear workspace.
              </p>

              <div className="featureList">
                <div>
                  <strong>Track every request</strong>
                  <span>Facilities, access, security, signage and other operational needs.</span>
                </div>
                <div>
                  <strong>One operational record</strong>
                  <span>Requests flow into the same ENESKO case engine used by mall operations.</span>
                </div>
                <div>
                  <strong>Role-scoped access</strong>
                  <span>Tenant accounts can only access their own tenant workspace.</span>
                </div>
              </div>
            </div>

            <div className="card loginCard">
              <span className="eyebrow">Authorized tenant access</span>
              <h2>Sign in</h2>
              <p className="muted">
                Local development uses a reference tenant workspace. Production
                tenant accounts are provisioned only from authorized mall data.
              </p>

              <form onSubmit={login} className="formStack">
                <label>
                  Email
                  <input
                    className="input"
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </label>

                <label>
                  Password
                  <input
                    className="input"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>

                <label className="checkRow">
                  <input
                    type="checkbox"
                    checked={showPassword}
                    onChange={(event) => setShowPassword(event.target.checked)}
                  />
                  <span>Show password</span>
                </label>

                <div className="buttonRow">
                  <button className="button" type="submit" disabled={signingIn}>
                    {signingIn ? "Signing in..." : "Sign in securely"}
                  </button>
                  <button
                    className="secondaryButton"
                    type="button"
                    onClick={loadLocalCredentials}
                  >
                    Load local credentials
                  </button>
                </div>
              </form>

              {credentialsLoaded && (
                <p className="status">Local reference credentials loaded.</p>
              )}
              {error && <p className="danger">{error}</p>}
            </div>
          </section>
        ) : (
          <>
            <section className="workspaceHeader">
              <div>
                <span className="eyebrow">Tenant workspace</span>
                <h1>{tenant?.name || profile.tenant_name || "Tenant"}</h1>
                <div className="workspaceMeta">
                  <span className="dataBadge">{statusLabel}</span>
                  {tenant?.unit && <span>{tenant.unit}</span>}
                  <span>{profile.user.full_name}</span>
                </div>
              </div>

              <button
                className="button"
                type="button"
                onClick={() => document.getElementById("new-request")?.scrollIntoView({ behavior: "smooth" })}
              >
                New operations request
              </button>
            </section>

            {notice && <p className="status notice">{notice}</p>}
            {error && <p className="danger notice">{error}</p>}

            <section className="metricGrid">
              <article className="metricCard">
                <span>Total requests</span>
                <strong>{metrics?.total_requests ?? 0}</strong>
                <small>All requests submitted from this tenant workspace.</small>
              </article>
              <article className="metricCard">
                <span>Open</span>
                <strong>{metrics?.open_requests ?? 0}</strong>
                <small>Requests still requiring operational action.</small>
              </article>
              <article className="metricCard">
                <span>Resolved</span>
                <strong>{metrics?.resolved_requests ?? 0}</strong>
                <small>Requests marked resolved or closed.</small>
              </article>
            </section>

            <section className="workspaceGrid">
              <div className="card requestCard" id="new-request">
                <div className="sectionHeader">
                  <div>
                    <span className="eyebrow">New request</span>
                    <h2>Send to mall operations</h2>
                  </div>
                </div>

                <form onSubmit={submitRequest} className="formStack">
                  <div className="fieldGrid">
                    <label>
                      Request type
                      <select
                        className="input"
                        value={requestType}
                        onChange={(event) => setRequestType(event.target.value)}
                      >
                        <option value="FACILITIES">Facilities</option>
                        <option value="MAINTENANCE">Maintenance</option>
                        <option value="SECURITY">Security</option>
                        <option value="ACCESS">Access / contractor</option>
                        <option value="SIGNAGE">Signage</option>
                        <option value="MARKETING">Marketing support</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </label>

                    <label>
                      Priority
                      <select
                        className="input"
                        value={priority}
                        onChange={(event) => setPriority(event.target.value)}
                      >
                        <option value="NORMAL">Normal</option>
                        <option value="HIGH">High</option>
                        <option value="URGENT">Urgent</option>
                      </select>
                    </label>
                  </div>

                  <label>
                    Summary
                    <input
                      className="input"
                      value={summary}
                      onChange={(event) => setSummary(event.target.value)}
                      placeholder="e.g. Air-conditioning support required"
                      maxLength={240}
                    />
                  </label>

                  <label>
                    Description
                    <textarea
                      className="input textarea"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder="Describe the operational issue, location and any useful context."
                      maxLength={4000}
                    />
                  </label>

                  <button className="button" type="submit" disabled={busy}>
                    {busy ? "Submitting..." : "Create request"}
                  </button>
                </form>
              </div>

              <div className="card">
                <div className="sectionHeader">
                  <div>
                    <span className="eyebrow">Request history</span>
                    <h2>Recent requests</h2>
                  </div>
                  <span className="countBadge">{requests.length}</span>
                </div>

                <div className="requestList">
                  {requests.length ? (
                    requests.map((request) => (
                      <article className="requestItem" key={request.id}>
                        <div className="requestTopline">
                          <strong>{request.case.reference}</strong>
                          <span className={`statusBadge status-${request.case.status.toLowerCase()}`}>
                            {request.case.status.replaceAll("_", " ")}
                          </span>
                        </div>
                        <h3>{request.case.summary}</h3>
                        <p>{request.case.description}</p>
                        <div className="requestMeta">
                          <span>{request.request_type.replaceAll("_", " ")}</span>
                          <span>{request.case.priority}</span>
                          <span>{new Date(request.created_at).toLocaleString()}</span>
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="emptyState">
                      <strong>No requests yet.</strong>
                      <p>Create an operational request and it will appear here immediately.</p>
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="resourceGrid">
              <div className="card">
                <div className="sectionHeader">
                  <div>
                    <span className="eyebrow">Mall communications</span>
                    <h2>Announcements</h2>
                  </div>
                </div>

                {announcements.length ? (
                  announcements.map((announcement) => (
                    <article className="resourceItem" key={announcement.id}>
                      <strong>{announcement.title}</strong>
                      <p>{announcement.message}</p>
                      <small>{announcement.data_status.replaceAll("_", " ")}</small>
                    </article>
                  ))
                ) : (
                  <div className="emptyState">
                    <strong>No announcements.</strong>
                    <p>Authorized mall communications will appear here.</p>
                  </div>
                )}
              </div>

              <div className="card">
                <div className="sectionHeader">
                  <div>
                    <span className="eyebrow">Tenant resources</span>
                    <h2>Documents</h2>
                  </div>
                </div>

                {documents.length ? (
                  documents.map((document) => (
                    <article className="resourceItem" key={document.id}>
                      <strong>{document.title}</strong>
                      <p>{document.document_type.replaceAll("_", " ")}</p>
                      <small>{document.reference}</small>
                    </article>
                  ))
                ) : (
                  <div className="emptyState">
                    <strong>No documents.</strong>
                    <p>Authorized tenant documents will appear here when published.</p>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
