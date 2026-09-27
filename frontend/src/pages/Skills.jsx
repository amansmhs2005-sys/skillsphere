import { useEffect, useState } from "react";
import client, { apiErrorMessage } from "../api/client";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"];

export default function Skills() {
  const [skills, setSkills] = useState([]);
  const [form, setForm] = useState({
    skill_name: "",
    topic_name: "",
    difficulty: "beginner",
    description: "",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  function load() {
    client.get("/skills/mine").then((res) => setSkills(res.data.skills));
  }

  async function addSkill(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/skills", form);
      setForm({ skill_name: "", topic_name: "", difficulty: "beginner", description: "" });
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function removeSkill(id) {
    await client.delete(`/skills/${id}`);
    load();
  }

  return (
    <div className="container">
      <div className="card">
        <h2>My skills &amp; topics</h2>
        {skills.length === 0 && <p>You haven't added any topics yet.</p>}
        {skills.map((s) => (
          <div key={s.skill_id} className="skill-row">
            <div>
              <strong>{s.skill_name}</strong> — {s.topic_name}{" "}
              <span className="pill">{s.difficulty}</span>
              {s.description && <div style={{ fontSize: 13, color: "#666" }}>{s.description}</div>}
            </div>
            <button className="danger" onClick={() => removeSkill(s.skill_id)}>
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Add a topic you can tutor</h3>
        <form onSubmit={addSkill}>
          <div className="field">
            <label>Skill / subject (e.g. Data Structures)</label>
            <input
              value={form.skill_name}
              onChange={(e) => setForm({ ...form, skill_name: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Specific topic (e.g. Binary Search Trees)</label>
            <input
              value={form.topic_name}
              onChange={(e) => setForm({ ...form, topic_name: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Difficulty</label>
            <select
              value={form.difficulty}
              onChange={(e) => setForm({ ...form, difficulty: e.target.value })}
            >
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Description (optional)</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit">Add topic</button>
        </form>
      </div>
    </div>
  );
}
