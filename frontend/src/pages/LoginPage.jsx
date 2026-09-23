import React, { useEffect, useState } from "react";
import { fetchOAuthStatus } from "../api/oauth.js";

export default function LoginPage() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetchOAuthStatus().then(setStatus).catch((err) => setError(err.message));
  }, []);
  const provider = (status?.provider || "oauth").replace(/^\w/, (letter) => letter.toUpperCase());
  return (
    <div className="login-wrap">
      <section className="login-hero">
        <p className="eyebrow">Acme Knowledge</p>
        <h1>Ask company policy. Get cited answers.</h1>
        <p className="lede">Sign in with your work identity provider. Access follows your company account, not a local password.</p>
        <ul className="login-points">
          <li>OAuth 2.0 / OIDC authorization code flow</li>
          <li>Role-based access after the provider handshake</li>
          <li>Sources shown next to every supported answer</li>
        </ul>
      </section>
      <section className="login-panel">
        <h2>Sign in</h2>
        <p className="muted">
          {status?.configured
            ? `Continue with ${provider}. You will be redirected to your identity provider.`
            : "OAuth is not configured yet. Set OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET."}
        </p>
        {error && <p className="error">{error}</p>}
        <a className="oauth-btn" href="/api/v1/auth/oauth/login" onClick={(event) => { if (!status?.configured) event.preventDefault(); }}>
          Continue with {provider}
        </a>
      </section>
    </div>
  );
}
