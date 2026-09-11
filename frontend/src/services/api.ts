import type {
  ChatResponse,
  ProgressEvent,
  ResearchResponse,
  ResearchResult,
  Session,
  Source,
} from "../types";

const API_BASE = "/api";

async function handleResponse<T>(promise: Promise<Response>): Promise<T> {
  const res = await promise;
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function health(): Promise<{ status: string }> {
  return handleResponse(fetch(`${API_BASE}/health`));
}

export async function startResearch(question: string): Promise<ResearchResponse> {
  return handleResponse(
    fetch(`${API_BASE}/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  );
}

export async function getResearchResult(threadId: string): Promise<ResearchResult> {
  return handleResponse(fetch(`${API_BASE}/research/${threadId}`));
}

export async function getSources(threadId: string): Promise<Source[]> {
  return handleResponse(fetch(`${API_BASE}/research/${threadId}/sources`));
}

export async function sendChat(threadId: string, message: string): Promise<ChatResponse> {
  return handleResponse(
    fetch(`${API_BASE}/research/${threadId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),
  );
}

export async function deleteResearch(threadId: string): Promise<void> {
  await handleResponse(
    fetch(`${API_BASE}/research/${threadId}`, { method: "DELETE" }),
  );
}

export async function listSessions(
  limit = 20,
  offset = 0,
): Promise<Session[]> {
  return handleResponse(
    fetch(`${API_BASE}/research?limit=${limit}&offset=${offset}`),
  );
}

export function streamResearch(
  threadId: string,
  onEvent: (event: ProgressEvent) => void,
  onDone: () => void,
  onError: (error: Event) => void,
): EventSource {
  const es = new EventSource(`${API_BASE}/research/${threadId}/stream`);
  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data) as ProgressEvent;
    if (data.step === "done") {
      onDone();
      es.close();
      return;
    }
    onEvent(data);
  };
  es.onerror = (ev) => {
    onError(ev);
    es.close();
  };
  return es;
}
