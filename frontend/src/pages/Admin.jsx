import { useEffect, useState } from "react";
import client, { apiErrorMessage } from "../api/client";

function ResolveReportForm({ report, onDone }) {
  const [status, setStatus] = useState("reviewed");
  const [action, setAction] = useState("");
  const [suspend, setSuspend] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/admin/reports/${report.report_id}/resolve`, {
        status,
        action,
        suspend_user_id: suspend ? report.reported_by : undefined,
      });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 8 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <div className="field">
          <label>Outcome</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="reviewed">Reviewed — action taken</option>
            <option value="dismissed">Dismissed — no action</option>
          </select>
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label>Notes</label>
          <input value={action} onChange={(e) => setAction(e.target.value)} />
        </div>
      </div>
      <label style={{ fontSize: 13, display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
        <input type="checkbox" checked={suspend} onChange={(e) => setSuspend(e.target.checked)} />
        Suspend the reported party's account
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit">Resolve report</button>
    </form>
  );
}

export default function Admin() {
  const [tab, setTab] = useState("users"); // "users" | "reports" | "stats"
  const [users, setUsers] = useState([]);
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  function loadUsers() {
    client.get("/admin/users").then((res) => setUsers(res.data.users)).catch((e) => setError(apiErrorMessage(e)));
  }
  function loadReports() {
    client
      .get("/admin/reports", { params: { status: "open" } })
      .then((res) => setReports(res.data.reports))
      .catch((e) => setError(apiErrorMessage(e)));
  }
  function loadStats() {
    client.get("/admin/stats").then((res) => setStats(res.data)).catch((e) => setError(apiErrorMessage(e)));
  }

  useEffect(() => {
    if (tab === "users") loadUsers();
    if (tab === "reports") loadReports();
    if (tab === "stats") loadStats();
  }, [tab]);

  async function verifyUser(id) {
    await client.post(`/admin/users/${id}/verify`);
    loadUsers();
  }
  async function suspendUser(id) {
    await client.post(`/admin/users/${id}/suspend`);
    loadUsers();
  }
  async function unsuspendUser(id) {
    await client.post(`/admin/users/${id}/unsuspend`);
    loadUsers();
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Admin dashboard</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={tab === "users" ? "" : "secondary"} onClick={() => setTab("users")}>
            Users
          </button>
          <button className={tab === "reports" ? "" : "secondary"} onClick={() => setTab("reports")}>
            Reports
          </button>
          <button className={tab === "stats" ? "" : "secondary"} onClick={() => setTab("stats")}>
            Platform stats
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {tab === "users" && (
        <div className="card">
          <h3>Users</h3>
          {users.map((u) => (
            <div key={u.user_id} className="skill-row">
              <div>
                <strong>{u.name}</strong> — {u.email}
                <div style={{ fontSize: 12, color: "#888" }}>
                  {u.is_tutor && <span className="pill">tutor</span>}{" "}
                  {u.is_learner && <span className="pill">learner</span>}{" "}
                  {u.admin_verified ? (
                    <span className="pill">admin-verified</span>
                  ) : (
                    <span className="pill">not admin-verified</span>
                  )}{" "}
                  {u.is_suspended && <span className="pill">suspended</span>}{" "}
                  trust {u.trust_score}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {!u.admin_verified && <button onClick={() => verifyUser(u.user_id)}>Verify</button>}
                {u.is_suspended ? (
                  <button className="secondary" onClick={() => unsuspendUser(u.user_id)}>
                    Unsuspend
                  </button>
                ) : (
                  <button className="danger" onClick={() => suspendUser(u.user_id)}>
                    Suspend
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "reports" && (
        <div className="card">
          <h3>Open reports</h3>
          {reports.length === 0 && <p>No open reports.</p>}
          {reports.map((r) => (
            <div key={r.report_id} style={{ borderBottom: "1px solid #eee", padding: "10px 0" }}>
              <div>
                <strong>Session #{r.session_id}</strong> — reported by {r.reporter_name}
              </div>
              <div style={{ fontSize: 13, color: "#666" }}>{r.reason}</div>
              <ResolveReportForm report={r} onDone={loadReports} />
            </div>
          ))}
        </div>
      )}

      {tab === "stats" && stats && (
        <div className="card">
          <h3>Platform activity</h3>
          <p>
            <strong>Users:</strong> {stats.users.total} total · {stats.users.pending_admin_verification} pending
            verification · {stats.users.suspended} suspended
          </p>
          <p>
            <strong>Sessions:</strong>{" "}
            {Object.entries(stats.sessions)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ")}
          </p>
          <p>
            <strong>Open reports:</strong> {stats.reports.open}
          </p>
        </div>
      )}
    </div>
  );
}
