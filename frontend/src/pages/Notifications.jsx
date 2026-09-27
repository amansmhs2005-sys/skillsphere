import { useEffect, useState } from "react";
import client from "../api/client";

export default function Notifications() {
  const [notes, setNotes] = useState([]);

  function load() {
    client.get("/notifications").then((res) => setNotes(res.data.notifications));
  }

  useEffect(() => {
    load();
  }, []);

  async function markRead(id) {
    await client.post(`/notifications/${id}/read`);
    load();
  }

  async function markAllRead() {
    await client.post("/notifications/read-all");
    load();
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2>Notifications</h2>
          <button className="secondary" onClick={markAllRead}>
            Mark all read
          </button>
        </div>
        {notes.length === 0 && <p>You're all caught up.</p>}
        {notes.map((n) => (
          <div
            key={n.notification_id}
            className="skill-row"
            style={{ background: n.is_read ? "transparent" : "#f0f0ff" }}
          >
            <div>
              <div>{n.message}</div>
              <div style={{ fontSize: 12, color: "#888" }}>{new Date(n.created_at).toLocaleString()}</div>
            </div>
            {!n.is_read && (
              <button className="secondary" onClick={() => markRead(n.notification_id)}>
                Mark read
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
