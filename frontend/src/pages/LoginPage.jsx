import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const DEMO_ACCOUNTS = [
  { email: "employee@acme.com", password: "employee123", label: "Employee", hint: "Ask and read public policy" },
  { email: "admin@acme.com", password: "admin123", label: "Admin", hint: "Seed index and run quality checks" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      const next = location.state?.from && location.state.from !== "/login" ? location.state.from : "/ask";
      navigate(next, { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <section className="login-hero">
        <p className="eyebrow">Acme Knowledge</p>
        <h1>Ask company policy. Get cited answers.</h1>
        <p className="lede">
          Employees can question leave, remote work, and other published policies.
          Admins keep the index current. The assistant will say when the documents do not cover the question.
        </p>
        <ul className="login-points">
          <li>Answers grounded in indexed policy text</li>
          <li>Role-based access with a signed session</li>
          <li>Sources shown next to every supported answer</li>
        </ul>
      </section>

      <section className="login-panel">
        <h2>Sign in</h2>
        <p className="muted">Use your work email. Demo accounts are listed below for this environment.</p>
        <form onSubmit={onSubmit}>
          <label>
            Work email
            <input
              type="email"
              value={email}
              autoComplete="username"
              placeholder="name@acme.com"
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <div className="password-row">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button type="button" className="ghost compact" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Continue"}
          </button>
        </form>
        <div className="demo-grid">
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.email}
              type="button"
              className="ghost demo-card"
              onClick={() => {
                setEmail(account.email);
                setPassword(account.password);
                setError("");
              }}
            >
              <strong>{account.label}</strong>
              <span>{account.email}</span>
              <small>{account.hint}</small>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
