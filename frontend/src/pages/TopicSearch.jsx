import { useState } from "react";
import client, { apiErrorMessage } from "../api/client";
import RequestSessionForm from "../components/RequestSessionForm";

export default function TopicSearch() {
  const [mode, setMode] = useState("ai"); // "ai" | "keyword"

  // AI free-text flow (REQ-6, REQ-7, REQ-8)
  const [problemText, setProblemText] = useState("");
  const [aiResult, setAiResult] = useState(null);
  const [aiError, setAiError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  // Keyword fallback (REQ-5)
  const [q, setQ] = useState("");
  const [keywordResults, setKeywordResults] = useState(null);
  const [keywordSearched, setKeywordSearched] = useState(false);
  const [keywordError, setKeywordError] = useState("");

  const [requestingTopicId, setRequestingTopicId] = useState(null);
  const [requestSent, setRequestSent] = useState(false);

  async function handleAiSubmit(e) {
    e.preventDefault();
    setAiError("");
    setAiResult(null);
    if (!problemText.trim()) return;
    setAiLoading(true);
    try {
      const res = await client.post("/ai/detect-topic", { text: problemText });
      setAiResult(res.data);
    } catch (err) {
      setAiError(apiErrorMessage(err));
    } finally {
      setAiLoading(false);
    }
  }

  async function handleKeywordSearch(e) {
    e.preventDefault();
    setKeywordError("");
    if (!q.trim()) return;
    try {
      const res = await client.get("/skills/search", { params: { q } });
      setKeywordResults(res.data.results);
      setKeywordSearched(true);
    } catch (err) {
      setKeywordError(apiErrorMessage(err));
    }
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button className={mode === "ai" ? "" : "secondary"} onClick={() => setMode("ai")}>
            Describe my problem
          </button>
          <button className={mode === "keyword" ? "" : "secondary"} onClick={() => setMode("keyword")}>
            Keyword search
          </button>
        </div>

        {mode === "ai" ? (
          <>
            <h2>What do you need help with?</h2>
            <p style={{ fontSize: 13, color: "#666" }}>
              Describe your problem in your own words — the AI engine detects the topic and
              ranks tutors for you (topic match, trust score, sessions completed, availability).
            </p>
            <form onSubmit={handleAiSubmit}>
              <div className="field">
                <textarea
                  placeholder="e.g. I don't understand how to insert and delete nodes in a binary search tree..."
                  value={problemText}
                  onChange={(e) => setProblemText(e.target.value)}
                  rows={3}
                />
              </div>
              {aiError && <p className="error">{aiError}</p>}
              <button type="submit" disabled={aiLoading}>
                {aiLoading ? "Analyzing..." : "Find a tutor"}
              </button>
            </form>
          </>
        ) : (
          <>
            <h2>Search for a topic</h2>
            <form onSubmit={handleKeywordSearch} style={{ display: "flex", gap: 8 }}>
              <input
                style={{ flex: 1 }}
                placeholder="e.g. binary search trees, recursion..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <button type="submit">Search</button>
            </form>
            {keywordError && <p className="error">{keywordError}</p>}
          </>
        )}
      </div>

      {mode === "ai" && aiResult && (
        <>
          {!aiResult.detected ? (
            <div className="card">
              <p>{aiResult.message}</p>
            </div>
          ) : (
            <>
              <div className="card">
                <h3>
                  Detected topic: {aiResult.detected.skill_name} — {aiResult.detected.topic_name}
                </h3>
                <p style={{ fontSize: 13, color: "#666" }}>
                  Confidence: {(aiResult.detected.confidence * 100).toFixed(0)}%
                </p>
              </div>

              <div className="card">
                <h3>Recommended tutors</h3>
                {aiResult.tutors.length === 0 && <p>No tutors currently teach this exact topic.</p>}
                {aiResult.tutors.map((t) => (
                  <div key={t.skill.skill_id}>
                    <div className="skill-row">
                      <div>
                        <strong>{t.tutor.name}</strong>{" "}
                        <span className="pill">trust {t.tutor.trust_score}</span>
                        <div style={{ fontSize: 13, color: "#666" }}>
                          match {(t.breakdown.relevance * 100).toFixed(0)}% · {t.breakdown.completed_sessions}{" "}
                          sessions completed ·{" "}
                          {t.breakdown.has_availability ? "has availability" : "no availability set"}
                        </div>
                        {t.skill.description && (
                          <div style={{ fontSize: 13, color: "#666" }}>{t.skill.description}</div>
                        )}
                      </div>
                      <button onClick={() => { setRequestingTopicId(t.skill.skill_id); setRequestSent(false); }}>
                        Request session
                      </button>
                    </div>
                    {requestingTopicId === t.skill.skill_id && !requestSent && (
                      <RequestSessionForm
                        topicId={t.skill.skill_id}
                        tutorName={t.tutor.name}
                        onCancel={() => setRequestingTopicId(null)}
                        onDone={() => setRequestSent(true)}
                      />
                    )}
                    {requestingTopicId === t.skill.skill_id && requestSent && (
                      <p className="success">
                        Request sent! Track it under "My Sessions" once the tutor responds.
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {aiResult.related_topics.length > 0 && (
                <div className="card">
                  <h3>Related topics</h3>
                  {aiResult.related_topics.map((rt, i) => (
                    <div key={i} className="skill-row">
                      <span>
                        {rt.skill_name} — {rt.topic_name}
                      </span>
                      <span className="pill">{rt.reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {mode === "keyword" && keywordSearched && (
        <div className="card">
          <h3>Results</h3>
          {keywordResults.length === 0 && <p>No matching topics found.</p>}
          {keywordResults.map((r) => (
            <div key={r.skill_id}>
              <div className="skill-row">
                <div>
                  <strong>{r.skill_name}</strong> — {r.topic_name} <span className="pill">{r.difficulty}</span>
                  <div style={{ fontSize: 13, color: "#666" }}>
                    Tutor: {r.tutor?.name} (trust score {r.tutor?.trust_score})
                  </div>
                  {r.description && <div style={{ fontSize: 13, color: "#666" }}>{r.description}</div>}
                </div>
                <button onClick={() => { setRequestingTopicId(r.skill_id); setRequestSent(false); }}>
                  Request session
                </button>
              </div>
              {requestingTopicId === r.skill_id && !requestSent && (
                <RequestSessionForm
                  topicId={r.skill_id}
                  tutorName={r.tutor?.name}
                  onCancel={() => setRequestingTopicId(null)}
                  onDone={() => setRequestSent(true)}
                />
              )}
              {requestingTopicId === r.skill_id && requestSent && (
                <p className="success">Request sent! Track it under "My Sessions".</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
