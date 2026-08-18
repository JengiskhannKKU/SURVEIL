import type {
  ChecklistItem,
  Engagement,
  EngagementSummary,
  Finding,
  Severity,
  ToolInfo,
  WordlistInfo,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listEngagements: () => request<EngagementSummary[]>("/api/engagements"),

  createEngagement: (target: string, name: string, notes: string) =>
    request<Engagement>("/api/engagements", {
      method: "POST",
      body: JSON.stringify({ target, name, notes }),
    }),

  getEngagement: (id: string) =>
    request<Engagement>(`/api/engagements/${id}`),

  deleteEngagement: (id: string) =>
    request<{ deleted: string }>(`/api/engagements/${id}`, {
      method: "DELETE",
    }),

  markDone: (engId: string, itemId: string) =>
    request<ChecklistItem>(
      `/api/engagements/${engId}/items/${itemId}/mark-done`,
      { method: "POST" }
    ),

  skip: (engId: string, itemId: string) =>
    request<ChecklistItem>(`/api/engagements/${engId}/items/${itemId}/skip`, {
      method: "POST",
    }),

  reset: (engId: string, itemId: string) =>
    request<ChecklistItem>(
      `/api/engagements/${engId}/items/${itemId}/reset`,
      { method: "POST" }
    ),

  updateNotes: (engId: string, itemId: string, notes: string) =>
    request<ChecklistItem>(
      `/api/engagements/${engId}/items/${itemId}/notes`,
      { method: "PATCH", body: JSON.stringify({ notes }) }
    ),

  createItem: (
    engId: string,
    body: {
      name: string;
      description?: string;
      category: string;
      category_code?: string;
      tools?: string[];
      references?: string[];
    }
  ) =>
    request<ChecklistItem>(`/api/engagements/${engId}/items`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateItem: (
    engId: string,
    itemId: string,
    body: Partial<
      Pick<ChecklistItem, "name" | "description" | "category" | "category_code" | "tools" | "references">
    >
  ) =>
    request<ChecklistItem>(`/api/engagements/${engId}/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteItem: (engId: string, itemId: string) =>
    request<{ deleted: string }>(`/api/engagements/${engId}/items/${itemId}`, {
      method: "DELETE",
    }),

  listTools: () => request<ToolInfo[]>("/api/tools"),

  previewCommand: (tool: string, target: string, fast: boolean, mode?: string) =>
    request<{ command: string[]; available: boolean }>(
      `/api/tools/${tool}/command?target=${encodeURIComponent(target)}&fast=${fast}` +
        (mode ? `&mode=${encodeURIComponent(mode)}` : "")
    ),

  listWordlists: () => request<WordlistInfo[]>("/api/tools/wordlists"),

  addFinding: (
    engId: string,
    itemId: string,
    body: {
      title: string;
      severity: Severity;
      description?: string;
      evidence?: string;
      cvss_vector?: string;
      cwe_id?: string;
      remediation?: string;
      verified?: boolean;
    }
  ) =>
    request<Finding>(
      `/api/engagements/${engId}/items/${itemId}/findings`,
      { method: "POST", body: JSON.stringify(body) }
    ),

  updateFinding: (
    engId: string,
    itemId: string,
    findingId: string,
    body: Partial<Pick<Finding, "title" | "severity" | "description" | "evidence" | "remediation" | "verified">>
  ) =>
    request<Finding>(
      `/api/engagements/${engId}/items/${itemId}/findings/${findingId}`,
      { method: "PATCH", body: JSON.stringify(body) }
    ),

  deleteFinding: (engId: string, itemId: string, findingId: string) =>
    request<{ deleted: string }>(
      `/api/engagements/${engId}/items/${itemId}/findings/${findingId}`,
      { method: "DELETE" }
    ),

  reportUrl: (engId: string, format: "md" | "docx") =>
    `${API_BASE}/api/engagements/${engId}/report?format=${format}`,
};
