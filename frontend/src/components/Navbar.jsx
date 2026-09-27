import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import client from "../api/client";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user) return;
    function poll() {
      client
        .get("/notifications")
        .then((res) => setUnread(res.data.unread_count))
        .catch(() => {});
    }
    poll();
    const id = setInterval(poll, 30000);
    return () => clearInterval(id);
  }, [user]);

  return (
    <nav>
      <Link to="/">SkillSphere</Link>
      {user && <Link to="/search">Find a Tutor</Link>}
      {user?.is_tutor && <Link to="/skills">My Skills</Link>}
      {user && <Link to="/sessions">My Sessions</Link>}
      {user && <Link to="/profile">Profile</Link>}
      {user && (
        <Link to="/notifications">Notifications{unread > 0 ? ` (${unread})` : ""}</Link>
      )}
      {user?.is_admin && <Link to="/admin">Admin</Link>}
      <span className="spacer" />
      {user ? (
        <button
          className="link"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Logout ({user.name})
        </button>
      ) : (
        <>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
