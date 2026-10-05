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
  login: async (email: string, password: string) => {
    const result = await request<{
      access_token: string;
      user: { id: string; email: string; role: string };
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    token = result.access_token;
    localStorage.setItem("meetmind_token", token);
    return result.user;
  },
  register: async (email: string, password: string) => {
    const result = await request<{
      access_token: string;
      user: { id: string; email: string; role: string };
    }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    token = result.access_token;
    localStorage.setItem("meetmind_token", token);
    return result.user;
  },
  logout: async () => {
    if (token)
      await request("/api/auth/logout", { method: "POST" }).catch(
        () => undefined,
      );
    token = "";
    localStorage.removeItem("meetmind_token");
  },
  downloadData: async () => {
    const response = await fetch(`${API_URL}/api/me/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => null))?.detail ??
          "Data export failed",
      );
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "meetmind-my-data.json";
    anchor.click();
    URL.revokeObjectURL(url);
  },
  deleteAccount: async () => {
    const response = await fetch(`${API_URL}/api/me`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => null))?.detail ??
          "Account deletion failed",
      );
    token = "";
    localStorage.removeItem("meetmind_token");
  },
  adminAuditLogs: () =>
    request<{
      items: Array<{
        id: string;
        user_id: string;
        action: string;
        resource_type: string;
        resource_id: string;
        metadata: Record<string, unknown>;
        created_at: string;
      }>;
      total: number;
    }>("/api/admin/audit-logs"),
  health: () =>
    request<{
      status: string;
      database: string;
      ai_provider: string;
      ai_configured: boolean;
      translation_provider: string;
      translation_configured: boolean;
      transcription_provider: string;
      transcription_configured: boolean;
    }>("/api/health"),
  async bootstrap() {
    if (token) {
      await request("/api/me").catch(async () => {
        await api.login("demo@meetmind.ai", "DemoPass123!");
      });
    } else {
      await api.login("demo@meetmind.ai", "DemoPass123!");
    }
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
  exportUrl: (
    meetingId: string,
    format: "json" | "txt" | "md" | "pdf" | "docx",
  ) => `${API_URL}/api/meetings/${meetingId}/export?format=${format}`,
  downloadExport: async (
    meetingId: string,
    format: "json" | "txt" | "md" | "pdf" | "docx",
  ) => {
    const response = await fetch(api.exportUrl(meetingId, format), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => null))?.detail ?? "Export failed",
      );
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `meetmind-${meetingId}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  },
  createMeeting: (title: string, description = "") =>
    request<ApiMeeting>("/api/meetings", {
      method: "POST",
      body: JSON.stringify({ title, description }),
    }),
  getMeeting: (meetingId: string) =>
    request<ApiMeeting>(`/api/meetings/${meetingId}`),
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
  process: (meetingId: string) =>
    request(`/api/meetings/${meetingId}/process`, { method: "POST" }),
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
  decisions: (meetingId: string) =>
    request<{
      items: Array<{
        id: string;
        decision: string;
        speaker: string;
        timestamp: string;
        evidence: string;
        confidence: number;
        status: string;
      }>;
    }>(`/api/meetings/${meetingId}/decisions`),
  risks: (meetingId: string) =>
    request<{
      items: Array<{
        id: string;
        risk: string;
        severity: string;
        timestamp: string;
        recommendation: string;
        status: string;
      }>;
    }>(`/api/meetings/${meetingId}/risks`),
  questions: (meetingId: string) =>
    request<{
      items: Array<{
        id: string;
        question: string;
        speaker: string;
        timestamp: string;
        status: string;
      }>;
    }>(`/api/meetings/${meetingId}/questions`),
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
  translate: (
    meetingId: string,
    targetLanguage: string,
    scope: "summary" | "transcript" = "summary",
  ) =>
    request<{ translated_text: string; target_language: string }>(
      `/api/meetings/${meetingId}/translate`,
      {
        method: "POST",
        body: JSON.stringify({ target_language: targetLanguage, scope }),
      },
    ),
  compare: (firstId: string, secondId: string) =>
    request(
      `/api/compare/meetings?first_id=${encodeURIComponent(firstId)}&second_id=${encodeURIComponent(secondId)}`,
    ),
};
