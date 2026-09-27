import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import client, { apiErrorMessage } from "../api/client";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      setMessage("No verification token found in the link.");
      return;
    }
    client
      .post("/auth/verify-email", { token })
      .then((res) => {
        setStatus("success");
        setMessage(res.data.message);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(apiErrorMessage(err));
      });
  }, [params]);

  return (
    <div className="container">
      <div className="card">
        <h2>Email verification</h2>
        {status === "verifying" && <p>Verifying your email...</p>}
        {status === "success" && (
          <>
            <p className="success">{message}</p>
            <Link to="/login">
              <button>Go to login</button>
            </Link>
          </>
        )}
        {status === "error" && <p className="error">{message}</p>}
      </div>
    </div>
  );
}
