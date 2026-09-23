import React, { useEffect, useRef, useState } from "react";
import CitationCard from "../components/CitationCard.jsx";
import { sendChat, streamChat, submitFeedback } from "../api/client.js";

const STARTERS = [
  "How many days of Privilege Leave do full-time employees get?",
  "How much Casual Leave can be carried forward?",
  "What is the monthly internet allowance for hybrid employees?",
  "What is the gym membership reimbursement policy?",
];

function newId() {
  return crypto.randomUUID ? crypto.randomUUID() : `conv_${Date.now()}`;
}

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(true);
  const [busy, setBusy] = useState(false);
  const [rated, setRated] = useState({});
  const conversationId = useRef(newId());
  const threadRef = useRef(null);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, busy]);

  function resetThread() {
    conversationId.current = newId();
    setMessages([]);
    setRated({});
    setInput("");
  }

  async function ask(question) {
    const text = (question || input).trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setMessages((current) => [
      ...current,
      { role: "user", content: text },
      { role: "assistant", content: "", citations: [], noAnswer: false, traceId: null },
    ]);

    try {
      if (streaming) {
        await streamChat(text, conversationId.current, (event, data) => {
          setMessages((current) => {
            const next = [...current];
            const last = { ...next[next.length - 1] };
            if (event === "token") last.content += data.token || "";
            if (event === "citations") last.citations = data;
            if (event === "redacted_answer") last.content = data.answer;
            if (event === "done") {
              last.noAnswer = Boolean(data.no_answer);
              last.traceId = data.trace_id;
            }
            next[next.length - 1] = last;
            return next;
          });
        });
      } else {
        const response = await sendChat(text, conversationId.current);
        setMessages((current) => {
          const next = [...current];
          next[next.length - 1] = {
            role: "assistant",
            content: response.answer,
            citations: response.citations || [],
            noAnswer: response.no_answer_flag,
            traceId: response.trace_id,
          };
          return next;
        });
      }
    } catch (error) {
      setMessages((current) => {
        const next = [...current];
        next[next.length - 1] = {
          role: "assistant",
          content: error.message,
          citations: [],
          noAnswer: true,
        };
        return next;
      });
    } finally {
      setBusy(false);
    }
  }

  async function rate(index, message, rating) {
    if (!message.traceId || rated[index]) return;
    try {
      await submitFeedback({
        rating,
        trace_id: message.traceId,
        comment: rating > 0 ? "helpful" : "not helpful",
      });
      setRated((current) => ({ ...current, [index]: rating }));
    } catch {
      /* ignore */
    }
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask();
    }
  }

  return (
    <section className="chat">
      <header className="page-head">
        <div>
          <p className="eyebrow">Ask</p>
          <h1>Policy help</h1>
        </div>
        <div className="head-actions">
          <label className="toggle">
            <input
              type="checkbox"
              checked={streaming}
              onChange={(event) => setStreaming(event.target.checked)}
            />
            Stream
          </label>
          <button type="button" className="ghost compact" onClick={resetThread} disabled={busy}>
            New question set
          </button>
        </div>
      </header>

      <div className="thread" ref={threadRef}>
        {messages.length === 0 && (
          <div className="empty">
            <h2>What do you need from policy?</h2>
            <p>Ask in plain language. If the indexed documents do not cover it, the assistant will say so instead of guessing.</p>
            <div className="starters">
              {STARTERS.map((item) => (
                <button key={item} type="button" className="ghost" onClick={() => ask(item)}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <article key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
            <p className="bubble-label">{message.role === "user" ? "You" : "Assistant"}</p>
            <p className="bubble-body">
              {message.content || (busy && message.role === "assistant" ? "Looking through policy…" : "")}
            </p>
            {message.noAnswer && <small>Not covered by indexed policy</small>}
            {message.citations?.length > 0 && (
              <div className="citations">
                {message.citations.map((citation) => (
                  <CitationCard key={citation.id} citation={citation} />
                ))}
              </div>
            )}
            {message.role === "assistant" && message.traceId && (
              <div className="feedback">
                <button
                  type="button"
                  className={rated[index] === 1 ? "selected" : ""}
                  onClick={() => rate(index, message, 1)}
                >
                  Helpful
                </button>
                <button
                  type="button"
                  className={rated[index] === -1 ? "selected" : ""}
                  onClick={() => rate(index, message, -1)}
                >
                  Not helpful
                </button>
                {rated[index] && <span className="muted">Thanks</span>}
              </div>
            )}
          </article>
        ))}
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          ask();
        }}
      >
        <textarea
          rows={2}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about leave, remote work, or another published policy…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          {busy ? "Sending" : "Send"}
        </button>
      </form>
    </section>
  );
}
