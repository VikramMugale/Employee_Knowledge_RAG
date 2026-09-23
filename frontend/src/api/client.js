const TOKEN_KEY = "rag_access_token";
const USER_KEY = "rag_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function storeSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function expireSession() {
  clearSession();
  window.dispatchEvent(new Event("rag:unauthorized"));
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    expireSession();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (response.status === 403) {
    throw new Error("You do not have access to this action.");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return null;
  return response.json();
}

export function login(email, password) {
  return request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function fetchMe() {
  return request("/api/v1/auth/me");
}

export function sendChat(message, conversationId) {
  return request("/api/v1/chat", { method: "POST", body: JSON.stringify({ message, conversation_id: conversationId }) });
}

export function listDocuments() {
  return request("/api/v1/documents");
}

export function seedDocuments() {
  return request("/api/v1/documents/seed", { method: "POST" });
}

export function uploadDocument(file, accessLevel = "PUBLIC_INTERNAL", background = true) {
  const body = new FormData();
  body.append("file", file);
  body.append("access_level", accessLevel);
  body.append("background", background ? "true" : "false");
  return request("/api/v1/documents/upload", { method: "POST", body });
}

export function getIngestJob(jobId) {
  return request(`/api/v1/documents/jobs/${jobId}`);
}

export function runRetrievalExperiments(question, relevantChunkIds = []) {
  return request("/api/v1/admin/evaluations/retrieval-experiments", {
    method: "POST",
    body: JSON.stringify({ question, relevant_chunk_ids: relevantChunkIds }),
  });
}

export function submitFeedback(payload) {
  return request("/api/v1/feedback", { method: "POST", body: JSON.stringify(payload) });
}

export function fetchAnalytics() {
  return request("/api/v1/feedback/analytics");
}

export function fetchAdminDashboard() {
  return request("/api/v1/admin/dashboard");
}

export function runEvaluations() {
  return request("/api/v1/admin/evaluations/run");
}

export function runQualityGate() {
  return request("/api/v1/admin/evaluations/gate");
}

export async function streamChat(message, conversationId, onEvent) {
  const token = getToken();
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (response.status === 401) {
    expireSession();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (!response.ok || !response.body) {
    throw new Error("Could not stream the answer. Try again.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      const eventLine = block.split("\n").find((line) => line.startsWith("event:"));
      const dataLine = block.split("\n").find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) continue;
      const event = eventLine.replace("event:", "").trim();
      const raw = dataLine.replace("data:", "").trim();
      let data = raw;
      try { data = JSON.parse(raw); } catch {}
      onEvent(event, data);
    }
  }
}
