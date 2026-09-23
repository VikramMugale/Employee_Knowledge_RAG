import React from "react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="empty-card">
      <p className="eyebrow">404</p>
      <h1>That page is not in this workspace</h1>
      <p className="muted">Check the address or go back to Ask.</p>
      <Link className="button-link" to="/ask">
        Go to Ask
      </Link>
    </section>
  );
}
