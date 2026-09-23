import React from "react";

export default function CitationCard({ citation }) {
  return (
    <article className="citation">
      <header>
        <span>{citation.id}</span>
        <strong>{citation.document_title}</strong>
      </header>
      <p className="muted">
        {citation.section_title || "General"} · v{citation.document_version}
      </p>
      <p>{citation.snippet}</p>
    </article>
  );
}
