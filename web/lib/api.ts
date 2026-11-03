const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  findings: unknown[];
  constructor(code: string, message: string, findings: unknown[] = []) {
    super(message);
    this.code = code;
    this.findings = findings;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("bdauth_token");
}

export function setToken(token: string) {
  localStorage.setItem("bdauth_token", token);
}

export function clearToken() {
  localStorage.removeItem("bdauth_token");
}

async function request<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && typeof options.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(data.code || "ERROR", data.message || res.statusText, data.findings || []);
  }
  return data as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; user: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  createSession: () => request("/sessions", { method: "POST" }),
  uploadData: (sessionId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/sessions/${sessionId}/data`, { method: "POST", body: form });
  },
  scrape: (sessionId: string, url: string, selector: string) => {
    const form = new FormData();
    form.append("url", url);
    form.append("selector", selector);
    return request(`/sessions/${sessionId}/scrape`, { method: "POST", body: form });
  },
  submitProblem: (sessionId: string, text: string) =>
    request(`/sessions/${sessionId}/problem`, { method: "POST", body: JSON.stringify({ text }) }),
  answerQuestions: (sessionId: string, answers: Record<string, string>) =>
    request(`/sessions/${sessionId}/answers`, { method: "POST", body: JSON.stringify({ answers }) }),
  confirm: (sessionId: string, edits: Record<string, string>) =>
    request(`/sessions/${sessionId}/confirm`, { method: "POST", body: JSON.stringify({ edits }) }),
  runResearch: (sessionId: string) => request(`/sessions/${sessionId}/research`, { method: "POST" }),
  generateOptions: (sessionId: string, useAi: boolean) =>
    request(`/sessions/${sessionId}/options`, { method: "POST", body: JSON.stringify({ use_ai: useAi }) }),
  updateRatings: (sessionId: string, optionRatings: Record<string, Record<string, number>>, weights?: Record<string, number>) =>
    request(`/sessions/${sessionId}/ratings`, {
      method: "PATCH",
      body: JSON.stringify({ option_ratings: optionRatings, weights }),
    }),
  getDecision: (sessionId: string) => request(`/sessions/${sessionId}/decision`),
  getSources: (sessionId: string) => request(`/sessions/${sessionId}/sources`),
  getAudit: (sessionId: string) => request(`/sessions/${sessionId}/audit`),
  getDeckUrl: (sessionId: string) => `${API_URL}/sessions/${sessionId}/deck.pptx`,
};
