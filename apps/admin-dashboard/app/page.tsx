"use client";

import { FormEvent, useState } from "react";

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const DEMO_EMAIL = "admin@enesko.local";
const DEMO_PASSWORD = "EneskoDemo2026!";

export default function Admin() {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState("");
  const [data, setData] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [acts, setActs] = useState<any[]>([]);
  const [parking, setParking] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [signingIn, setSigningIn] = useState(false);

  async function load(t: string) {
    const headers = { Authorization: "Bearer " + t };
    const [overviewResponse, casesResponse, activationsResponse, parkingResponse] =
      await Promise.all([
        fetch(API + "/api/v1/admin/overview", { headers }),
        fetch(API + "/api/v1/cases"),
        fetch(API + "/api/v1/activations"),
        fetch(API + "/api/v1/parking"),
      ]);

    if (!overviewResponse.ok) {
      throw new Error("Admin overview could not be loaded.");
    }

    setData(await overviewResponse.json());
    setCases(await casesResponse.json());
    setActs(await activationsResponse.json());
    setParking(await parkingResponse.json());
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
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

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setError(body?.detail || "Invalid email or password.");
        return;
      }

      const result = await response.json();
      setToken(result.access_token);
      await load(result.access_token);
    } catch {
      setError(
        "Could not reach the ENESKO backend. Confirm http://127.0.0.1:8000/health is available."
      );
    } finally {
      setSigningIn(false);
    }
  }

  function restoreDemoCredentials() {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    setError("");
  }

  return (
    <div className="shell">
      <nav className="nav">
        <div className="brand">ENESKO OPS</div>
        <span className="pill">Operations Control</span>
      </nav>

      <main className="main">
        {!token ? (
          <div className="panel card">
            <div className="eyebrow">Authorized staff</div>
            <h1>Operations sign in</h1>
            <p className="muted">
              Development access for the ENESKO operations dashboard.
            </p>

            <form onSubmit={login}>
              <label htmlFor="admin-email" className="muted">
                Email
              </label>
              <input
                id="admin-email"
                className="input"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />

              <label htmlFor="admin-password" className="muted">
                Password
              </label>
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
                <button
                  className="button"
                  type="button"
                  onClick={restoreDemoCredentials}
                >
                  Restore demo credentials
                </button>
              </div>
            </form>

            {error && <p className="danger">{error}</p>}
          </div>
        ) : (
          <>
            <div className="row">
              <div>
                <div className="eyebrow">Command center</div>
                <h1>Operational overview</h1>
              </div>
              <button className="button" onClick={() => load(token)}>
                Refresh
              </button>
            </div>

            <div className="grid">
              {[
                ["Cases", data?.cases],
                ["Tenant requests", data?.tenant_requests],
                ["Activations", data?.activations],
                ["Audit events", data?.audit_events],
              ].map((metric: any) => (
                <div className="card" key={metric[0]}>
                  <div className="metric">{metric[1] ?? 0}</div>
                  <p className="muted">{metric[0]}</p>
                </div>
              ))}
            </div>

            <div className="grid">
              <div className="card">
                <h3>Case queue</h3>
                {cases.slice(0, 5).map((item) => (
                  <p key={item.id} className="muted">
                    {item.reference} · {item.status} · {item.summary}
                  </p>
                ))}
              </div>

              <div className="card">
                <h3>Activations</h3>
                {acts.slice(0, 5).map((item) => (
                  <p key={item.id} className="muted">
                    {item.reference} · {item.current_stage}
                  </p>
                ))}
              </div>

              <div className="card">
                <h3>Parking</h3>
                {parking.map((item) => (
                  <p key={item.id} className="muted">
                    {item.name} · {item.occupancy_status}
                  </p>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
