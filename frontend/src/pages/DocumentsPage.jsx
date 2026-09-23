import React, { useEffect, useMemo, useState } from "react";
import { listDocuments } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function DocumentsPage() {
  const { isAdmin } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listDocuments()
      .then((rows) => setDocuments(Array.isArray(rows) ? rows : []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return documents;
    return documents.filter((document) =>
      `${document.title} ${document.owner} ${document.access_level}`.toLowerCase().includes(needle)
    );
  }, [documents, query]);

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="eyebrow">Policies</p>
          <h1>What the assistant can read</h1>
        </div>
        <input
          className="filter"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by title or owner"
        />
      </header>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading indexed policies…</p>}
      {!loading && documents.length === 0 && (
        <div className="empty-card">
          <h2>No policies indexed yet</h2>
          <p className="muted">
            {isAdmin
              ? "Open Admin and seed the sample leave and remote-work policies."
              : "Ask an admin to seed the policy library, then try again."}
          </p>
        </div>
      )}
      <div className="cards">
        {visible.map((document) => (
          <article key={document.id} className="card">
            <div className="card-top">
              <h2>{document.title}</h2>
              <span className="status-pill">{document.lifecycle_state}</span>
            </div>
            <p className="muted">
              {document.access_level} · v{document.version}
            </p>
            <p>{document.owner}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
