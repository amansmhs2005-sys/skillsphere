import { useEffect, useState } from "react";
import client, { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Profile() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({ name: "", branch: "", year: "", bio: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [slots, setSlots] = useState([]);
  const [newSlot, setNewSlot] = useState({ day: "Mon", start_time: "09:00", end_time: "10:00" });

  const [progress, setProgress] = useState([]);

  useEffect(() => {
    if (user) {
      setForm({
        name: user.name || "",
        branch: user.branch || "",
        year: user.year || "",
        bio: user.bio || "",
      });
    }
    if (user?.is_tutor) loadAvailability();
    if (user?.is_learner) loadProgress();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  function loadAvailability() {
    client.get("/profile/availability").then((res) => setSlots(res.data.availability));
  }

  function loadProgress() {
    client.get("/profile/progress").then((res) => setProgress(res.data.progress));
  }

  async function saveProfile(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const res = await client.put("/profile", form);
      setUser(res.data.user);
      setSuccess("Profile updated.");
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function addSlot(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/profile/availability", newSlot);
      loadAvailability();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function removeSlot(id) {
    await client.delete(`/profile/availability/${id}`);
    loadAvailability();
  }

  if (!user) return null;

  return (
    <div className="container">
      <div className="card">
        <h2>Your profile</h2>
        <form onSubmit={saveProfile}>
          <div className="field">
            <label>Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label>Branch</label>
            <input value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value })} />
          </div>
          <div className="field">
            <label>Year</label>
            <input value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
          </div>
          <div className="field">
            <label>Bio</label>
            <textarea value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
          </div>
          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}
          <button type="submit">Save profile</button>
        </form>
      </div>

      {user.is_tutor && (
        <div className="card">
          <h3>Availability</h3>
          {slots.length === 0 && <p>No availability set yet.</p>}
          {slots.map((s) => (
            <div key={s.availability_id} className="skill-row">
              <span>
                {s.day} · {s.start_time}–{s.end_time}
              </span>
              <button className="danger" onClick={() => removeSlot(s.availability_id)}>
                Remove
              </button>
            </div>
          ))}
          <form onSubmit={addSlot} style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "flex-end" }}>
            <div className="field">
              <label>Day</label>
              <select value={newSlot.day} onChange={(e) => setNewSlot({ ...newSlot, day: e.target.value })}>
                {DAYS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Start</label>
              <input
                type="time"
                value={newSlot.start_time}
                onChange={(e) => setNewSlot({ ...newSlot, start_time: e.target.value })}
              />
            </div>
            <div className="field">
              <label>End</label>
              <input
                type="time"
                value={newSlot.end_time}
                onChange={(e) => setNewSlot({ ...newSlot, end_time: e.target.value })}
              />
            </div>
            <button type="submit">Add slot</button>
          </form>
        </div>
      )}

      {user.is_learner && (
        <div className="card">
          <h3>Topic progress</h3>
          {progress.length === 0 && (
            <p>
              No topics tracked yet — this fills in once you complete sessions with a
              tutor.
            </p>
          )}
          {progress.map((p) => (
            <div key={p.progress_id} className="skill-row">
              <span>
                {p.skill_name} — {p.topic_name}
              </span>
              <span className="pill">{p.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
