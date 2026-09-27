import { useEffect, useState } from "react";
import client, { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

function CompleteForm({ session, onDone }) {
  const [notes, setNotes] = useState("");
  const [attended, setAttended] = useState(true);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/sessions/${session.request_id}/complete`, {
        session_notes: notes,
        attended,
      });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 10 }}>
      <div className="field">
        <label>Did the learner attend?</label>
        <select value={attended ? "yes" : "no"} onChange={(e) => setAttended(e.target.value === "yes")}>
          <option value="yes">Yes</option>
          <option value="no">No — no-show</option>
        </select>
      </div>
      <div className="field">
        <label>Session notes (used to generate the summary)</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4} />
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit">Mark complete</button>
    </form>
  );
}

function ReviewForm({ session, onDone }) {
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/sessions/${session.request_id}/review`, { rating: Number(rating), feedback });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 10 }}>
      <div className="field">
        <label>Rating</label>
        <select value={rating} onChange={(e) => setRating(e.target.value)}>
          {[5, 4, 3, 2, 1].map((n) => (
            <option key={n} value={n}>
              {n} star{n > 1 ? "s" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>Feedback (optional)</label>
        <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} />
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit">Submit review</button>
    </form>
  );
}

function ReportForm({ session, onDone }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post(`/sessions/${session.request_id}/report`, { reason });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 10 }}>
      <div className="field">
        <label>What happened?</label>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} required />
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit" className="danger">
        Submit report
      </button>
    </form>
  );
}

function SessionCard({ session, role, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [activeForm, setActiveForm] = useState(null); // "complete" | "review" | "report" | null
  const [error, setError] = useState("");

  function loadDetail() {
    client.get(`/sessions/${session.request_id}`).then((res) => setDetail(res.data.session));
  }

  useEffect(() => {
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.request_id]);

  async function act(action, body = {}) {
    setError("");
    try {
      await client.post(`/sessions/${session.request_id}/${action}`, body);
      loadDetail();
      onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  const otherParty = role === "tutor" ? session.learner_name : session.tutor_name;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <strong>
            {session.skill_name} — {session.topic_name}
          </strong>
          <div style={{ fontSize: 13, color: "#666" }}>
            {role === "tutor" ? "Learner" : "Tutor"}: {otherParty} · {session.mode}
          </div>
          <div style={{ fontSize: 13, color: "#666" }}>
            {session.scheduled_date
              ? `Scheduled: ${session.scheduled_date} ${session.scheduled_time || ""}`
              : session.preferred_date
              ? `Requested: ${session.preferred_date} ${session.preferred_time || ""}`
              : "No date set"}
          </div>
        </div>
        <span className="pill">{session.status}</span>
      </div>

      {detail?.problem_description && (
        <p style={{ fontSize: 13, marginTop: 8 }}>
          <em>{detail.problem_description}</em>
        </p>
      )}

      {error && <p className="error">{error}</p>}

      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        {role === "tutor" && session.status === "pending" && (
          <>
            <button onClick={() => act("accept")}>Accept</button>
            <button className="secondary" onClick={() => act("reject")}>
              Reject
            </button>
          </>
        )}
        {(session.status === "pending" || session.status === "accepted") && (
          <button className="secondary" onClick={() => act("cancel")}>
            Cancel
          </button>
        )}
        {role === "tutor" && session.status === "accepted" && (
          <button onClick={() => setActiveForm(activeForm === "complete" ? null : "complete")}>
            Mark complete
          </button>
        )}
        {role === "learner" && session.status === "completed" && !detail?.has_review && (
          <button onClick={() => setActiveForm(activeForm === "review" ? null : "review")}>Leave review</button>
        )}
        {(session.status === "completed" || session.status === "accepted") && (
          <button className="secondary" onClick={() => setActiveForm(activeForm === "report" ? null : "report")}>
            Report issue
          </button>
        )}
      </div>

      {activeForm === "complete" && (
        <CompleteForm session={session} onDone={() => { setActiveForm(null); loadDetail(); onChanged(); }} />
      )}
      {activeForm === "review" && (
        <ReviewForm session={session} onDone={() => { setActiveForm(null); loadDetail(); onChanged(); }} />
      )}
      {activeForm === "report" && (
        <ReportForm session={session} onDone={() => setActiveForm(null)} />
      )}

      {detail?.session_summary && (
        <div style={{ marginTop: 10, background: "#f6f7fb", padding: 10, borderRadius: 6, fontSize: 13 }}>
          <strong>Session summary</strong>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: "6px 0 0" }}>
            {detail.session_summary}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function Sessions() {
  const { user } = useAuth();
  const [role, setRole] = useState(user?.is_tutor ? "tutor" : "learner");
  const [sessions, setSessions] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");

  function load() {
    client
      .get("/sessions/mine", { params: { role, status: statusFilter || undefined } })
      .then((res) => setSessions(res.data.sessions));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, statusFilter]);

  return (
    <div className="container">
      <div className="card">
        <h2>My sessions</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          {user?.is_learner && (
            <button className={role === "learner" ? "" : "secondary"} onClick={() => setRole("learner")}>
              As learner
            </button>
          )}
          {user?.is_tutor && (
            <button className={role === "tutor" ? "" : "secondary"} onClick={() => setRole("tutor")}>
              As tutor
            </button>
          )}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ marginLeft: "auto" }}>
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="completed">Completed</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        {sessions.length === 0 && <p>No sessions here yet.</p>}
      </div>

      {sessions.map((s) => (
        <SessionCard key={s.request_id} session={s} role={role} onChanged={load} />
      ))}
    </div>
  );
}
