import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import client, { apiErrorMessage } from "../api/client";

export default function Register() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "learner",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);
    try {
      const res = await client.post("/auth/register", form);
      setSuccess(res.data.message);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Create your SkillSphere account</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Full name</label>
            <input
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Institutional email</label>
            <input
              type="email"
              placeholder="you@college.edu"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Password (min 8 characters)</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              minLength={8}
              required
            />
          </div>
          <div className="field">
            <label>I want to join as a</label>
            <select value={form.role} onChange={(e) => update("role", e.target.value)}>
              <option value="learner">Learner</option>
              <option value="tutor">Tutor</option>
              <option value="both">Both</option>
            </select>
          </div>

          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}

          <button type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Register"}
          </button>
        </form>
        <p style={{ marginTop: 14, fontSize: 13 }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
