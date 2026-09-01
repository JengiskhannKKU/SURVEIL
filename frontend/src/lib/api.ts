import type {
  AppConfig,
  ChecklistItem,
  Engagement,
  EngagementSummary,
  Finding,
  GroupedWordlists,
  RemoteGroupedWordlists,
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
    // FastAPI's HTTPException bodies are {"detail": "..."} — surface that
    // directly instead of the raw JSON text, callers show this in the UI.
    let detail: string | undefined;
    try {
      detail = JSON.parse(body)?.detail;
    } catch {
      // not JSON — fall through to the generic message below
    }
    throw new Error(detail ?? `${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listEngagements: () => request<EngagementSummary[]>("/api/engagements"),

  createEngagement: (
    target: string,
    name: string,
    notes: string,
    icon: string,
    methodology: string
  ) =>
    request<Engagement>("/api/engagements", {
      method: "POST",
      body: JSON.stringify({ target, name, notes, icon, methodology }),
    }),

  getEngagement: (id: string) =>
    request<Engagement>(`/api/engagements/${id}`),

  deleteEngagement: (id: string) =>
    request<{ deleted: string }>(`/api/engagements/${id}`, {
      method: "DELETE",
    }),

  addManualPath: (engId: string, path: string, status: number | null, note: string) =>
    request<Engagement>(`/api/engagements/${engId}/paths`, {
      method: "POST",
      body: JSON.stringify({ path, status, note }),
    }),

  removePath: (engId: string, path: string) =>
    request<Engagement>(`/api/engagements/${engId}/paths/remove`, {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  restorePath: (engId: string, path: string) =>
    request<Engagement>(`/api/engagements/${engId}/paths/restore`, {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  addManualPort: (engId: string, port: number, protocol: string, service: string, note: string) =>
    request<Engagement>(`/api/engagements/${engId}/ports`, {
      method: "POST",
      body: JSON.stringify({ port, protocol, service, note }),
    }),

  removePort: (engId: string, port: number, protocol: string) =>
    request<Engagement>(`/api/engagements/${engId}/ports/remove`, {
      method: "POST",
      body: JSON.stringify({ port, protocol }),
    }),

  restorePort: (engId: string, port: number, protocol: string) =>
    request<Engagement>(`/api/engagements/${engId}/ports/restore`, {
      method: "POST",
      body: JSON.stringify({ port, protocol }),
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

  cancelRun: (engId: string, itemId: string) =>
    request<{ cancelling: string }>(
      `/api/engagements/${engId}/items/${itemId}/cancel`,
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

  previewCommand: (tool: string, target: string, fast: boolean, mode?: string, itemId?: string) =>
    request<{
      command: string[];
      available: boolean;
      recommended_category: string | null;
      recommended_category_label: string | null;
      nuclei_tags: string | null;
    }>(
      `/api/tools/${tool}/command?target=${encodeURIComponent(target)}&fast=${fast}` +
        (mode ? `&mode=${encodeURIComponent(mode)}` : "") +
        (itemId ? `&item_id=${encodeURIComponent(itemId)}` : "")
    ),

  getToolHelp: (tool: string) =>
    request<{ available: boolean; text: string }>(`/api/tools/${tool}/help`),

  listWordlists: () => request<WordlistInfo[]>("/api/tools/wordlists"),

  // `category`, when passed, overrides the item_id-derived recommendation
  // outright — for a picker opened against a fixed category regardless of
  // checklist item (hydra's -L/-P slots; see ToolInfo.wordlist_slots).
  listWordlistsGrouped: (itemId?: string, category?: string) =>
    request<GroupedWordlists>(
      `/api/tools/wordlists/grouped?` +
        [
          itemId ? `item_id=${encodeURIComponent(itemId)}` : "",
          category ? `category=${encodeURIComponent(category)}` : "",
        ]
          .filter(Boolean)
          .join("&")
    ),

  browseRemoteWordlists: (itemId?: string, q?: string, category?: string) =>
    request<RemoteGroupedWordlists>(
      `/api/tools/wordlists/remote/browse?` +
        [
          itemId ? `item_id=${encodeURIComponent(itemId)}` : "",
          q ? `q=${encodeURIComponent(q)}` : "",
          category ? `category=${encodeURIComponent(category)}` : "",
        ]
          .filter(Boolean)
          .join("&")
    ),

  downloadRemoteWordlist: (path: string) =>
    request<{ path: string }>("/api/tools/wordlists/remote/download", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

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

  getReportContent: (engId: string) =>
    request<{ content: string }>(`/api/engagements/${engId}/report/content`),

  getConfig: () => request<AppConfig>("/api/config"),

  setWordlistDir: (wordlistDir: string | null) =>
    request<AppConfig>("/api/config/wordlist-dir", {
      method: "PUT",
      body: JSON.stringify({ wordlist_dir: wordlistDir }),
    }),
};
