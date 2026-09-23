import React, { useEffect, useState } from "react";
import {
  fetchAdminDashboard,
  runEvaluations,
  runQualityGate,
  seedDocuments,
} from "../api/client.js";

export default function AdminPage() {
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [evalSummary, setEvalSummary] = useState(null);

  async function loadDashboard() {
    setError("");
    const payload = await fetchAdminDashboard();
    setDash(payload);
  }

  useEffect(() => {
    loadDashboard()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function run(label, action) {
    setBusy(label);
    setError("");
    try {
      const result = await action();
      if (label !== "seed") setEvalSummary({ label, result });
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  const feedback = dash?.feedback || {};
  const rate = Math.round((feedback.satisfaction_rate || 0) * 100);

  return (
    <section>
      <header className="page-head">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>Index health and quality</h1>
        </div>
        <button type="button" className="ghost compact" disabled={Boolean(busy)} onClick={() => loadDashboard()}>
          Refresh
        </button>
      </header>

      {loading && <p className="muted">Loading workspace…</p>}
      {error && <p className="error">{error}</p>}

      {dash && (
        <>
          <div className="metrics">
            <article className="metric">
              <p className="eyebrow">Policies</p>
              <strong>{dash.documents.count}</strong>
              <span>indexed documents</span>
            </article>
            <article className="metric">
              <p className="eyebrow">Chunks</p>
              <strong>{dash.index.vector_memory}</strong>
              <span>in the live index</span>
            </article>
            <article className="metric">
              <p className="eyebrow">Feedback</p>
              <strong>{feedback.total || 0}</strong>
              <span>{rate}% marked helpful</span>
            </article>
            <article className="metric">
              <p className="eyebrow">Ratings</p>
              <strong>
                {feedback.positive || 0}/{feedback.negative || 0}
              </strong>
              <span>helpful / not helpful</span>
            </article>
          </div>

          <div className="admin-grid">
            <article className="card">
              <h2>Services</h2>
              <ul className="status-list">
                <li>Gemini — {dash.services.gemini}</li>
                <li>Voyage rerank — {dash.services.voyage}</li>
                <li>Qdrant — {dash.index.qdrant}</li>
                <li>OpenSearch — {dash.index.opensearch}</li>
                <li>Neon — {dash.services.postgres}</li>
                <li>Langfuse — {dash.services.langfuse}</li>
              </ul>
            </article>
            <article className="card">
              <h2>Operations</h2>
              <p className="muted">These actions are admin-only. Employees cannot reach them.</p>
              <div className="admin-actions">
                <button type="button" disabled={Boolean(busy)} onClick={() => run("seed", seedDocuments)}>
                  {busy === "seed" ? "Seeding…" : "Seed policies"}
                </button>
                <button type="button" disabled={Boolean(busy)} onClick={() => run("eval", runEvaluations)}>
                  {busy === "eval" ? "Evaluating…" : "Run evaluations"}
                </button>
                <button type="button" disabled={Boolean(busy)} onClick={() => run("gate", runQualityGate)}>
                  {busy === "gate" ? "Checking…" : "Quality gate"}
                </button>
              </div>
            </article>
          </div>

          <h2>Indexed policies</h2>
          {dash.documents.items.length === 0 ? (
            <p className="muted">Nothing indexed yet. Seed policies first.</p>
          ) : (
            <div className="cards">
              {dash.documents.items.map((document) => (
                <article key={document.id} className="card">
                  <div className="card-top">
                    <h2>{document.title}</h2>
                    <span className="status-pill">{document.lifecycle_state}</span>
                  </div>
                  <p className="muted">
                    {document.access_level} · v{document.version} · {document.chunks} chunks
                  </p>
                  <p>{document.owner}</p>
                </article>
              ))}
            </div>
          )}

          <h2>Recent feedback</h2>
          {(feedback.recent || []).length === 0 ? (
            <p className="muted">No ratings yet. They appear after employees mark an answer helpful or not.</p>
          ) : (
            <div className="cards">
              {feedback.recent.map((item, index) => (
                <article key={`${item.trace_id}-${index}`} className="card">
                  <strong>{item.rating > 0 ? "Helpful" : "Not helpful"}</strong>
                  <p className="muted">{item.comment || "No comment"}</p>
                  <p className="muted">{item.created_at}</p>
                </article>
              ))}
            </div>
          )}

          {evalSummary && (
            <div className="eval-box">
              <h2>{evalSummary.label === "gate" ? "Quality gate" : "Evaluation"} result</h2>
              {evalSummary.result.gate_passed !== undefined && (
                <p className={evalSummary.result.gate_passed ? "ok" : "error"}>
                  {evalSummary.result.status}
                </p>
              )}
              {evalSummary.result.total_cases !== undefined && (
                <div className="metrics compact">
                  <article className="metric">
                    <p className="eyebrow">Cases</p>
                    <strong>{evalSummary.result.total_cases}</strong>
                  </article>
                  <article className="metric">
                    <p className="eyebrow">Faithfulness</p>
                    <strong>{Math.round((evalSummary.result.mean_faithfulness || 0) * 100)}%</strong>
                  </article>
                  <article className="metric">
                    <p className="eyebrow">No-answer</p>
                    <strong>{Math.round((evalSummary.result.no_answer_accuracy || 0) * 100)}%</strong>
                  </article>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
