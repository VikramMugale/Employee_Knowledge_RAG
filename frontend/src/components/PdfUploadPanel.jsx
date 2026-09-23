import React, { useState } from "react";
import { uploadDocument, getIngestJob } from "../api/client.js";

export default function PdfUploadPanel({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [accessLevel, setAccessLevel] = useState("PUBLIC_INTERNAL");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function waitForJob(jobId) {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const job = await getIngestJob(jobId);
      if (job.status === "completed" || job.status === "failed") return job;
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
    return { status: "processing", message: "Still indexing…" };
  }

  async function submit(event) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError("");
    setStatus("Uploading…");
    try {
      const result = await uploadDocument(file, accessLevel, true);
      if (result.job_id) {
        setStatus("Queued for indexing…");
        const job = await waitForJob(result.job_id);
        setStatus(job.status === "completed" ? `Indexed ${file.name}` : `Job ${job.status}: ${job.message || ""}`);
      } else {
        setStatus(`Indexed ${result.document || file.name}`);
      }
      setFile(null);
      event.target.reset();
      if (onUploaded) onUploaded();
    } catch (err) {
      setError(err.message);
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div>
        <p className="eyebrow">Admin ingest</p>
        <h2>Upload company PDFs</h2>
        <p className="muted">PDF, Markdown, or text. Files are stored under data/uploads and indexed with ACL metadata.</p>
      </div>
      <label className="upload-drop">
        <input
          type="file"
          accept=".pdf,.md,.markdown,.txt,application/pdf,text/markdown,text/plain"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
        <span>{file ? file.name : "Choose a policy PDF"}</span>
      </label>
      <label className="field">
        Access level
        <select value={accessLevel} onChange={(event) => setAccessLevel(event.target.value)}>
          <option value="PUBLIC_INTERNAL">PUBLIC_INTERNAL</option>
          <option value="INTERNAL_RESTRICTED">INTERNAL_RESTRICTED</option>
        </select>
      </label>
      <button type="submit" disabled={!file || busy}>
        {busy ? "Indexing…" : "Upload and index"}
      </button>
      {status && <p className="muted">{status}</p>}
      {error && <p className="error">{error}</p>}
    </form>
  );
}
