import { useState } from "react";
import client, { apiErrorMessage } from "../api/client";

export default function RequestSessionForm({ topicId, tutorName, onDone, onCancel }) {
  const [form, setForm] = useState({
    mode: "online",
    problem_description: "",
    preferred_date: "",
    preferred_time: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await client.post("/sessions", { topic_id: topicId, ...form });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ background: "#f9f9ff" }}>
      <h4>Request a session with {tutorName}</h4>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label>Describe your problem</label>
          <textarea
            value={form.problem_description}
            onChange={(e) => setForm({ ...form, problem_description: e.target.value })}
            required
          />
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <div className="field">
            <label>Preferred date</label>
            <input
              type="date"
              value={form.preferred_date}
              onChange={(e) => setForm({ ...form, preferred_date: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Preferred time</label>
            <input
              type="time"
              value={form.preferred_time}
              onChange={(e) => setForm({ ...form, preferred_time: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Mode</label>
            <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={submitting}>
            {submitting ? "Sending..." : "Send request"}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
