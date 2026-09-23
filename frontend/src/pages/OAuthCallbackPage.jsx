import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function OAuthCallbackPage() {
  const { completeOAuth } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("access_token");
    const oauthError = params.get("error");
    if (oauthError) { setError(oauthError); return; }
    if (!token) { setError("Missing access token from the identity provider."); return; }
    completeOAuth(token).then(() => navigate("/ask", { replace: true })).catch((err) => setError(err.message || "Could not finish sign-in."));
  }, [completeOAuth, navigate]);
  return (
    <div className="boot">
      <div className="boot-card">
        <span className="brand-mark">AK</span>
        <p>{error || "Finishing sign-in…"}</p>
        {error && <a href="/login" className="oauth-btn">Back to sign in</a>}
      </div>
    </div>
  );
}
