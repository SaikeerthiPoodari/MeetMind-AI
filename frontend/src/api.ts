export type ApiAction = {
  id: string;
  meeting_id: string;
  task: string;
  owner: string;
  deadline: string;
  priority: string;
  status: string;
  timestamp: string;
  confidence: number;
  evidence: string;
};
export type ApiMeeting = {
  id: string;
  title: string;
  description: string;
  status: string;
  is_demo: boolean;
  summary: string;
  created_at: string;
  actions: ApiAction[];
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001";
let token = localStorage.getItem("meetmind_token") ?? "";
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (!response.ok)
    throw new Error(
      (await response.json().catch(() => null))?.detail ??
        `Request failed (${response.status})`,
    );
  return response.json();
}
export const api = {
  async bootstrap() {
    const login = await request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: "demo@meetmind.ai",
        password: "DemoPass123!",
      }),
    });
    token = login.access_token;
    localStorage.setItem("meetmind_token", token);
    const meetings = await request<{ items: ApiMeeting[] }>("/api/meetings");
    const actions = await request<{ items: ApiAction[] }>("/api/actions");
    return { meetings: meetings.items, actions: actions.items };
  },
  listActions: () =>
    request<{ items: ApiAction[]; total: number }>("/api/actions"),
  updateAction: (id: string, payload: Partial<ApiAction>) =>
    request<ApiAction>(`/api/actions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  ask: (meetingId: string, question: string) =>
    request<{
      answer: string;
      confidence: number;
      evidence: Array<{ timestamp: string; speaker: string; text?: string }>;
    }>(`/api/meetings/${meetingId}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  search: (query: string) =>
    request<{
      items: Array<{
        type: string;
        meeting_id: string;
        title: string;
        matched: string;
        timestamp?: string;
        speaker?: string;
      }>;
      total: number;
    }>(`/api/search?q=${encodeURIComponent(query)}`),
  exportUrl: (meetingId: string, format: "json" | "txt") =>
    `${API_URL}/api/meetings/${meetingId}/export?format=${format}`,
  createMeeting: (title: string, description = "") =>
    request<ApiMeeting>("/api/meetings", {
      method: "POST",
      body: JSON.stringify({ title, description }),
    }),
  upload: async (meetingId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch(
      `${API_URL}/api/meetings/${meetingId}/upload`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body,
      },
    );
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => null))?.detail ?? "Upload failed",
      );
    return response.json() as Promise<{
      status: string;
      segments_created: number;
      message: string;
    }>;
  },
  join: (meetingId: string) =>
    request(`/api/meetings/${meetingId}/join`, { method: "POST" }),
  start: (meetingId: string) =>
    request(`/api/meetings/${meetingId}/start`, { method: "POST" }),
  end: (meetingId: string) =>
    request(`/api/meetings/${meetingId}/end`, { method: "POST" }),
  transcript: (meetingId: string) =>
    request<{
      items: Array<{
        id: string;
        timestamp: string;
        speaker: string;
        text: string;
        topic: string;
      }>;
    }>(`/api/meetings/${meetingId}/transcript`),
  profile: () =>
    request<{
      id: string;
      email: string;
      role: string;
      language: string;
      timezone: string;
      notifications_enabled: boolean;
    }>("/api/me"),
  updateProfile: (payload: {
    language: string;
    timezone: string;
    notifications_enabled: boolean;
  }) =>
    request<{
      language: string;
      timezone: string;
      notifications_enabled: boolean;
    }>("/api/me", { method: "PATCH", body: JSON.stringify(payload) }),
  notifications: () =>
    request<{
      items: Array<{
        id: string;
        kind: string;
        title: string;
        body: string;
        read: boolean;
        created_at: string;
      }>;
      unread: number;
    }>("/api/notifications"),
  markNotification: (id: string) =>
    request(`/api/notifications/${id}`, { method: "PATCH" }),
};
